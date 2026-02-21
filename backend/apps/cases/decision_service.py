"""
Decision service — record decisions and track outcomes
"""
import logging
import uuid
from datetime import date
from typing import Optional, List

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import Case, CaseStatus, DecisionRecord
from apps.events.services import EventService
from apps.events.models import EventType, ActorType

logger = logging.getLogger(__name__)


class DecisionService:
    """Service for recording decisions and tracking outcomes."""

    @staticmethod
    @transaction.atomic
    def record_decision(
        user: User,
        case_id: uuid.UUID,
        decision_text: str,
        key_reasons: List[str],
        confidence_level: int,
        caveats: str = "",
        linked_assumption_ids: Optional[List[str]] = None,
        outcome_check_date: Optional[date] = None,
    ) -> DecisionRecord:
        """
        Record a formal decision for a case.

        Creates a DecisionRecord, transitions the case to DECIDED status,
        and emits a DECISION_RECORDED provenance event.

        Args:
            user: User recording the decision
            case_id: Case UUID
            decision_text: What was decided
            key_reasons: List of reason strings
            confidence_level: 0-100 confidence
            caveats: Optional risk notes
            linked_assumption_ids: UUIDs of validated assumptions
            outcome_check_date: Optional date to check outcomes

        Returns:
            Created DecisionRecord

        Raises:
            Case.DoesNotExist: If case not found or not owned by user
            ValueError: If case already has a decision or is not active
        """
        case = Case.objects.select_for_update().get(id=case_id, user=user)

        # Validate: can't decide twice
        if hasattr(case, 'decision'):
            try:
                case.decision
                raise ValueError("Case already has a recorded decision")
            except DecisionRecord.DoesNotExist:
                pass  # No decision exists — proceed

        # Validate: case must be active (not draft or archived)
        if case.status not in (CaseStatus.ACTIVE,):
            raise ValueError(f"Cannot record decision on case with status '{case.status}'")

        # Create decision record
        record = DecisionRecord.objects.create(
            case=case,
            decision_text=decision_text,
            key_reasons=key_reasons,
            confidence_level=max(0, min(100, confidence_level)),
            caveats=caveats,
            linked_assumption_ids=linked_assumption_ids or [],
            outcome_check_date=outcome_check_date,
        )

        # Transition case status
        case.status = CaseStatus.DECIDED
        case.save(update_fields=['status', 'updated_at'])

        # Emit provenance event
        EventService.append(
            event_type=EventType.DECISION_RECORDED,
            payload={
                'decision_id': str(record.id),
                'resolution_type': 'resolved',  # legacy path always records as resolved
                'decision_text': decision_text[:200],
                'confidence_level': confidence_level,
                'reasons_count': len(key_reasons),
                'has_outcome_check': outcome_check_date is not None,
            },
            actor_type=ActorType.USER,
            actor_id=user.id,
            case_id=case.id,
        )

        logger.info(
            "decision_recorded",
            extra={
                'case_id': str(case_id),
                'confidence': confidence_level,
                'reasons_count': len(key_reasons),
            }
        )

        # Post-resolution hooks (shared with ResolutionService)
        from ._resolution_hooks import schedule_premortem_comparison, schedule_embedding_generation
        schedule_premortem_comparison(case, record)
        embed_text = f"{decision_text} {' '.join(key_reasons[:3])}"
        schedule_embedding_generation(record, embed_text)

        return record

    @staticmethod
    @transaction.atomic
    def add_outcome_note(
        user: User,
        case_id: uuid.UUID,
        note: str,
        sentiment: str = "neutral",
    ) -> DecisionRecord:
        """
        Add an outcome observation to an existing decision.

        Args:
            user: User adding the note
            case_id: Case UUID
            note: Outcome observation text
            sentiment: 'positive', 'neutral', 'negative', or 'mixed'

        Returns:
            Updated DecisionRecord

        Raises:
            DecisionRecord.DoesNotExist: If no decision exists for this case
        """
        case = Case.objects.get(id=case_id, user=user)
        record = DecisionRecord.objects.select_for_update().get(case=case)

        # Append note
        notes = record.outcome_notes or []
        notes.append({
            'date': timezone.now().isoformat(),
            'note': note,
            'sentiment': sentiment,
        })
        record.outcome_notes = notes
        record.save(update_fields=['outcome_notes', 'updated_at'])

        # Emit event
        EventService.append(
            event_type=EventType.OUTCOME_NOTE_ADDED,
            payload={
                'decision_id': str(record.id),
                'note_index': len(notes) - 1,
                'sentiment': sentiment,
            },
            actor_type=ActorType.USER,
            actor_id=user.id,
            case_id=case.id,
        )

        return record
