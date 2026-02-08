"""
Chat views
"""
import json
import time
import logging
import asyncio
from asgiref.sync import sync_to_async
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes, renderer_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.renderers import BaseRenderer
from django.conf import settings
from django.db import transaction
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from .models import ChatThread, Message
from .serializers import (
    ChatThreadSerializer,
    ChatThreadDetailSerializer,
    MessageSerializer,
    CreateMessageSerializer,
)
from .services import ChatService
from tasks.workflows import assistant_response_workflow
from apps.signals.prompts import get_assistant_response_prompt

logger = logging.getLogger(__name__)


class StreamingRenderer(BaseRenderer):
    """Renderer for Server-Sent Events streaming responses."""
    media_type = "text/event-stream"
    format = "stream"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # StreamingHttpResponse handles rendering; return as-is.
        return data


async def _authenticate_jwt(request):
    """Authenticate a raw Django request using JWT (for async views outside DRF)."""
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed as JWTAuthFailed
    from django.contrib.auth.models import AnonymousUser

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return None

    jwt_auth = JWTAuthentication()
    try:
        validated_token = await sync_to_async(jwt_auth.get_validated_token)(
            auth_header.split(' ', 1)[1]
        )
        user = await sync_to_async(jwt_auth.get_user)(validated_token)
        return user
    except (InvalidToken, JWTAuthFailed):
        return None


class ChatThreadViewSet(viewsets.ModelViewSet):
    """ViewSet for chat threads"""
    
    permission_classes = [IsAuthenticated]

    def get_renderers(self):
        """Select renderers based on streaming mode."""
        if self.action == "messages" and self.request.query_params.get("stream") == "true":
            return [StreamingRenderer()]
        return super().get_renderers()
    
    def get_queryset(self):
        from django.db.models import Count, Prefetch

        queryset = ChatThread.objects.filter(user=self.request.user)

        archived_param = self.request.query_params.get('archived')
        if archived_param == 'true':
            queryset = queryset.filter(archived=True)
        elif archived_param == 'false' or archived_param is None:
            queryset = queryset.filter(archived=False)
        # archived=all -> no filter

        query = self.request.query_params.get('q')
        if query:
            queryset = queryset.filter(title__icontains=query)

        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # Annotate message_count to avoid N+1 in serializer
        queryset = queryset.annotate(
            _message_count=Count('messages'),
        )

        # Only prefetch messages for detail view (list doesn't need them)
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('messages')

        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatThreadDetailSerializer
        return ChatThreadSerializer
    
    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')
        if project and project.user_id != self.request.user.id:
            raise PermissionDenied("Project does not belong to user.")
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        project = serializer.validated_data.get('project')
        if project and project.user_id != self.request.user.id:
            raise PermissionDenied("Project does not belong to user.")
        # Mark title as manually edited when user explicitly changes it
        if 'title' in serializer.validated_data:
            serializer.save(title_manually_edited=True)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def messages(self, request, pk=None):
        """
        Create a new message in this thread
        
        POST /api/chat/threads/{id}/messages/
        {
            "content": "Hello, world!"
        }
        
        Supports streaming with ?stream=true query parameter
        """
        thread = self.get_object()
        serializer = CreateMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create user message
        message = ChatService.create_user_message(
            thread_id=thread.id,
            content=serializer.validated_data['content'],
            user=request.user
        )
        
        stream = request.query_params.get('stream') == 'true'

        if stream:
            # Stream tokens from OpenAI when available; fallback to chunked response
            async def event_stream():
                if not settings.OPENAI_API_KEY:
                    payload = json.dumps({"delta": "OpenAI API key not configured locally."})
                    yield f"event: chunk\ndata: {payload}\n\n"
                    yield f"event: done\ndata: {json.dumps({'message_id': None})}\n\n"
                    return

                # Use modular LLM provider (supports OpenAI, Anthropic, etc.)
                from apps.common.llm_providers import get_llm_provider
                
                model_key = settings.AI_MODELS.get('chat', settings.AI_MODELS['fast'])
                provider = get_llm_provider('chat')
                
                # Wrap sync Django ORM calls
                context_messages = await sync_to_async(ChatService._get_context_messages)(thread)
                conversation_context = ChatService._format_conversation_context(context_messages)
                prompt = get_assistant_response_prompt(
                    user_message=message.content,
                    conversation_context=conversation_context
                )

                full_content = ""
                try:
                    # Stream from provider (works with any provider)
                    system_prompt = (
                        "You are Episteme, a thoughtful assistant. "
                        "Be concise, ask clarifying questions when useful, and avoid generic advice."
                    )
                    
                    async for chunk in provider.stream_chat(
                        messages=[{"role": "user", "content": prompt}],
                        system_prompt=system_prompt
                    ):
                        full_content += chunk.content
                        payload = json.dumps({"delta": chunk.content})
                        yield f"event: chunk\ndata: {payload}\n\n"
                        
                except Exception:
                    logger.exception(
                        "assistant_stream_failed",
                        extra={"thread_id": str(thread.id), "message_id": str(message.id)},
                    )
                    fallback = "Sorry, I hit an error generating a response."
                    full_content = fallback
                    payload = json.dumps({"delta": fallback})
                    yield f"event: chunk\ndata: {payload}\n\n"

                # Create assistant message (sync operation)
                assistant_message = await sync_to_async(ChatService.create_assistant_message)(
                    thread_id=thread.id,
                    content=full_content,
                    metadata={'model': model_key, 'stub': False, 'streamed': True}
                )
                done_payload = json.dumps({"message_id": str(assistant_message.id)})
                yield f"event: done\ndata: {done_payload}\n\n"

            # Create streaming response
            # DRF recognizes StreamingHttpResponse and skips rendering
            response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"
            
            # CORS headers — validate origin against allowlist
            origin = request.headers.get("Origin", "")
            allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', ['http://localhost:3000'])
            if origin in allowed_origins:
                response["Access-Control-Allow-Origin"] = origin
                response["Access-Control-Allow-Credentials"] = "true"

            # Skip DRF's response finalization by returning raw HttpResponse
            # DRF detects HttpResponse and returns it as-is
            return response

        if settings.CHAT_SYNC_RESPONSES:
            assistant_response_workflow(
                thread_id=str(thread.id),
                user_message_id=str(message.id)
            )
        else:
            # Trigger assistant response workflow (async)
            assistant_response_workflow.delay(
                thread_id=str(thread.id),
                user_message_id=str(message.id)
            )
        
        # Return the user message immediately
        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    async def analyze_for_case(self, request, pk=None):
        """
        Analyze conversation to extract case components for preview.
        
        POST /api/chat/threads/{id}/analyze_for_case/
        Returns: AI analysis with title, position, questions, assumptions
        """
        from apps.common.llm_providers import get_llm_provider
        from apps.events.services import EventService
        from apps.events.models import EventType, ActorType
        import uuid as uuid_module
        import json
        
        thread = await sync_to_async(self.get_object)()
        messages = await sync_to_async(lambda: list(
            Message.objects.filter(thread=thread).order_by('created_at')
        ))()

        # Optional user focus to scope the analysis
        body = request.data if request.data else {}
        user_focus = body.get('user_focus', '')

        # Get last 8 messages for context
        recent_messages = messages[max(0, len(messages)-8):]

        # Build conversation context
        conversation_text = "\n\n".join([
            f"{m.role.upper()}: {m.content}"
            for m in recent_messages
        ])

        # AI analysis
        provider = get_llm_provider('fast')
        system_prompt = "You analyze conversations to extract decision components."

        focus_instruction = ""
        if user_focus:
            focus_instruction = f"The user wants to focus this case on: {user_focus}\nFrame the title, questions, and assumptions around this focus.\n\n"

        user_prompt = f"""{focus_instruction}Analyze this conversation and extract decision-making components:

{conversation_text}

Extract:
1. suggested_title: Short, clear decision question (under 60 chars)
2. position_draft: 2-3 sentences summarizing user's current thinking
3. key_questions: Array of 3-5 questions user should investigate
4. assumptions: Array of 2-4 untested assumptions
5. background_summary: 1-2 sentences of context
6. confidence: 0.0-1.0 (how clear is the decision space?)
7. decision_criteria: Array of 2-3 conditions that would let the user decide (e.g. "Cost comparison complete", "Risk assessment done")
8. assumption_test_strategies: Object mapping each assumption text to a one-line strategy for testing it

Return ONLY valid JSON:
{{"suggested_title": "...", "position_draft": "...", "key_questions": [...], "assumptions": [...], "background_summary": "...", "confidence": 0.75, "decision_criteria": [...], "assumption_test_strategies": {{"assumption text": "test strategy"}}}}"""
        
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt
        ):
            full_response += chunk.content
        
        try:
            from apps.common.llm_providers.utils import strip_markdown_fences
            cleaned = strip_markdown_fences(full_response.strip())
            analysis = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError, IndexError):
            return Response(
                {'error': 'Failed to parse analysis from AI response'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Emit event for provenance
        correlation_id = uuid_module.uuid4()
        await sync_to_async(EventService.append)(
            event_type=EventType.CONVERSATION_ANALYZED_FOR_CASE,
            payload={
                'thread_id': str(thread.id),
                'message_ids': [str(m.id) for m in recent_messages],
                'messages_count': len(recent_messages),
                'analysis': analysis,
                'model': 'claude-4.5-haiku',
            },
            actor_type=ActorType.ASSISTANT,
            thread_id=thread.id,
            correlation_id=correlation_id
        )
        
        return Response({
            **analysis,
            'correlation_id': str(correlation_id),
            'message_count': len(recent_messages)
        })
    
    @action(detail=True, methods=['post'])
    def dismiss_structure_suggestion(self, request, pk=None):
        """
        Dismiss a pending structure suggestion.
        
        POST /api/chat/threads/{id}/dismiss_structure_suggestion/
        
        Tracks dismissal for sensitivity tuning.
        """
        from apps.agents.structure_detector import StructureReadinessDetector
        
        thread = self.get_object()
        
        # Track feedback
        StructureReadinessDetector.track_suggestion_feedback(
            thread=thread,
            accepted=False
        )
        
        return Response({
            'status': 'dismissed',
            'suggestion_hint': thread.metadata.get('sensitivity_suggestion'),
        })
    
    @action(detail=True, methods=['post'])
    async def invoke_agent(self, request, pk=None):
        """
        Manually invoke an agent for this thread.
        
        POST /api/chat/threads/{id}/invoke_agent/
        
        Request body:
        {
            "agent_type": "research",  // "research" | "critique" | "brief"
            "params": {
                "topic": "FDA requirements",
                "use_case_skills": true
            }
        }
        
        Returns: Agent execution info
        """
        from apps.agents.orchestrator import AgentOrchestrator
        
        thread = await sync_to_async(self.get_object)()
        agent_type = request.data.get('agent_type')
        params = request.data.get('params', {})
        
        if not agent_type:
            return Response(
                {'error': 'agent_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if agent_type not in ['research', 'critique', 'brief']:
            return Response(
                {'error': 'agent_type must be research, critique, or brief'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not thread.primary_case:
            return Response(
                {'error': 'Thread must have a linked case to run agents'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = await AgentOrchestrator.run_agent_in_chat(
                thread=thread,
                agent_type=agent_type,
                user=request.user,
                **params
            )
            
            return Response(result, status=status.HTTP_202_ACCEPTED)
        except (ValueError, KeyError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("invoke_agent failed for thread %s", pk)
            return Response(
                {'error': 'Agent execution failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def validate_assumptions(self, request, pk=None):
        """
        Validate assumptions from a card action.
        
        POST /api/chat/threads/{id}/validate_assumptions/
        Body: {"assumption_ids": ["uuid1", "uuid2"]}
        
        Triggers research to validate assumptions.
        """
        from apps.signals.models import Signal
        
        thread = self.get_object()
        assumption_ids = request.data.get('assumption_ids', [])
        
        if not assumption_ids:
            return Response(
                {'error': 'assumption_ids required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get assumptions
        assumptions = Signal.objects.filter(
            id__in=assumption_ids,
            thread=thread,
            type='assumption'
        )
        
        if not assumptions.exists():
            return Response(
                {'error': 'No valid assumptions found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create assumption validator card
        message = ChatService.create_assumption_validator_card(
            thread_id=thread.id,
            assumptions=list(assumptions)
        )
        
        return Response({
            'status': 'validation_started',
            'message_id': str(message.id),
            'assumption_count': len(assumptions)
        })
    
    @action(detail=True, methods=['post'])
    def organize_questions(self, request, pk=None):
        """
        Organize questions into an inquiry.

        POST /api/chat/threads/{id}/organize_questions/
        Body: {
            "question_ids": ["uuid1", "uuid2"],
            "title": "Optional custom title"
        }

        Returns the created inquiry.
        """
        from apps.signals.models import Signal
        from apps.inquiries.services import InquiryService
        from apps.inquiries.models import ElevationReason
        from apps.inquiries.serializers import InquirySerializer
        from apps.companion.receipts import SessionReceiptService

        thread = self.get_object()
        question_ids = request.data.get('question_ids', [])
        custom_title = request.data.get('title')

        if not question_ids:
            return Response(
                {'error': 'question_ids required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if thread has a case
        if not thread.primary_case:
            return Response(
                {'error': 'Thread must be linked to a case before organizing questions into inquiries'},
                status=status.HTTP_400_BAD_REQUEST
            )

        case = thread.primary_case

        # Get questions - accept both 'question' and 'Question' types
        questions = list(Signal.objects.filter(
            id__in=question_ids,
            thread=thread,
            type__iexact='question'
        ))

        if not questions:
            return Response(
                {'error': 'No valid questions found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Determine inquiry title
        if custom_title:
            title = custom_title
        elif len(questions) == 1:
            title = questions[0].text
        else:
            # Use first question as title, note the others in description
            title = questions[0].text

        # Build description from multiple questions
        if len(questions) > 1:
            description = "Combined from questions:\n" + "\n".join(
                f"- {q.text}" for q in questions
            )
        else:
            description = ""

        # Create inquiry + link signals atomically
        with transaction.atomic():
            inquiry = InquiryService.create_inquiry(
                case=case,
                title=title,
                elevation_reason=ElevationReason.USER_CREATED,
                description=description,
                source='organize_questions',
                user=request.user,
                origin_signal_id=questions[0].id if questions else None,
            )

            # Link all question signals to the inquiry
            from apps.signals.models import Signal
            Signal.objects.filter(
                id__in=[q.id for q in questions]
            ).update(inquiry=inquiry)

        # Record session receipt
        SessionReceiptService.record(
            thread_id=thread.id,
            receipt_type='inquiry_created',
            title=f'Inquiry created: {title[:50]}{"..." if len(title) > 50 else ""}',
            detail=f'Organized from {len(questions)} question{"s" if len(questions) != 1 else ""}',
            related_case_id=case.id,
            related_inquiry_id=inquiry.id,
        )

        return Response({
            'status': 'inquiry_created',
            'inquiry': InquirySerializer(inquiry).data,
            'question_count': len(questions),
        })
    
    @action(detail=True, methods=['post'])
    def dismiss_suggestion(self, request, pk=None):
        """
        Dismiss a suggestion/intervention.

        POST /api/chat/threads/{id}/dismiss_suggestion/
        Body: {"type": "organize_questions"}
        """
        from .interventions import InterventionService

        thread = self.get_object()
        suggestion_type = request.data.get('type')

        if not suggestion_type:
            return Response(
                {'error': 'type required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark suggestion as dismissed
        InterventionService.dismiss_suggestion(thread, suggestion_type)

        return Response({
            'status': 'dismissed',
            'type': suggestion_type
        })

    @action(detail=True, methods=['get'])
    def session_receipts(self, request, pk=None):
        """
        Get session receipts for this thread.

        GET /api/chat/threads/{id}/session_receipts/

        Query params:
        - session_only: true (default) to get current session only (last 4 hours)
        - limit: max number of receipts (default 50)

        Returns: List of session receipts for the companion panel
        """
        from apps.companion.receipts import SessionReceiptService
        from apps.companion.serializers import SessionReceiptSerializer

        thread = self.get_object()
        session_only = request.query_params.get('session_only', 'true').lower() == 'true'
        limit = int(request.query_params.get('limit', '50'))

        if session_only:
            receipts = SessionReceiptService.get_session_receipts(
                thread_id=thread.id,
                limit=limit
            )
        else:
            receipts = SessionReceiptService.get_all_thread_receipts(
                thread_id=thread.id,
                limit=limit
            )

        serializer = SessionReceiptSerializer(receipts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    async def create_case_from_analysis(self, request, pk=None):
        """
        Create case from conversation analysis with pre-filled content.
        
        POST /api/chat/threads/{id}/create_case_from_analysis/
        Body: {analysis, correlation_id, user_edits}
        """
        from apps.cases.services import CaseService
        from apps.cases.serializers import CaseSerializer, CaseDocumentSerializer, InvestigationPlanSerializer
        from apps.inquiries.serializers import InquirySerializer
        import uuid as uuid_module

        thread = await sync_to_async(self.get_object)()

        analysis = request.data.get('analysis')
        raw_correlation_id = request.data.get('correlation_id')
        user_edits = request.data.get('user_edits')

        if not analysis or not raw_correlation_id:
            return Response(
                {'error': 'analysis and correlation_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            correlation_id = uuid_module.UUID(raw_correlation_id)
        except (ValueError, AttributeError):
            return Response(
                {'error': 'correlation_id must be a valid UUID'},
                status=status.HTTP_400_BAD_REQUEST
            )

        case, brief, inquiries, plan = await sync_to_async(
            CaseService.create_case_from_analysis
        )(
            user=request.user,
            analysis=analysis,
            thread_id=thread.id,
            correlation_id=correlation_id,
            user_edits=user_edits
        )

        return Response({
            'case': await sync_to_async(lambda: CaseSerializer(case).data)(),
            'brief': await sync_to_async(lambda: CaseDocumentSerializer(brief).data)(),
            'inquiries': await sync_to_async(lambda: InquirySerializer(inquiries, many=True).data)(),
            'plan': await sync_to_async(lambda: InvestigationPlanSerializer(plan).data)(),
            'correlation_id': str(correlation_id)
        })


@csrf_exempt
@require_POST
async def unified_stream(request, thread_id):
    """
    Unified streaming endpoint for chat response + reflection + signals + action hints.

    Uses the UnifiedAnalysisEngine to generate a single LLM response with
    sectioned output that streams to the client.

    POST /api/chat/threads/{thread_id}/unified-stream/
    {
        "content": "User message content"
    }

    Streams:
    - response_chunk: Chat response tokens
    - reflection_chunk: Reflection tokens
    - response_complete: Full response
    - reflection_complete: Full reflection
    - signals: Extracted signals array
    - action_hints: AI-suggested actions
    - done: Completion with IDs
    - error: Error message
    """
    import uuid as uuid_module

    # Authenticate via JWT
    user = await _authenticate_jwt(request)
    if user is None:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    # Get thread and verify ownership
    thread = await sync_to_async(
        lambda: get_object_or_404(ChatThread, id=thread_id, user=user)
    )()

    # Parse JSON body
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    # Get message content from request body
    content = body.get('content', '')
    if not content:
        return JsonResponse(
            {'error': 'Message content is required'},
            status=400
        )

    # Get optional mode context for system prompt selection
    mode_context = body.get('context', {})

    # Create user message first (persist mode_context as metadata)
    user_message = await sync_to_async(ChatService.create_user_message)(
        thread_id=thread.id,
        content=content,
        user=user,
        metadata={'mode_context': mode_context} if mode_context else None,
    )

    # Kick off parallel title generation (non-blocking) before entering the stream
    from apps.intelligence.title_generator import generate_thread_title

    title_task = None
    should_gen_title = (
        (not thread.title or thread.title == 'New Chat')
        and not thread.title_manually_edited
    )
    if should_gen_title:
        title_task = asyncio.create_task(
            generate_thread_title([{"role": "user", "content": content}])
        )

    async def event_stream():
        """Generator for SSE events using UnifiedAnalysisEngine"""
        from apps.intelligence.engine import UnifiedAnalysisEngine, StreamEventType
        from apps.intelligence.handlers import UnifiedAnalysisHandler

        correlation_id = uuid_module.uuid4()
        engine = UnifiedAnalysisEngine()

        # Build conversation context
        messages = await sync_to_async(list)(
            Message.objects.filter(thread=thread)
            .order_by('-created_at')[:10]
        )
        conversation_context = "\n\n".join([
            f"{m.role.upper()}: {m.content}"
            for m in reversed(messages)
        ])

        # Track content for post-processing
        response_content = ""
        reflection_content = ""
        signals_json = ""
        action_hints_json = ""
        extraction_enabled = True

        # Check if thread is in scaffolding mode or if frontend sent mode context
        thread_metadata = thread.metadata or {}
        system_prompt_override = None
        if thread_metadata.get('mode') == 'scaffolding':
            from apps.intelligence.prompts import build_scaffolding_system_prompt

            # Load skill context for domain-aware scaffolding
            scaffolding_skill_context = None
            try:
                from apps.skills.injection import build_skill_context
                # Skills can come from: (1) thread's linked case, or (2) thread metadata
                _case = thread.primary_case
                if _case:
                    _skills = await sync_to_async(
                        lambda: list(_case.active_skills.filter(status='active'))
                    )()
                    if _skills:
                        scaffolding_skill_context = await sync_to_async(
                            lambda: build_skill_context(_skills, 'brief')
                        )()
            except Exception as e:
                logger.warning(f"Could not load skills for scaffolding: {e}")

            system_prompt_override = build_scaffolding_system_prompt(
                skill_context=scaffolding_skill_context
            )
        elif mode_context.get('mode') == 'inquiry_focus' and mode_context.get('inquiryId'):
            # Inquiry-focused mode: emphasize investigation and evidence gathering
            inquiry_id = mode_context.get('inquiryId')
            try:
                from apps.inquiries.models import Inquiry
                inquiry = await sync_to_async(
                    lambda: Inquiry.objects.filter(id=inquiry_id).first()
                )()
                if inquiry:
                    system_prompt_override = (
                        "You are Episteme, a thoughtful decision-support assistant. "
                        f"The user is currently investigating a specific inquiry: \"{inquiry.title}\". "
                        f"{('Context: ' + inquiry.description + '. ') if inquiry.description else ''}"
                        "Focus your responses on helping them gather evidence, validate assumptions, "
                        "and reach a well-supported conclusion for this inquiry. "
                        "Be specific, cite reasoning, and suggest concrete next steps for investigation. "
                        "When the user's question relates to this inquiry, frame your answer in that context."
                    )
            except Exception as e:
                logger.warning(f"Could not load inquiry for mode context: {e}")
        elif mode_context.get('mode') == 'case' and mode_context.get('caseId'):
            # Case mode: inject stage-aware guidance
            case_id = mode_context.get('caseId')
            try:
                from apps.cases.models import InvestigationPlan
                plan_obj = await sync_to_async(
                    lambda: InvestigationPlan.objects.filter(case_id=case_id).first()
                )()
                if plan_obj:
                    stage_guidance = {
                        'exploring': (
                            'The user is in the exploring stage. '
                            'Surface assumptions, identify blind spots, and suggest areas to investigate.'
                        ),
                        'investigating': (
                            'The user is actively investigating. '
                            'Help gather evidence, challenge beliefs, and update assumption statuses.'
                        ),
                        'synthesizing': (
                            'The user is synthesizing findings. '
                            'Help evaluate decision criteria, weigh trade-offs, and refine their position.'
                        ),
                        'ready': (
                            'The investigation is nearing completion. '
                            'Help finalize the decision, ensure all criteria are addressed, and prepare a summary.'
                        ),
                    }
                    system_prompt_override = (
                        "You are Episteme, a thoughtful decision-support assistant. "
                        f"The case is currently in the '{plan_obj.stage}' stage. "
                        f"{stage_guidance.get(plan_obj.stage, '')} "
                        "Adapt your tone and suggestions to match this investigation phase."
                    )
            except Exception as e:
                logger.warning(f"Could not load plan for stage context: {e}")

        try:
            async for event in engine.analyze_simple(
                thread=thread,
                user_message=content,
                conversation_context=conversation_context,
                system_prompt_override=system_prompt_override,
            ):
                if event.type == StreamEventType.RESPONSE_CHUNK:
                    response_content += event.data
                    payload = json.dumps({"delta": event.data})
                    yield f"event: response_chunk\ndata: {payload}\n\n"

                elif event.type == StreamEventType.REFLECTION_CHUNK:
                    reflection_content += event.data
                    payload = json.dumps({"delta": event.data})
                    yield f"event: reflection_chunk\ndata: {payload}\n\n"

                elif event.type == StreamEventType.RESPONSE_COMPLETE:
                    response_content = event.data
                    payload = json.dumps({"content": event.data})
                    yield f"event: response_complete\ndata: {payload}\n\n"

                elif event.type == StreamEventType.REFLECTION_COMPLETE:
                    reflection_content = event.data
                    payload = json.dumps({"content": event.data})
                    yield f"event: reflection_complete\ndata: {payload}\n\n"

                elif event.type == StreamEventType.SIGNALS_COMPLETE:
                    signals = event.data.get('signals', [])
                    signals_json = event.data.get('raw', '[]')
                    extraction_enabled = event.data.get('extraction_enabled', True)
                    payload = json.dumps({"signals": signals})
                    yield f"event: signals\ndata: {payload}\n\n"

                elif event.type == StreamEventType.ACTION_HINTS_COMPLETE:
                    action_hints = event.data.get('action_hints', [])
                    action_hints_json = event.data.get('raw', '[]')
                    payload = json.dumps({"action_hints": action_hints})
                    yield f"event: action_hints\ndata: {payload}\n\n"

                elif event.type == StreamEventType.ERROR:
                    error_msg = event.data.get('error', 'Unknown error')
                    payload = json.dumps({"error": error_msg})
                    yield f"event: error\ndata: {payload}\n\n"

                elif event.type == StreamEventType.DONE:
                    extraction_enabled = event.data.get('extraction_enabled', True)
                    # Don't yield done yet - we need to save first

            # Post-process: save message, reflection, signals
            result = await UnifiedAnalysisHandler.handle_completion(
                thread=thread,
                user=user,
                response_content=response_content,
                reflection_content=reflection_content,
                signals_json=signals_json,
                model_key='chat',
                extraction_was_enabled=extraction_enabled,
                correlation_id=correlation_id
            )

            # --- Title generation: await parallel task or check for refresh ---
            if title_task is not None:
                try:
                    generated_title = await title_task
                    if generated_title:
                        thread.title = generated_title
                        metadata = thread.metadata or {}
                        msg_count = await sync_to_async(
                            lambda: Message.objects.filter(thread=thread, role='user').count()
                        )()
                        metadata['title_gen_at_msg_count'] = msg_count
                        thread.metadata = metadata
                        await sync_to_async(thread.save)(
                            update_fields=['title', 'metadata']
                        )
                        title_payload = json.dumps({"title": generated_title})
                        yield f"event: title_update\ndata: {title_payload}\n\n"
                except Exception:
                    logger.warning(
                        "title_generation_failed",
                        extra={"thread_id": str(thread.id)}
                    )
            else:
                # Check if title should be refreshed (conversation drift)
                if not thread.title_manually_edited and thread.title not in ('', 'New Chat'):
                    try:
                        metadata = thread.metadata or {}
                        msg_count = await sync_to_async(
                            lambda: Message.objects.filter(thread=thread, role='user').count()
                        )()
                        last_title_gen_at_msg = metadata.get('title_gen_at_msg_count', 0)

                        if msg_count >= 10 and (msg_count - last_title_gen_at_msg) >= 8:
                            recent_msgs = await sync_to_async(list)(
                                Message.objects.filter(thread=thread)
                                .order_by('-created_at')[:6]
                            )
                            # TODO: This await blocks the done event by ~300ms.
                            # Could be parallelized with create_task if latency matters,
                            # but refresh is rare (every 8+ msgs after 10th) so acceptable.
                            refreshed_title = await generate_thread_title([
                                {"role": m.role, "content": m.content}
                                for m in reversed(recent_msgs)
                            ])
                            if refreshed_title and refreshed_title != thread.title:
                                thread.title = refreshed_title
                                metadata['title_gen_at_msg_count'] = msg_count
                                thread.metadata = metadata
                                await sync_to_async(thread.save)(
                                    update_fields=['title', 'metadata']
                                )
                                title_payload = json.dumps({"title": refreshed_title})
                                yield f"event: title_update\ndata: {title_payload}\n\n"
                    except Exception:
                        logger.warning(
                            "title_refresh_failed",
                            extra={"thread_id": str(thread.id)}
                        )

            # Now yield done event with IDs
            done_payload = json.dumps({
                "message_id": result.get('message_id'),
                "reflection_id": result.get('reflection_id'),
                "signals_count": result.get('signals_count', 0),
                "action_hints_count": len(json.loads(action_hints_json or '[]'))
            })
            yield f"event: done\ndata: {done_payload}\n\n"

        except Exception as e:
            logger.exception(
                "unified_stream_error",
                extra={"thread_id": str(thread.id), "error": str(e)}
            )
            error_payload = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_payload}\n\n"

    # Create streaming response
    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    # CORS headers — validate origin against allowlist
    origin = request.headers.get("Origin", "")
    allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', ['http://localhost:3000'])
    if origin in allowed_origins:
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Credentials"] = "true"

    return response




class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for messages
    Messages are created via ChatThreadViewSet.messages action
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see messages in their own threads
        queryset = Message.objects.filter(thread__user=self.request.user)
        thread_id = self.request.query_params.get('thread')
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        return queryset
