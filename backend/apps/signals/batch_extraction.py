"""
Batch signal extraction with threshold-based triggering.

Combines Strategy 1 (selective extraction) and Strategy 2 (batched extraction):
- Accumulates messages until threshold met (char count OR turn count)
- Extracts from batch in single LLM call
- Resets counters after extraction
"""
import logging
import asyncio
from typing import List
from django.db.models import Q

from apps.chat.models import Message, MessageRole, ChatThread
from apps.signals.extractors import get_signal_extractor
from apps.events.services import EventService
from apps.events.models import EventType, ActorType

logger = logging.getLogger(__name__)


def should_trigger_batch_extraction(
    thread: ChatThread,
    char_threshold: int = 500,
    turn_threshold: int = 5
) -> bool:
    """
    Check if extraction threshold is met for this thread.
    
    Args:
        thread: ChatThread to check
        char_threshold: Minimum characters to accumulate (default: 500)
        turn_threshold: Minimum user messages to accumulate (default: 5)
        
    Returns:
        Boolean indicating if batch extraction should be triggered
    """
    return thread.should_extract_signals(char_threshold, turn_threshold)


def get_unprocessed_messages(thread: ChatThread) -> List[Message]:
    """
    Get user messages since last extraction.
    
    Uses last_extraction_at timestamp to find unprocessed messages.
    
    Args:
        thread: ChatThread to get messages from
        
    Returns:
        List of Message objects
    """
    query = Message.objects.filter(
        thread=thread,
        role=MessageRole.USER
    )
    
    # Filter by last extraction time
    if thread.last_extraction_at:
        query = query.filter(created_at__gt=thread.last_extraction_at)
    
    return list(query.order_by('created_at'))


async def extract_signals_from_batch_async(
    thread: ChatThread,
    messages: List[Message]
) -> int:
    """
    Extract signals from a batch of messages (async).
    
    Args:
        thread: ChatThread containing the messages
        messages: List of user messages to extract from
        
    Returns:
        Total number of signals extracted
    """
    if not messages:
        return 0
    
    extractor = get_signal_extractor()
    
    # Extract from batch in single LLM call
    signals_by_message = await extractor.extract_from_messages_batch(
        messages=messages,
        thread=thread
    )
    
    total_signals = 0
    
    # Save signals with event sourcing
    for message_id, signals in signals_by_message.items():
        for signal in signals:
            try:
                # Create event
                event = EventService.append(
                    event_type=EventType.SIGNAL_EXTRACTED,
                    payload={
                        'signal_type': signal.type,
                        'text': signal.text,
                        'confidence': signal.confidence,
                        'source_type': 'chat_message',
                        'batch_extraction': True,
                    },
                    actor_type=ActorType.SYSTEM,
                    case_id=thread.case_id if thread.case else None,
                )
                
                # Link event and save signal
                signal.event_id = event.id
                signal.case_id = thread.case_id if thread.case else None
                signal.save()
                
                total_signals += 1
                
            except Exception:
                logger.exception(
                    "batch_signal_save_failed",
                    extra={
                        "thread_id": str(thread.id),
                        "message_id": message_id,
                        "signal_type": signal.type
                    }
                )
                continue
    
    # Reset extraction counters
    thread.reset_extraction_counters()
    
    logger.info(
        "batch_signals_extracted",
        extra={
            "thread_id": str(thread.id),
            "messages_processed": len(messages),
            "signals_extracted": total_signals
        }
    )
    
    return total_signals


def extract_signals_from_batch(
    thread: ChatThread,
    messages: List[Message]
) -> int:
    """
    Sync wrapper for batch extraction.
    
    Args:
        thread: ChatThread containing the messages
        messages: List of user messages to extract from
        
    Returns:
        Total number of signals extracted
    """
    return asyncio.run(extract_signals_from_batch_async(thread, messages))
