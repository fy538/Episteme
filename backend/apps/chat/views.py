"""
Chat views
"""
import json
import time
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
from django.http import StreamingHttpResponse

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


class ChatThreadViewSet(viewsets.ModelViewSet):
    """ViewSet for chat threads"""
    
    permission_classes = [IsAuthenticated]

    def get_renderers(self):
        """Select renderers based on streaming mode."""
        if self.action == "messages" and self.request.query_params.get("stream") == "true":
            return [StreamingRenderer()]
        return super().get_renderers()
    
    def get_queryset(self):
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
            
            # CORS headers
            origin = request.headers.get("Origin", "http://localhost:3000")
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
        
        user_prompt = f"""Analyze this conversation and extract decision-making components:

{conversation_text}

Extract:
1. suggested_title: Short, clear decision question (under 60 chars)
2. position_draft: 2-3 sentences summarizing user's current thinking
3. key_questions: Array of 3-5 questions user should investigate
4. assumptions: Array of 2-4 untested assumptions
5. background_summary: 1-2 sentences of context
6. confidence: 0.0-1.0 (how clear is the decision space?)

Return ONLY valid JSON:
{{"suggested_title": "...", "position_draft": "...", "key_questions": [...], "assumptions": [...], "background_summary": "...", "confidence": 0.75}}"""
        
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt
        ):
            full_response += chunk.content
        
        analysis = json.loads(full_response.strip())
        
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
        except Exception as e:
            return Response(
                {'error': str(e)},
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
        from apps.cases.serializers import CaseSerializer, CaseDocumentSerializer
        from apps.inquiries.serializers import InquirySerializer
        import uuid as uuid_module
        
        thread = await sync_to_async(self.get_object)()
        analysis = request.data['analysis']
        correlation_id = uuid_module.UUID(request.data['correlation_id'])
        user_edits = request.data.get('user_edits')
        
        case, brief, inquiries = await sync_to_async(
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
            'correlation_id': str(correlation_id)
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
        queryset = Message.objects.filter(thread__user=self.request.user)
        thread_id = self.request.query_params.get('thread')
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        return queryset
