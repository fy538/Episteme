"""
Signal handlers for companion app
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.inquiries.models import Inquiry
from apps.companion.models import InquiryHistory

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Inquiry)
def track_inquiry_confidence_change(sender, instance, created, **kwargs):
    """
    Automatically track confidence changes for inquiries.

    Creates an InquiryHistory entry whenever an inquiry's confidence is updated.
    This enables "75% → 45%" visualizations in the companion panel.

    Also triggers companion reflection if confidence change exceeds 20%
    (Silent Observer mode).
    """
    # Only track if inquiry has a confidence value
    if instance.conclusion_confidence is not None:
        # Get the last history entry to check if confidence actually changed
        last_entry = instance.confidence_history.first()

        old_confidence = last_entry.confidence if last_entry else None
        new_confidence = instance.conclusion_confidence

        # Create new history entry if:
        # 1. No previous entry (first time setting confidence), OR
        # 2. Confidence has changed
        if not last_entry or last_entry.confidence != new_confidence:
            InquiryHistory.objects.create(
                inquiry=instance,
                confidence=new_confidence,
                reason=f"Confidence {'set' if created else 'updated'} to {int(new_confidence * 100)}%"
            )

            # Check if confidence change is significant (>20%)
            # and trigger companion reflection
            if old_confidence is not None:
                delta = abs(new_confidence - old_confidence)

                if delta > 0.20:
                    # Get thread from inquiry's case
                    try:
                        case = instance.case
                        if case:
                            # Get the most recent thread for this case
                            thread = case.chat_threads.order_by('-updated_at').first()

                            if thread:
                                from apps.companion.tasks import generate_companion_reflection_task

                                generate_companion_reflection_task.delay(
                                    thread_id=str(thread.id),
                                    trigger_type='confidence_change',
                                    trigger_context={
                                        'inquiry_id': str(instance.id),
                                        'inquiry_title': instance.title,
                                        'old_confidence': old_confidence,
                                        'new_confidence': new_confidence,
                                        'delta': delta
                                    }
                                )
                                logger.info(
                                    "companion_reflection_triggered_by_confidence_change",
                                    extra={
                                        "inquiry_id": str(instance.id),
                                        "thread_id": str(thread.id),
                                        "delta": delta
                                    }
                                )
                    except Exception:
                        logger.exception(
                            "companion_reflection_trigger_failed_for_confidence_change",
                            extra={"inquiry_id": str(instance.id)}
                        )
