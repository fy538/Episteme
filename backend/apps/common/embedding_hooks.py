"""
Embedding generation hooks for searchable models.

Automatically generates embeddings when models are saved,
enabling fast semantic search without on-the-fly embedding generation.

Covered models:
  - Inquiry (pre_save) — title + description
  - Case (pre_save) — title + position
  - DecisionRecord (post_save) — decision_text + key_reasons + caveats
  - ProjectInsight (post_save) — title + content
  - ResearchResult (post_save) — question + answer (when status='complete')
  - ConversationStructure (post_save) — context_summary (also updates ChatThread.embedding)
  - ConversationEpisode (post_save) — content_summary (when sealed)
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


# ---------------------------------------------------------------------------
# DecisionRecord — post_save (created once, never edited)
# ---------------------------------------------------------------------------

def _decision_embedding_text(record) -> str:
    """Build embedding text from a DecisionRecord."""
    reasons = ' '.join(record.key_reasons) if record.key_reasons else ''
    return f"{record.decision_text} {reasons} {record.caveats or ''}"[:500]


@receiver(post_save, sender='cases.DecisionRecord')
def generate_decision_embedding(sender, instance, created, **kwargs):
    """Generate embedding when a DecisionRecord is created."""
    if not created or instance.embedding:
        return
    try:
        from apps.common.embeddings import generate_embedding
        text = _decision_embedding_text(instance)
        embedding = generate_embedding(text)
        if embedding:
            sender.objects.filter(pk=instance.pk).update(embedding=embedding)
    except Exception as e:
        logger.warning(f"Decision embedding generation failed: {e}")


# ---------------------------------------------------------------------------
# ProjectInsight — post_save (created once by agents)
# ---------------------------------------------------------------------------

def _insight_embedding_text(insight) -> str:
    """Build embedding text from a ProjectInsight."""
    return f"{insight.title} {insight.content}"[:500]


@receiver(post_save, sender='graph.ProjectInsight')
def generate_insight_embedding(sender, instance, created, **kwargs):
    """Generate embedding when a ProjectInsight is created."""
    if not created or instance.embedding:
        return
    try:
        from apps.common.embeddings import generate_embedding
        text = _insight_embedding_text(instance)
        embedding = generate_embedding(text)
        if embedding:
            sender.objects.filter(pk=instance.pk).update(embedding=embedding)
    except Exception as e:
        logger.warning(f"Insight embedding generation failed: {e}")


# ---------------------------------------------------------------------------
# ResearchResult — post_save (embed when status='complete')
# ---------------------------------------------------------------------------

def _research_embedding_text(result) -> str:
    """Build embedding text from a ResearchResult."""
    return f"{result.question} {result.answer}"[:500]


@receiver(post_save, sender='chat.ResearchResult')
def generate_research_embedding(sender, instance, **kwargs):
    """Generate embedding when a ResearchResult completes."""
    if instance.status != 'complete' or instance.embedding:
        return
    try:
        from apps.common.embeddings import generate_embedding
        text = _research_embedding_text(instance)
        embedding = generate_embedding(text)
        if embedding:
            sender.objects.filter(pk=instance.pk).update(embedding=embedding)
    except Exception as e:
        logger.warning(f"Research result embedding generation failed: {e}")


# ---------------------------------------------------------------------------
# Backfill: generic factory + per-model thin wrappers
# ---------------------------------------------------------------------------

def _backfill_embeddings(
    queryset,
    text_builder,
    label: str,
    batch_size: int = 100,
    verbose: bool = False,
    post_update=None,
) -> dict:
    """
    Generic backfill: fetch records missing embeddings, batch-generate, save.

    Args:
        queryset: Pre-filtered queryset of records needing embeddings.
        text_builder: Callable(record) -> str for embedding text.
        label: Human-readable model name for logging.
        batch_size: Max records per batch.
        verbose: Whether to log results.
        post_update: Optional callable(records, embeddings, stats) for
                     model-specific post-processing (e.g. thread propagation).
    """
    from apps.common.embeddings import generate_embeddings_batch

    stats = {'processed': 0, 'embedded': 0, 'failed': 0}

    records = list(queryset[:batch_size])
    if not records:
        return stats

    texts = [text_builder(r) for r in records]
    embeddings = generate_embeddings_batch(texts)

    for record, embedding in zip(records, embeddings):
        stats['processed'] += 1
        if embedding:
            record.embedding = embedding
            record.save(update_fields=['embedding'])
            stats['embedded'] += 1
        else:
            stats['failed'] += 1

    if post_update:
        post_update(records, embeddings, stats)

    if verbose:
        logger.info(f"Backfilled {label} embeddings: {stats}")

    return stats


def backfill_inquiry_embeddings(batch_size: int = 100, verbose: bool = False) -> dict:
    from apps.inquiries.models import Inquiry
    return _backfill_embeddings(
        queryset=Inquiry.objects.filter(embedding__isnull=True),
        text_builder=lambda inq: f"{inq.title} {inq.description or ''}"[:500],
        label='inquiry', batch_size=batch_size, verbose=verbose,
    )


def backfill_case_embeddings(batch_size: int = 100, verbose: bool = False) -> dict:
    from apps.cases.models import Case
    return _backfill_embeddings(
        queryset=Case.objects.filter(embedding__isnull=True),
        text_builder=lambda c: f"{c.title or ''} {c.position or ''}"[:500],
        label='case', batch_size=batch_size, verbose=verbose,
    )


def backfill_decision_embeddings(batch_size: int = 100, verbose: bool = False) -> dict:
    from apps.cases.models import DecisionRecord
    return _backfill_embeddings(
        queryset=DecisionRecord.objects.filter(embedding__isnull=True),
        text_builder=_decision_embedding_text,
        label='decision', batch_size=batch_size, verbose=verbose,
    )


def backfill_insight_embeddings(batch_size: int = 100, verbose: bool = False) -> dict:
    from apps.graph.models import ProjectInsight
    return _backfill_embeddings(
        queryset=ProjectInsight.objects.filter(embedding__isnull=True),
        text_builder=_insight_embedding_text,
        label='insight', batch_size=batch_size, verbose=verbose,
    )


def backfill_research_embeddings(batch_size: int = 100, verbose: bool = False) -> dict:
    from apps.chat.models import ResearchResult
    return _backfill_embeddings(
        queryset=ResearchResult.objects.filter(status='complete', embedding__isnull=True),
        text_builder=_research_embedding_text,
        label='research result', batch_size=batch_size, verbose=verbose,
    )


# ---------------------------------------------------------------------------
# ConversationStructure — post_save (updated on every companion cycle)
# Also propagates embedding to ChatThread for thread-level search
# ---------------------------------------------------------------------------

@receiver(post_save, sender='chat.ConversationStructure')
def generate_structure_embedding(sender, instance, **kwargs):
    """
    Generate embedding when a ConversationStructure is saved.

    Unlike most models, structures are versioned and updated frequently,
    so we generate on every save (not just creation).
    Also propagates the embedding to ChatThread for thread-level search.
    """
    context_summary = instance.context_summary or ''
    if len(context_summary) < 20:
        return

    try:
        from apps.common.embeddings import generate_embedding
        text = context_summary[:500]
        embedding = generate_embedding(text)
        if embedding:
            # Update structure embedding (avoid re-triggering signal via .update())
            sender.objects.filter(pk=instance.pk).update(embedding=embedding)

            # Also update ChatThread embedding (latest structure = thread embedding)
            from apps.chat.models import ChatThread
            ChatThread.objects.filter(id=instance.thread_id).update(embedding=embedding)
    except Exception as e:
        logger.warning(f"Structure embedding generation failed: {e}")


# ---------------------------------------------------------------------------
# ConversationEpisode — post_save (embed when sealed)
# ---------------------------------------------------------------------------

@receiver(post_save, sender='chat.ConversationEpisode')
def generate_episode_embedding(sender, instance, **kwargs):
    """Generate embedding when a ConversationEpisode is sealed."""
    if not instance.sealed or instance.embedding:
        return

    content_summary = instance.content_summary or ''
    if len(content_summary) < 20:
        return

    try:
        from apps.common.embeddings import generate_embedding
        text = content_summary[:500]
        embedding = generate_embedding(text)
        if embedding:
            sender.objects.filter(pk=instance.pk).update(embedding=embedding)
    except Exception as e:
        logger.warning(f"Episode embedding generation failed: {e}")


# ---------------------------------------------------------------------------
# Backfill: ConversationStructure embeddings
# (uses post_update hook for thread embedding propagation)
# ---------------------------------------------------------------------------

def _propagate_thread_embeddings(records, embeddings, stats):
    """Post-update hook: propagate latest structure embedding to ChatThread."""
    from apps.chat.models import ChatThread

    thread_embeddings = {}
    for structure, embedding in zip(records, embeddings):
        if embedding:
            thread_id = structure.thread_id
            if thread_id not in thread_embeddings:
                thread_embeddings[thread_id] = (structure.version, embedding)
            elif structure.version > thread_embeddings[thread_id][0]:
                thread_embeddings[thread_id] = (structure.version, embedding)

    for thread_id, (_, embedding) in thread_embeddings.items():
        ChatThread.objects.filter(id=thread_id).update(embedding=embedding)


def backfill_structure_embeddings(batch_size: int = 100, verbose: bool = False) -> dict:
    from apps.chat.models import ConversationStructure
    return _backfill_embeddings(
        queryset=ConversationStructure.objects.filter(
            embedding__isnull=True,
        ).exclude(context_summary='').select_related('thread'),
        text_builder=lambda s: s.context_summary[:500],
        label='structure', batch_size=batch_size, verbose=verbose,
        post_update=_propagate_thread_embeddings,
    )


# ---------------------------------------------------------------------------
# Backfill: ConversationEpisode embeddings
# ---------------------------------------------------------------------------

def backfill_episode_embeddings(batch_size: int = 100, verbose: bool = False) -> dict:
    from apps.chat.models import ConversationEpisode
    return _backfill_embeddings(
        queryset=ConversationEpisode.objects.filter(
            sealed=True, embedding__isnull=True,
        ).exclude(content_summary=''),
        text_builder=lambda ep: ep.content_summary[:500],
        label='episode', batch_size=batch_size, verbose=verbose,
    )
