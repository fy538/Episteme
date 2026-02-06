"""
Embedding generation hooks for Inquiry and Case models.

Automatically generates embeddings when these models are saved,
enabling fast semantic search without on-the-fly embedding generation.
"""
import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def generate_inquiry_embedding(inquiry) -> list | None:
    """Generate embedding for an inquiry based on title + description."""
    from apps.common.embeddings import generate_embedding

    text = f"{inquiry.title} {inquiry.description or ''}"[:500]  # Limit length
    return generate_embedding(text)


def generate_case_embedding(case) -> list | None:
    """Generate embedding for a case based on title + position."""
    from apps.common.embeddings import generate_embedding

    text = f"{case.title or ''} {case.position or ''}"[:500]  # Limit length
    return generate_embedding(text)


@receiver(pre_save, sender='inquiries.Inquiry')
def update_inquiry_embedding(sender, instance, **kwargs):
    """
    Update embedding when inquiry title or description changes.

    Uses pre_save to avoid infinite loops and to check if content changed.
    """
    # Skip if we're just loading from DB
    if instance._state.adding:
        # New inquiry - will generate embedding
        instance.embedding = generate_inquiry_embedding(instance)
        return

    try:
        # Check if title or description changed
        old_instance = sender.objects.get(pk=instance.pk)
        if (old_instance.title != instance.title or
                old_instance.description != instance.description):
            instance.embedding = generate_inquiry_embedding(instance)
    except sender.DoesNotExist:
        # New record
        instance.embedding = generate_inquiry_embedding(instance)


@receiver(pre_save, sender='cases.Case')
def update_case_embedding(sender, instance, **kwargs):
    """
    Update embedding when case title or position changes.
    """
    # Skip if we're just loading from DB
    if instance._state.adding:
        # New case - will generate embedding
        instance.embedding = generate_case_embedding(instance)
        return

    try:
        # Check if title or position changed
        old_instance = sender.objects.get(pk=instance.pk)
        if (old_instance.title != instance.title or
                old_instance.position != instance.position):
            instance.embedding = generate_case_embedding(instance)
    except sender.DoesNotExist:
        # New record
        instance.embedding = generate_case_embedding(instance)


def backfill_inquiry_embeddings(batch_size: int = 100, verbose: bool = False) -> dict:
    """
    Backfill embeddings for existing inquiries without embeddings.

    Returns stats: {processed, embedded, failed}
    """
    from apps.inquiries.models import Inquiry
    from apps.common.embeddings import generate_embeddings_batch

    stats = {'processed': 0, 'embedded': 0, 'failed': 0}

    # Get inquiries without embeddings
    inquiries = list(Inquiry.objects.filter(embedding__isnull=True)[:batch_size])

    if not inquiries:
        return stats

    # Prepare texts
    texts = [f"{inq.title} {inq.description or ''}"[:500] for inq in inquiries]

    # Batch generate embeddings
    embeddings = generate_embeddings_batch(texts)

    # Update inquiries
    for inquiry, embedding in zip(inquiries, embeddings):
        stats['processed'] += 1
        if embedding:
            inquiry.embedding = embedding
            inquiry.save(update_fields=['embedding'])
            stats['embedded'] += 1
        else:
            stats['failed'] += 1

    if verbose:
        logger.info(f"Backfilled inquiry embeddings: {stats}")

    return stats


def backfill_case_embeddings(batch_size: int = 100, verbose: bool = False) -> dict:
    """
    Backfill embeddings for existing cases without embeddings.

    Returns stats: {processed, embedded, failed}
    """
    from apps.cases.models import Case
    from apps.common.embeddings import generate_embeddings_batch

    stats = {'processed': 0, 'embedded': 0, 'failed': 0}

    # Get cases without embeddings
    cases = list(Case.objects.filter(embedding__isnull=True)[:batch_size])

    if not cases:
        return stats

    # Prepare texts
    texts = [f"{case.title or ''} {case.position or ''}"[:500] for case in cases]

    # Batch generate embeddings
    embeddings = generate_embeddings_batch(texts)

    # Update cases
    for case, embedding in zip(cases, embeddings):
        stats['processed'] += 1
        if embedding:
            case.embedding = embedding
            case.save(update_fields=['embedding'])
            stats['embedded'] += 1
        else:
            stats['failed'] += 1

    if verbose:
        logger.info(f"Backfilled case embeddings: {stats}")

    return stats
