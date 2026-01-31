"""
Chat views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ChatThread, Message
from .serializers import (
    ChatThreadSerializer,
    ChatThreadDetailSerializer,
    MessageSerializer,
    CreateMessageSerializer,
)
from .services import ChatService
from tasks.workflows import assistant_response_workflow


class ChatThreadViewSet(viewsets.ModelViewSet):
    """ViewSet for chat threads"""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ChatThread.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatThreadDetailSerializer
        return ChatThreadSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def messages(self, request, pk=None):
        """
        Create a new message in this thread
        
        POST /api/chat/threads/{id}/messages/
        {
            "content": "Hello, world!"
        }
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
        return Message.objects.filter(thread__user=self.request.user)
