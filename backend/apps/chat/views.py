"""
Chat views
"""
import json
import logging
import asyncio
from asgiref.sync import sync_to_async
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.renderers import BaseRenderer
from django.conf import settings
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
from apps.chat.prompts import get_assistant_response_prompt
from apps.common.auth import authenticate_jwt

logger = logging.getLogger(__name__)


class StreamingRenderer(BaseRenderer):
    """Renderer for Server-Sent Events streaming responses."""
    media_type = "text/event-stream"
    format = "stream"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # StreamingHttpResponse handles rendering; return as-is.
        return data




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
            from django.db.models import Prefetch
            from apps.projects.models import DocumentChunk
            queryset = queryset.prefetch_related(
                Prefetch(
                    'messages__source_chunks',
                    queryset=DocumentChunk.objects.select_related('document'),
                ),
                'messages',
            )

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
        insight_id = body.get('insight_id', '')

        # Get last 8 messages for context
        recent_messages = messages[max(0, len(messages)-8):]

        # Build conversation context
        conversation_text = "\n\n".join([
            f"{m.role.upper()}: {m.content}"
            for m in recent_messages
        ])

        # Enrich with orientation finding context if provided
        finding_context = ""
        if insight_id and thread.project_id:
            try:
                from apps.graph.models import ProjectInsight
                insight = await sync_to_async(
                    lambda: ProjectInsight.objects.select_related('orientation').get(
                        id=insight_id,
                        orientation__project_id=thread.project_id,
                    )
                )()
                finding_context = (
                    f"\n\nThis conversation originated from an orientation finding:\n"
                    f"- Type: {insight.insight_type}\n"
                    f"- Title: {insight.title}\n"
                    f"- Content: {insight.content}\n"
                )
                if insight.research_result:
                    finding_context += f"- Prior research: {insight.research_result[:500]}\n"
                finding_context += (
                    "Use this finding context to inform the case analysis — "
                    "the finding's themes and tensions should shape the key questions and assumptions.\n"
                )
            except Exception as e:
                logger.debug("Finding context load skipped: %s", e)

        # AI analysis
        provider = get_llm_provider('fast')
        system_prompt = "You analyze conversations to extract decision components."

        focus_instruction = ""
        if user_focus:
            focus_instruction = f"The user wants to focus this case on: {user_focus}\nFrame the title, questions, and assumptions around this focus.\n\n"

        user_prompt = f"""{focus_instruction}{finding_context}Analyze this conversation and extract decision-making components:

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
            logger.exception("Agent invocation validation error for thread %s", pk)
            return Response(
                {'error': 'Invalid agent configuration. Please check parameters and try again.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("invoke_agent failed for thread %s", pk)
            return Response(
                {'error': 'Agent execution failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    async def create_case_from_analysis(self, request, pk=None):
        """
        Create case from conversation analysis with pre-filled content.
        
        POST /api/chat/threads/{id}/create_case_from_analysis/
        Body: {analysis, correlation_id, user_edits}
        """
        from apps.cases.services import CaseService
        from apps.cases.serializers import CaseSerializer, WorkingDocumentSerializer, InvestigationPlanSerializer
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
            'brief': await sync_to_async(lambda: WorkingDocumentSerializer(brief).data)(),
            'inquiries': await sync_to_async(lambda: InquirySerializer(inquiries, many=True).data)(),
            'plan': await sync_to_async(lambda: InvestigationPlanSerializer(plan).data)(),
            'correlation_id': str(correlation_id)
        })


@csrf_exempt
@require_POST
async def unified_stream(request, thread_id):
    """
    Unified streaming endpoint for chat response + reflection + action hints.

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
    - action_hints: AI-suggested actions
    - done: Completion with IDs
    - error: Error message
    """
    import uuid as uuid_module

    # Authenticate via JWT
    user = await authenticate_jwt(request)
    if user is None:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    # Get thread and verify ownership
    # H1: annotate with message count for tool activation depth gate
    from django.db.models import Count
    thread = await sync_to_async(
        lambda: ChatThread.objects.filter(
            id=thread_id, user=user,
        ).annotate(
            _message_count=Count('messages'),
        ).first()
    )()
    if not thread:
        return JsonResponse({'error': 'Thread not found'}, status=404)

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
        """SSE generator — delegates to decomposed phase functions in stream_phases."""
        from .stream_phases import (
            StreamState, sse,
            assemble_context, stream_llm_response,
            persist_message, apply_graph_edits,
            execute_tool_actions, kick_off_companion,
            resolve_title, process_companion_results,
            build_done_event,
        )

        state = StreamState(
            thread=thread,
            user=user,
            content=content,
            mode_context=mode_context,
            title_task=title_task,
            correlation_id=uuid_module.uuid4(),
        )

        try:
            # Phase 1: Context assembly
            await assemble_context(state)

            # Phase 2: LLM streaming (main SSE event source)
            async for event in stream_llm_response(state):
                yield event

            # Phase 3: Persist message + emit source chunks
            async for event in persist_message(state):
                yield event

            # Phase 4: Apply graph edits (no SSE output)
            await apply_graph_edits(state)

            # Phase 5: Execute tool actions
            async for event in execute_tool_actions(state):
                yield event

            # Phase 6: Kick off companion (fire-and-forget)
            await kick_off_companion(state)

            # Phase 7: Title generation
            async for event in resolve_title(state):
                yield event

            # Phase 8: Companion await + streaming
            async for event in process_companion_results(state):
                yield event

            # Phase 9: Done event
            yield build_done_event(state)

        except Exception as e:
            logger.exception(
                "unified_stream_error",
                extra={"thread_id": str(thread.id), "error": str(e)}
            )
            yield sse("error", {"error": "An unexpected error occurred. Please try again."})

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




@csrf_exempt
@require_GET
async def thread_structure(request, thread_id):
    """
    Get the current conversation structure for a thread.

    GET /api/chat/threads/{thread_id}/structure/
    """
    user = await authenticate_jwt(request)
    if user is None:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    thread = await sync_to_async(
        lambda: get_object_or_404(ChatThread, id=thread_id, user=user)
    )()

    from .companion_service import CompanionService
    structure = await CompanionService.get_current_structure_async(thread.id)

    if not structure:
        return JsonResponse({'structure': None})

    return JsonResponse({
        'structure': {
            'id': str(structure.id),
            'thread_id': str(structure.thread_id),
            'version': structure.version,
            'structure_type': structure.structure_type,
            'content': structure.content,
            'established': structure.established,
            'open_questions': structure.open_questions,
            'eliminated': structure.eliminated,
            'context_summary': structure.context_summary,
            'updated_at': structure.updated_at.isoformat(),
        }
    })


@csrf_exempt
@require_POST
async def confirm_tool_action(request, thread_id):
    """
    Confirm and execute a pending tool action.

    POST /api/chat/threads/{thread_id}/confirm-tool/
    Body: { "confirmation_id": "...", "approved": true/false }

    Response contract:
      On dismiss (approved=false):
        { "success": true, "dismissed": true }
      On successful execution (approved=true, tool succeeds):
        { "success": true, "tool": "...", "display_name": "...", "output": {...}, "error": null }
      On failed execution (approved=true, tool fails):
        { "success": false, "tool": "...", "display_name": "...", "output": {}, "error": "..." }

    Frontend check: ``!result.success && !result.dismissed`` detects execution
    failures. A dismissed response always has ``success=true`` so it passes through.
    """
    user = await authenticate_jwt(request)
    if user is None:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    # Verify thread ownership
    await sync_to_async(
        lambda: get_object_or_404(ChatThread, id=thread_id, user=user)
    )()

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    confirmation_id = body.get('confirmation_id')
    approved = body.get('approved', False)

    if not confirmation_id:
        return JsonResponse(
            {'error': 'confirmation_id is required'}, status=400
        )

    if not approved:
        return JsonResponse({'success': True, 'dismissed': True})

    from apps.intelligence.tools.executor import ToolExecutor

    result = await ToolExecutor.execute_confirmed(confirmation_id, user)

    return JsonResponse({
        'success': result.success,
        'tool': result.tool_name,
        'display_name': result.display_name,
        'output': result.output,
        'error': result.error,
    })


@csrf_exempt
@require_GET
async def thread_research(request, thread_id):
    """
    Get research results for a thread.

    GET /api/chat/threads/{thread_id}/research/
    """
    user = await authenticate_jwt(request)
    if user is None:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    thread = await sync_to_async(
        lambda: get_object_or_404(ChatThread, id=thread_id, user=user)
    )()

    from .models import ResearchResult
    results = await sync_to_async(list)(
        ResearchResult.objects.filter(thread=thread).order_by('-created_at')[:20]
    )

    return JsonResponse({
        'results': [
            {
                'id': str(r.id),
                'question': r.question,
                'answer': r.answer,
                'sources': r.sources,
                'status': r.status,
                'surfaced': r.surfaced,
                'created_at': r.created_at.isoformat(),
            }
            for r in results
        ]
    })


@csrf_exempt
@require_GET
async def thread_episodes(request, thread_id):
    """
    Get conversation episodes for a thread.

    GET /api/chat/threads/{thread_id}/episodes/
    """
    user = await authenticate_jwt(request)
    if user is None:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    thread = await sync_to_async(
        lambda: get_object_or_404(ChatThread, id=thread_id, user=user)
    )()

    from .models import ConversationEpisode
    episodes = await sync_to_async(list)(
        ConversationEpisode.objects.filter(thread=thread).order_by('episode_index')
    )

    current_episode_id = None
    if thread.current_episode_id:
        current_episode_id = str(thread.current_episode_id)

    return JsonResponse({
        'episodes': [
            {
                'id': str(ep.id),
                'episode_index': ep.episode_index,
                'topic_label': ep.topic_label,
                'content_summary': ep.content_summary,
                'message_count': ep.message_count,
                'shift_type': ep.shift_type,
                'sealed': ep.sealed,
                'sealed_at': ep.sealed_at.isoformat() if ep.sealed_at else None,
                'start_message_id': str(ep.start_message_id) if ep.start_message_id else None,
                'end_message_id': str(ep.end_message_id) if ep.end_message_id else None,
                'created_at': ep.created_at.isoformat(),
            }
            for ep in episodes
        ],
        'current_episode_id': current_episode_id,
    })


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for messages
    Messages are created via ChatThreadViewSet.messages action
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see messages in their own threads
        from django.db.models import Prefetch
        from apps.projects.models import DocumentChunk
        queryset = Message.objects.filter(
            thread__user=self.request.user
        ).prefetch_related(
            Prefetch(
                'source_chunks',
                queryset=DocumentChunk.objects.select_related('document'),
            ),
        )
        thread_id = self.request.query_params.get('thread')
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        return queryset
