"""
Redis pub/sub for event-driven companion reflections.

Provides real-time event delivery from Celery tasks to SSE endpoints.
"""
import json
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


def get_redis_url() -> str:
    """Get Redis URL from Celery broker settings."""
    return getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')


def get_channel_name(thread_id: str) -> str:
    """Get Redis channel name for a thread."""
    return f"companion:thread:{thread_id}"


def publish_companion_event(thread_id: str, event_type: str, payload: Dict[str, Any]) -> bool:
    """
    Publish a companion event to Redis.

    Called from Celery tasks to send events to SSE subscribers.

    Args:
        thread_id: Thread ID to publish to
        event_type: Event type (reflection_start, reflection_chunk, etc.)
        payload: Event data

    Returns:
        True if published successfully
    """
    import redis

    try:
        # Parse Redis URL
        redis_url = get_redis_url()
        client = redis.from_url(redis_url)

        # Build message
        message = {
            'type': event_type,
            **payload
        }

        # Publish to channel
        channel = get_channel_name(thread_id)
        num_subscribers = client.publish(channel, json.dumps(message))

        logger.debug(
            "companion_event_published",
            extra={
                "thread_id": thread_id,
                "event_type": event_type,
                "subscribers": num_subscribers
            }
        )

        return True

    except Exception:
        logger.exception(
            "companion_event_publish_failed",
            extra={"thread_id": thread_id, "event_type": event_type}
        )
        return False


async def subscribe_to_companion_events(
    thread_id: str,
    heartbeat_interval: float = 30.0
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Subscribe to companion events for a thread.

    Async generator that yields events as they arrive.
    Used by SSE endpoint to forward events to clients.

    Args:
        thread_id: Thread ID to subscribe to
        heartbeat_interval: Seconds between heartbeat messages

    Yields:
        Event dictionaries with 'type' and payload
    """
    # Use redis.asyncio (built into redis>=4.2.0)
    import redis.asyncio as aioredis

    redis_url = get_redis_url()
    channel_name = get_channel_name(thread_id)

    redis_client = None
    pubsub = None

    try:
        # Create async Redis connection
        redis_client = aioredis.from_url(redis_url)
        pubsub = redis_client.pubsub()

        # Subscribe to channel
        await pubsub.subscribe(channel_name)
        logger.info(
            "companion_subscribed",
            extra={"thread_id": thread_id, "channel": channel_name}
        )

        last_heartbeat = asyncio.get_event_loop().time()

        while True:
            try:
                # Non-blocking receive with timeout for heartbeat
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=1.0  # Check every second
                )

                if message and message['type'] == 'message':
                    # Parse and yield event
                    data = json.loads(message['data'])
                    yield data

            except asyncio.TimeoutError:
                # No message received - check if heartbeat needed
                pass

            # Send heartbeat if needed
            current_time = asyncio.get_event_loop().time()
            if current_time - last_heartbeat >= heartbeat_interval:
                yield {'type': 'heartbeat'}
                last_heartbeat = current_time

    except asyncio.CancelledError:
        # Clean shutdown
        logger.info(
            "companion_unsubscribed",
            extra={"thread_id": thread_id}
        )
        raise

    except Exception:
        logger.exception(
            "companion_subscribe_error",
            extra={"thread_id": thread_id}
        )
        raise

    finally:
        # Cleanup
        try:
            if pubsub:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
            if redis_client:
                await redis_client.close()
        except Exception:
            pass


def publish_reflection_start(thread_id: str, trigger_type: str) -> bool:
    """Publish reflection start event."""
    return publish_companion_event(thread_id, 'reflection_start', {
        'trigger_type': trigger_type
    })


def publish_reflection_chunk(thread_id: str, delta: str) -> bool:
    """Publish reflection chunk (streaming token)."""
    return publish_companion_event(thread_id, 'reflection_chunk', {
        'delta': delta
    })


def publish_reflection_complete(
    thread_id: str,
    reflection_id: str,
    text: str,
    patterns: Dict,
    current_topic: Optional[str] = None
) -> bool:
    """Publish reflection complete event."""
    return publish_companion_event(thread_id, 'reflection_complete', {
        'id': reflection_id,
        'text': text,
        'patterns': patterns,
        'current_topic': current_topic
    })


def publish_background_update(thread_id: str, activity: Dict) -> bool:
    """Publish background activity update."""
    return publish_companion_event(thread_id, 'background_update', {
        'activity': activity
    })
