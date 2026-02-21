"""
Shared post-resolution hooks used by both DecisionService (legacy) and
ResolutionService (new auto-resolution flow).

Keeps the premortem scheduling, embedding generation, and event enhancement
logic in one place.
"""
import asyncio
import logging

from django.db import transaction

logger = logging.getLogger(__name__)


def schedule_premortem_comparison(case, record):
    """Schedule a premortem comparison after the transaction commits.

    Only fires if the case has premortem_text or what_would_change_mind set.
    Uses transaction.on_commit() to avoid running async code inside a
    transaction.

    Args:
        case: Case model instance (must have premortem_text, what_would_change_mind)
        record: DecisionRecord model instance
    """
    if not (case.premortem_text or case.what_would_change_mind):
        return

    def _schedule():
        try:
            from apps.chat.fact_promotion import compare_decision_to_premortem
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    compare_decision_to_premortem(record, case)
                )
            else:
                loop.run_until_complete(
                    compare_decision_to_premortem(record, case)
                )
        except Exception as e:
            logger.debug(f"Premortem comparison scheduling failed: {e}")

    transaction.on_commit(_schedule)


def schedule_embedding_generation(record, embed_text: str):
    """Generate and persist an embedding for the decision record after commit.

    Args:
        record: DecisionRecord model instance
        embed_text: Text to embed (typically decision_text + top reasons)
    """
    def _generate():
        try:
            from apps.common.vector_utils import generate_embedding
            from .models import DecisionRecord
            embedding = generate_embedding(embed_text)
            DecisionRecord.objects.filter(id=record.id).update(embedding=embedding)
        except Exception as e:
            logger.debug(f"Resolution embedding failed: {e}")

    transaction.on_commit(_generate)
