"""
Signal handlers for companion app
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.inquiries.models import Inquiry
from apps.companion.models import InquiryHistory


@receiver(post_save, sender=Inquiry)
def track_inquiry_confidence_change(sender, instance, created, **kwargs):
    """
    Automatically track confidence changes for inquiries.
    
    Creates an InquiryHistory entry whenever an inquiry's confidence is updated.
    This enables "75% → 45%" visualizations in the companion panel.
    """
    # Only track if inquiry has a confidence value
    if instance.conclusion_confidence is not None:
        # Get the last history entry to check if confidence actually changed
        last_entry = instance.confidence_history.first()
        
        # Create new history entry if:
        # 1. No previous entry (first time setting confidence), OR
        # 2. Confidence has changed
        if not last_entry or last_entry.confidence != instance.conclusion_confidence:
            InquiryHistory.objects.create(
                inquiry=instance,
                confidence=instance.conclusion_confidence,
                reason=f"Confidence {'set' if created else 'updated'} to {int(instance.conclusion_confidence * 100)}%"
            )
