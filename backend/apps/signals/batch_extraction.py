"""
Batch signal extraction with threshold-based triggering.

Combines Strategy 1 (selective extraction) and Strategy 2 (batched extraction):
- Accumulates messages until threshold met (char count OR turn count)
- Extracts from batch in single LLM call
- Resets counters after extraction
"""
import logging
from typing import List
from asgiref.sync import async_to_sync
from django.db.models import Q
from django.db import transaction

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


@transaction.atomic
async def extract_signals_from_batch_async(
    thread: ChatThread,
    messages: List[Message]
) -> int:
    """
    Extract signals from a batch of messages (async).
    
    Uses bulk_create for efficiency and wraps in transaction for atomicity.
    
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
    
    # Collect all signals and create events in bulk
    all_signals = []
    event_signal_pairs = []
    
    for message_id, signals in signals_by_message.items():
        for signal in signals:
            try:
                # Create event (still individual for now, but in same transaction)
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
                    case_id=thread.primary_case_id if thread.primary_case else None,
                )
                
                # Link event and case to signal
                signal.event_id = event.id
                signal.case_id = thread.primary_case_id if thread.primary_case else None
                
                all_signals.append(signal)
                event_signal_pairs.append((event, signal))
                
            except Exception:
                logger.exception(
                    "batch_signal_event_creation_failed",
                    extra={
                        "thread_id": str(thread.id),
                        "message_id": message_id,
                        "signal_type": signal.type
                    }
                )
                # Continue with other signals - transaction will roll back all on outer error
                continue
    
    # Bulk create all signals in one query
    if all_signals:
        from apps.signals.models import Signal
        Signal.objects.bulk_create(all_signals)
        
        logger.info(
            "batch_signals_created",
            extra={
                "thread_id": str(thread.id),
                "signals_created": len(all_signals)
            }
        )
    
    # Reset extraction counters (inside transaction)
    thread.reset_extraction_counters()
    
    total_signals = len(all_signals)
    
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
    return async_to_sync(extract_signals_from_batch_async)(thread, messages)
