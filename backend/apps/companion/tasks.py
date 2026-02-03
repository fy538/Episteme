"""
Celery tasks for event-driven companion reflections.

Triggers reflections based on significant events (Silent Observer mode).
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def generate_companion_reflection_task(
    thread_id: str,
    trigger_type: str,
    trigger_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a companion reflection asynchronously.

    Called after significant events (signal extraction, contradictions, etc.).
    Streams tokens via Redis pub/sub to SSE subscribers.

    Args:
        thread_id: Thread ID to generate reflection for
        trigger_type: What triggered this reflection
        trigger_context: Additional context about the trigger

    Returns:
        Result with reflection ID and status
    """
    from apps.companion.pubsub import (
        publish_reflection_start,
        publish_reflection_chunk,
        publish_reflection_complete,
    )
    from apps.companion.services import CompanionService
    from apps.companion.models import Reflection, ReflectionTriggerType

    try:
        # Publish start event
        publish_reflection_start(thread_id, trigger_type)

        # Run async reflection generation
        result = asyncio.run(_generate_reflection_async(
            thread_id=thread_id,
            trigger_type=trigger_type,
            trigger_context=trigger_context
        ))

        return result

    except Exception:
        logger.exception(
            "companion_reflection_task_failed",
            extra={
                "thread_id": thread_id,
                "trigger_type": trigger_type
            }
        )
        return {
            'status': 'failed',
            'thread_id': thread_id
        }


async def _generate_reflection_async(
    thread_id: str,
    trigger_type: str,
    trigger_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Async implementation of reflection generation.

    Streams tokens to Redis pub/sub as they're generated.
    Uses memory-aware prompts for continuity.
    """
    from apps.companion.pubsub import (
        publish_reflection_chunk,
        publish_reflection_complete,
    )
    from apps.companion.services import CompanionService
    from apps.companion.models import Reflection, ReflectionTriggerType
    from apps.companion.memory import CompanionMemory
    from asgiref.sync import sync_to_async

    companion = CompanionService()

    # Prepare context
    context = await companion.prepare_reflection_context(thread_id=thread_id)
    thread = context['thread']

    # Get memory context for continuity
    memory_context = await sync_to_async(CompanionMemory.get_memory_context)(thread)

    # Extract current topic
    current_topic = companion.extract_current_topic(context['recent_messages'])

    # Stream reflection token-by-token (with memory)
    full_reflection_text = ""

    async for token in companion.stream_reflection_with_memory(
        thread=thread,
        recent_messages=context['recent_messages'],
        current_signals=context['current_signals'],
        patterns=context['patterns'],
        memory_context=memory_context
    ):
        full_reflection_text += token

        # Publish each token to Redis
        publish_reflection_chunk(thread_id, token)

    # Map trigger_type string to enum
    trigger_type_map = {
        'signals_extracted': ReflectionTriggerType.USER_MESSAGE,
        'contradiction_detected': ReflectionTriggerType.CONTRADICTION_DETECTED,
        'confidence_change': ReflectionTriggerType.CONFIDENCE_CHANGE,
        'document_upload': ReflectionTriggerType.DOCUMENT_UPLOAD,
        'periodic': ReflectionTriggerType.PERIODIC,
    }
    reflection_trigger = trigger_type_map.get(
        trigger_type,
        ReflectionTriggerType.PERIODIC
    )

    # Save completed reflection to database
    reflection = await sync_to_async(Reflection.objects.create)(
        thread=thread,
        reflection_text=full_reflection_text.strip(),
        trigger_type=reflection_trigger,
        analyzed_messages=[str(m['id']) for m in context['recent_messages']],
        analyzed_signals=[str(s['id']) for s in context['current_signals']],
        patterns=context['patterns']
    )

    # Update companion memory with new reflection
    await sync_to_async(CompanionMemory.update_memory)(thread, reflection)

    # Publish completion event
    publish_reflection_complete(
        thread_id=thread_id,
        reflection_id=str(reflection.id),
        text=full_reflection_text.strip(),
        patterns=context['patterns'],
        current_topic=current_topic
    )

    logger.info(
        "companion_reflection_generated",
        extra={
            "thread_id": thread_id,
            "reflection_id": str(reflection.id),
            "trigger_type": trigger_type,
            "text_length": len(full_reflection_text),
            "has_memory": bool(memory_context.get('recent_reflections'))
        }
    )

    return {
        'status': 'completed',
        'reflection_id': str(reflection.id),
        'thread_id': thread_id,
        'trigger_type': trigger_type
    }


def should_trigger_reflection(
    trigger_type: str,
    trigger_context: Dict[str, Any]
) -> bool:
    """
    Determine if a reflection should be triggered (Silent Observer mode).

    Only triggers on significant events to avoid noise.

    Args:
        trigger_type: Type of trigger event
        trigger_context: Context data for the trigger

    Returns:
        True if reflection should be generated
    """
    if trigger_type == 'signals_extracted':
        # Only trigger if 5+ signals were extracted
        signals_count = trigger_context.get('signals_count', 0)
        return signals_count >= 5

    elif trigger_type == 'contradiction_detected':
        # Always trigger on contradictions
        return True

    elif trigger_type == 'confidence_change':
        # Only trigger if confidence changed by >20%
        old_confidence = trigger_context.get('old_confidence', 0)
        new_confidence = trigger_context.get('new_confidence', 0)
        delta = abs(new_confidence - old_confidence)
        return delta > 0.20

    elif trigger_type == 'inquiry_created':
        # Trigger when new inquiry is created
        return True

    elif trigger_type == 'strong_claim':
        # Trigger on high-confidence claims (>80%)
        confidence = trigger_context.get('confidence', 0)
        return confidence > 0.80

    # Default: don't trigger
    return False


@shared_task
def maybe_trigger_companion_reflection(
    thread_id: str,
    trigger_type: str,
    trigger_context: Dict[str, Any]
) -> Optional[str]:
    """
    Conditionally trigger a companion reflection.

    Checks if the trigger meets Silent Observer thresholds before generating.

    Args:
        thread_id: Thread ID
        trigger_type: Type of trigger event
        trigger_context: Context data for the trigger

    Returns:
        Task ID if triggered, None otherwise
    """
    if should_trigger_reflection(trigger_type, trigger_context):
        logger.info(
            "companion_reflection_triggered",
            extra={
                "thread_id": thread_id,
                "trigger_type": trigger_type,
                "context": trigger_context
            }
        )

        # Trigger the actual reflection task
        result = generate_companion_reflection_task.delay(
            thread_id=thread_id,
            trigger_type=trigger_type,
            trigger_context=trigger_context
        )
        return result.id

    else:
        logger.debug(
            "companion_reflection_skipped",
            extra={
                "thread_id": thread_id,
                "trigger_type": trigger_type,
                "reason": "threshold_not_met"
            }
        )
        return None
