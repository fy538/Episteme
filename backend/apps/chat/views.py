"""
Chat views
"""
import json
import time
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.conf import settings
from django.http import StreamingHttpResponse
from openai import OpenAI

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


class ChatThreadViewSet(viewsets.ModelViewSet):
    """ViewSet for chat threads"""
    
    permission_classes = [IsAuthenticated]
    
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
    
    @action(detail=True, methods=['post'], renderer_classes=[])
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
            # Bypass DRF content negotiation for SSE streaming
            # DRF's renderer classes can interfere with text/event-stream
            # Stream tokens from OpenAI when available; fallback to chunked response
            def event_stream():
                if not settings.OPENAI_API_KEY:
                    payload = json.dumps({"delta": "OpenAI API key not configured locally."})
                    yield f"event: chunk\ndata: {payload}\n\n"
                    yield f"event: done\ndata: {json.dumps({'message_id': None})}\n\n"
                    return

                model_key = settings.AI_MODELS.get('chat', settings.AI_MODELS['fast'])
                provider, _, model_name = model_key.partition(':')
                if provider != 'openai':
                    assistant_message = ChatService.generate_assistant_response(
                        thread_id=thread.id,
                        user_message_id=message.id
                    )
                    content = assistant_message.content or ""
                    chunk_size = 24
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i + chunk_size]
                        payload = json.dumps({"delta": chunk})
                        yield f"event: chunk\ndata: {payload}\n\n"
                        time.sleep(0.01)
                    done_payload = json.dumps({"message_id": str(assistant_message.id)})
                    yield f"event: done\ndata: {done_payload}\n\n"
                    return

                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                context_messages = ChatService._get_context_messages(thread)
                conversation_context = ChatService._format_conversation_context(context_messages)
                prompt = get_assistant_response_prompt(
                    user_message=message.content,
                    conversation_context=conversation_context
                )

                full_content = ""
                try:
                    stream_resp = client.chat.completions.create(
                        model=model_name or model_key,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are Episteme, a thoughtful assistant. "
                                    "Be concise, ask clarifying questions when useful, and avoid generic advice."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        stream=True,
                    )
                    for chunk in stream_resp:
                        delta = chunk.choices[0].delta.content or ""
                        if not delta:
                            continue
                        full_content += delta
                        payload = json.dumps({"delta": delta})
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

                assistant_message = ChatService.create_assistant_message(
                    thread_id=thread.id,
                    content=full_content,
                    metadata={'model': model_key, 'stub': False, 'streamed': True}
                )
                done_payload = json.dumps({"message_id": str(assistant_message.id)})
                yield f"event: done\ndata: {done_payload}\n\n"

            response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"
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
