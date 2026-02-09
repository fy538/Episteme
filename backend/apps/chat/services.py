"""
Chat service
"""
import uuid
import logging
from typing import Optional, List
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.db import transaction
from django.conf import settings
from pydantic_ai import Agent

from .models import ChatThread, Message, MessageRole
from apps.events.services import EventService
from apps.events.models import EventType, ActorType
from apps.common.ai_models import get_model
from apps.chat.prompts import get_assistant_response_prompt

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for chat operations
    """
    
    @staticmethod
    def create_thread(user: User, title: str = "New Chat") -> ChatThread:
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
        user: User,
        metadata: dict | None = None,
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
            metadata: Optional metadata dict (mode_context, source info, etc.)

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
            metadata=metadata or {},
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
        Generate assistant response to user message.

        Args:
            thread_id: Thread ID
            user_message_id: User message to respond to

        Returns:
            Assistant Message
        """
        thread = ChatThread.objects.get(id=thread_id)
        user_message = Message.objects.get(id=user_message_id)

        if not settings.OPENAI_API_KEY:
            response_content = "OpenAI API key not configured locally."
            return ChatService.create_assistant_message(
                thread_id=thread_id,
                content=response_content,
                metadata={'stub': True, 'reason': 'missing_api_key'}
            )

        # Get recent conversation context
        context_messages = ChatService._get_context_messages(thread)
        conversation_context = ChatService._format_conversation_context(context_messages)

        # Build prompt
        prompt = get_assistant_response_prompt(
            user_message=user_message.content,
            conversation_context=conversation_context,
        )

        # Get user's preferred model (from preferences or fallback to settings)
        model_key = settings.AI_MODELS.get('chat', settings.AI_MODELS['fast'])
        
        # Check if user has custom model preference
        try:
            if hasattr(thread.user, 'preferences'):
                user_model = thread.user.preferences.chat_model
                if user_model:
                    model_key = user_model
                    logger.info(
                        "using_user_preferred_model",
                        extra={"user_id": str(thread.user.id), "model": user_model}
                    )
        except Exception as e:
            # Fallback to settings if preferences not available
            logger.debug(f"Could not load user model preference: {e}")
        
        agent = Agent(
            get_model(model_key),
            system_prompt=(
                "You are Episteme, a thoughtful assistant with memory. "
                "Be concise, reference relevant past context, and ask clarifying questions when useful."
            )
        )

        try:
            result = async_to_sync(agent.run)(prompt)
            response_content = result.data
        except Exception:
            logger.exception(
                "assistant_response_failed",
                extra={"thread_id": str(thread_id), "message_id": str(user_message_id)}
            )
            response_content = "Sorry, I hit an error generating a response."

        return ChatService.create_assistant_message(
            thread_id=thread_id,
            content=response_content,
            metadata={
                'model': model_key,
                'stub': False,
            }
        )

    @staticmethod
    def _get_context_messages(thread: ChatThread, limit: int = 6) -> List[Message]:
        recent = list(
            Message.objects.filter(thread=thread)
            .order_by('-created_at')[:limit]
        )
        return list(reversed(recent))

    @staticmethod
    def _format_conversation_context(messages: Optional[List[Message]]) -> str:
        if not messages:
            return ""
        recent = messages[-5:] if len(messages) > 5 else messages
        context_lines = []
        for msg in recent:
            role = msg.role.upper()
            content = msg.content[:400]
            if len(msg.content) > 400:
                content += "..."
            context_lines.append(f"{role}: {content}")
        return "\n".join(context_lines)
    
    @staticmethod
    @transaction.atomic
    def create_rich_message(
        thread_id: uuid.UUID,
        content_type: str,
        structured_content: dict,
        fallback_text: str,
        metadata: Optional[dict] = None
    ) -> Message:
        """
        Create a rich message (card) in a thread
        
        Args:
            thread_id: Thread to add message to
            content_type: Type of rich content (from MessageContentType)
            structured_content: Structured card data
            fallback_text: Plain text fallback for accessibility/search
            metadata: Optional metadata
            
        Returns:
            Created Message
        """
        thread = ChatThread.objects.get(id=thread_id)
        
        # 1. Append event
        event = EventService.append(
            event_type=EventType.ASSISTANT_MESSAGE_CREATED,
            payload={
                'thread_id': str(thread_id),
                'content': fallback_text,
                'content_type': content_type,
                'structured_content': structured_content,
                'metadata': metadata or {},
            },
            actor_type=ActorType.ASSISTANT,
            thread_id=thread_id,
        )
        
        # 2. Create message
        message = Message.objects.create(
            thread=thread,
            role=MessageRole.ASSISTANT,
            content=fallback_text,
            content_type=content_type,
            structured_content=structured_content,
            event_id=event.id,
            metadata=metadata or {},
        )
        
        logger.info(
            "rich_message_created",
            extra={
                "thread_id": str(thread_id),
                "message_id": str(message.id),
                "content_type": content_type
            }
        )
        
        return message
    
