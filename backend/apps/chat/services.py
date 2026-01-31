"""
Chat service
"""
import uuid
from typing import Optional
from django.contrib.auth.models import User
from django.db import transaction

from .models import ChatThread, Message, MessageRole
from apps.events.services import EventService
from apps.events.models import EventType, ActorType


class ChatService:
    """
    Service for chat operations
    """
    
    @staticmethod
    def create_thread(user: User, title: str = "") -> ChatThread:
        """
        Create a new chat thread
        
        Args:
            user: User who owns the thread
            title: Optional thread title
        
        Returns:
            Created ChatThread
        """
        thread = ChatThread.objects.create(
            user=user,
            title=title
        )
        return thread
    
    @staticmethod
    @transaction.atomic
    def create_user_message(
        thread_id: uuid.UUID,
        content: str,
        user: User
    ) -> Message:
        """
        Create a user message in a thread
        
        This follows the dual-write pattern:
        1. Append event (source of truth)
        2. Create message (read model)
        
        Args:
            thread_id: Thread to add message to
            content: Message content
            user: User sending the message
        
        Returns:
            Created Message
        """
        thread = ChatThread.objects.get(id=thread_id)
        
        # 1. Append event (source of truth)
        event = EventService.append(
            event_type=EventType.USER_MESSAGE_CREATED,
            payload={
                'thread_id': str(thread_id),
                'content': content,
                'user_id': str(user.id),
            },
            actor_type=ActorType.USER,
            actor_id=user.id,
            thread_id=thread_id,
        )
        
        # 2. Create message (read model)
        message = Message.objects.create(
            thread=thread,
            role=MessageRole.USER,
            content=content,
            event_id=event.id,
        )
        
        return message
    
    @staticmethod
    @transaction.atomic
    def create_assistant_message(
        thread_id: uuid.UUID,
        content: str,
        metadata: Optional[dict] = None
    ) -> Message:
        """
        Create an assistant message in a thread
        
        Args:
            thread_id: Thread to add message to
            content: Message content
            metadata: Optional metadata (model, latency, etc.)
        
        Returns:
            Created Message
        """
        thread = ChatThread.objects.get(id=thread_id)
        
        # 1. Append event (source of truth)
        event = EventService.append(
            event_type=EventType.ASSISTANT_MESSAGE_CREATED,
            payload={
                'thread_id': str(thread_id),
                'content': content,
                'metadata': metadata or {},
            },
            actor_type=ActorType.ASSISTANT,
            thread_id=thread_id,
        )
        
        # 2. Create message (read model)
        message = Message.objects.create(
            thread=thread,
            role=MessageRole.ASSISTANT,
            content=content,
            event_id=event.id,
            metadata=metadata or {},
        )
        
        return message
    
    @staticmethod
    def generate_assistant_response(
        thread_id: uuid.UUID,
        user_message_id: uuid.UUID
    ) -> Message:
        """
        Generate assistant response to user message
        
        Phase 0: Simple stub response
        Phase 1: Will call LLM and trigger signal extraction
        
        Args:
            thread_id: Thread ID
            user_message_id: User message to respond to
        
        Returns:
            Assistant Message
        """
        # Phase 0: Simple stub
        # TODO Phase 1: Call LLM, extract signals, etc.
        
        response_content = "Thank you for your message. I'm a Phase 0 stub response."
        
        return ChatService.create_assistant_message(
            thread_id=thread_id,
            content=response_content,
            metadata={'stub': True}
        )
