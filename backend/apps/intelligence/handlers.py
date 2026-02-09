"""
Post-processing handlers for unified analysis

Handles saving messages after stream completes.
"""

import uuid
import logging
from typing import Dict, Optional, Any

from apps.events.services import EventService
from apps.events.models import EventType, ActorType

logger = logging.getLogger(__name__)


class UnifiedAnalysisHandler:
    """
    Handles post-processing after unified analysis stream completes.

    Responsibilities:
    1. Save assistant message to DB
    2. Emit completion events
    """

    @staticmethod
    async def handle_completion(
        thread,
        user,
        response_content: str,
        reflection_content: str,
        model_key: str,
        correlation_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Handle completion of unified analysis.

        Args:
            thread: ChatThread object
            user: User object
            response_content: Full assistant response text
            reflection_content: Full reflection text
            model_key: Model used for generation
            correlation_id: Optional correlation ID for event tracking

        Returns:
            Dict with created object IDs
        """
        from asgiref.sync import sync_to_async
        from apps.chat.services import ChatService

        result = {
            'message_id': None,
        }

        correlation_id = correlation_id or uuid.uuid4()

        # 1. Save assistant message
        try:
            assistant_message = await sync_to_async(ChatService.create_assistant_message)(
                thread_id=thread.id,
                content=response_content,
                metadata={
                    'model': model_key,
                    'unified_stream': True,
                    'streamed': True
                }
            )
            result['message_id'] = str(assistant_message.id)
            logger.info(f"Saved assistant message: {assistant_message.id}")
        except Exception as e:
            logger.exception(f"Failed to save assistant message: {e}")
            raise

        # 2. Emit completion event
        try:
            await sync_to_async(EventService.append)(
                event_type=EventType.WORKFLOW_COMPLETED,
                payload={
                    'workflow_type': 'unified_analysis',
                    'thread_id': str(thread.id),
                    'message_id': result['message_id'],
                    'model': model_key
                },
                actor_type=ActorType.ASSISTANT,
                correlation_id=correlation_id,
                thread_id=thread.id
            )
        except Exception as e:
            logger.warning(f"Failed to emit completion event: {e}")

        return result
