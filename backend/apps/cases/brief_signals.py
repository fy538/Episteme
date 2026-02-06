"""
Django signal handlers that trigger brief grounding recomputation.

Listens for changes to Signals, Evidence, and Inquiries that affect
the case brief. Triggers async evolve_brief_async via Celery task
with debouncing to avoid redundant recomputation.

Registered in CasesConfig.ready().
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='signals.Signal')
def on_signal_created(sender, instance, created, **kwargs):
    """
    When a new signal is extracted, trigger brief evolution
    for the associated case.
    """
    if created and instance.case_id:
        _schedule_brief_evolve(str(instance.case_id))


@receiver(post_save, sender='inquiries.Evidence')
def on_evidence_created(sender, instance, created, **kwargs):
    """
    When new evidence is added to an inquiry, trigger brief evolution.
    Evidence is linked to inquiry, which is linked to case.
    """
    if created:
        try:
            case_id = str(instance.inquiry.case_id)
            _schedule_brief_evolve(case_id)
        except Exception as e:
            logger.warning(f"Could not trigger brief evolve for evidence {instance.id}: {e}")


@receiver(post_save, sender='inquiries.Inquiry')
def on_inquiry_updated(sender, instance, **kwargs):
    """
    When an inquiry status changes, trigger brief evolution.
    This catches resolutions, conclusion changes, etc.
    """
    if instance.case_id:
        # Only trigger if status-related fields changed
        update_fields = kwargs.get('update_fields')
        if update_fields is None or any(
            f in (update_fields or [])
            for f in ('status', 'conclusion', 'description')
        ):
            _schedule_brief_evolve(str(instance.case_id))


def _schedule_brief_evolve(case_id: str):
    """
    Schedule async brief evolution with import-time safety.

    Attempts to use Celery task. Falls back to synchronous
    execution if Celery is not available (e.g., in tests).
    """
    try:
        from tasks.brief_tasks import evolve_brief_async
        evolve_brief_async.delay(case_id)
    except Exception as e:
        logger.warning(
            f"Could not schedule async brief evolve for case {case_id}: {e}. "
            "Falling back to synchronous execution."
        )
        try:
            from apps.cases.brief_grounding import BriefGroundingEngine
            BriefGroundingEngine.evolve_brief(case_id)
        except Exception as e2:
            logger.error(f"Synchronous brief evolve also failed for case {case_id}: {e2}")
