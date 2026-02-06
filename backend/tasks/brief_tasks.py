"""
Celery task for asynchronous brief grounding evolution.

Triggered by Django signal handlers in apps.cases.brief_signals
when Signals, Evidence, or Inquiries change.

Includes simple debounce via cache to avoid redundant recomputation
when multiple related changes happen in quick succession.
"""
import logging

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def evolve_brief_async(self, case_id: str):
    """
    Async brief evolution with simple debounce.

    Uses cache key to avoid redundant runs within 10 seconds.
    If another evolve was recently triggered for this case,
    this invocation is skipped.

    Args:
        case_id: UUID string of the case to evolve
    """
    cache_key = f"evolve_brief:{case_id}"

    # Simple debounce: skip if recently ran
    if cache.get(cache_key):
        logger.debug(f"Skipping brief evolve for case {case_id} (debounced)")
        return {'status': 'debounced', 'case_id': case_id}

    # Mark as running (10-second window)
    cache.set(cache_key, True, timeout=10)

    try:
        from apps.cases.brief_grounding import BriefGroundingEngine

        result = BriefGroundingEngine.evolve_brief(case_id)

        logger.info(
            f"Brief evolved for case {case_id}: "
            f"{result.get('sections_updated', 0)} sections updated, "
            f"{result.get('annotations_created', 0)} annotations created, "
            f"{result.get('annotations_resolved', 0)} annotations resolved"
        )

        # Optionally emit BRIEF_EVOLVED event
        try:
            from apps.events.services import EventService
            from apps.events.models import EventType, ActorType

            EventService.append(
                event_type=EventType.BRIEF_EVOLVED,
                payload={
                    'case_id': case_id,
                    'sections_updated': result.get('sections_updated', 0),
                    'annotations_created': result.get('annotations_created', 0),
                    'annotations_resolved': result.get('annotations_resolved', 0),
                },
                actor_type=ActorType.SYSTEM,
                case_id=case_id,
            )
        except Exception as e:
            logger.warning(f"Failed to emit BRIEF_EVOLVED event for case {case_id}: {e}")

        return {
            'status': 'success',
            'case_id': case_id,
            'sections_updated': result.get('sections_updated', 0),
        }

    except Exception as exc:
        logger.error(f"Brief evolve failed for case {case_id}: {exc}")
        # Clear cache so retry can proceed
        cache.delete(cache_key)
        raise self.retry(exc=exc)
