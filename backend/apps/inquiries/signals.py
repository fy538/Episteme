"""
Signals for inquiry lifecycle events.

Handles automatic actions when inquiries change state.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.inquiries.models import Inquiry, InquiryStatus

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Inquiry)
def auto_complete_checklist_on_inquiry_resolve(sender, instance, created, **kwargs):
    """
    When an inquiry is resolved, auto-complete any checklist items linked to it.

    This provides a seamless experience where resolving an inquiry automatically
    marks the related readiness checklist item as complete.
    """
    # Only trigger on updates (not creation) when status becomes RESOLVED
    if not created and instance.status == InquiryStatus.RESOLVED:
        from apps.cases.models import ReadinessChecklistItem

        # Find all incomplete checklist items linked to this inquiry
        items = ReadinessChecklistItem.objects.filter(
            linked_inquiry=instance,
            is_complete=False
        )

        if items.exists():
            logger.info(f"Auto-completing {items.count()} checklist items for resolved inquiry {instance.id}")

            for item in items:
                item.is_complete = True
                item.completed_at = timezone.now()

                # Create informative completion note
                conclusion_preview = instance.conclusion[:100] if instance.conclusion else "No conclusion provided"
                item.completion_note = f"Auto-completed when inquiry resolved: {conclusion_preview}"

                item.save(update_fields=['is_complete', 'completed_at', 'completion_note', 'updated_at'])

            logger.info(f"Successfully auto-completed {items.count()} checklist items")
