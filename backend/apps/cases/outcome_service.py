"""
Outcome Review Service

Surfaces overdue decision reviews contextually — not as push notifications,
but as companion-injected context when the user interacts with a decided case
or visits the project dashboard.

Integration:
    - ContextAssemblyService._resolve_case_mode() checks per-case reviews
    - ContextAssemblyService.assemble() checks project-wide pending reviews
"""
import logging
from datetime import date, timedelta
from typing import List, Optional

from django.db.models import Q

logger = logging.getLogger(__name__)


class OutcomeReviewService:
    """Surfaces overdue outcome reviews as contextual companion nudges."""

    @staticmethod
    def get_pending_reviews(user, project_id=None, limit: int = 5) -> List[dict]:
        """
        Find decisions with outcome_check_date <= today and no recent outcome note.

        Args:
            user: Authenticated user
            project_id: Optional scope to a specific project
            limit: Max results to return

        Returns:
            List of dicts: [{decision_id, case_id, case_title, decision_text,
                             resolution_type, resolution_profile, days_overdue, last_note_date}]
        """
        from .models import DecisionRecord

        queryset = DecisionRecord.objects.filter(
            case__user=user,
            outcome_check_date__lte=date.today(),
        ).exclude(
            resolution_type='closed',
        ).select_related('case')

        if project_id:
            queryset = queryset.filter(case__project_id=project_id)

        # Exclude decisions with an outcome note in the last 7 days
        # We check this in Python since outcome_notes is a JSONField
        results = []
        for record in queryset.order_by('outcome_check_date')[:limit * 2]:
            # Check if there's a recent outcome note
            if record.outcome_notes:
                latest_note = record.outcome_notes[-1]
                note_date_str = latest_note.get('date', '')
                if note_date_str:
                    try:
                        # Parse ISO date and check if recent
                        note_date = date.fromisoformat(note_date_str[:10])
                        if (date.today() - note_date) < timedelta(days=7):
                            continue  # Skip — recently reviewed
                    except (ValueError, TypeError):
                        pass

            days_overdue = (date.today() - record.outcome_check_date).days

            last_note_date = None
            if record.outcome_notes:
                last_note_date = record.outcome_notes[-1].get('date', '')[:10]

            results.append({
                'decision_id': str(record.id),
                'case_id': str(record.case_id),
                'case_title': record.case.title[:60] if record.case else 'Unknown',
                'decision_text': record.decision_text[:200],
                'resolution_type': getattr(record, 'resolution_type', 'resolved'),
                'resolution_profile': getattr(record, 'resolution_profile', '')[:200],
                'days_overdue': days_overdue,
                'last_note_date': last_note_date,
            })

            if len(results) >= limit:
                break

        return results

    @staticmethod
    def get_review_for_case(case_id) -> Optional[dict]:
        """
        Check if a specific case has a pending outcome review.

        Args:
            case_id: UUID of the case

        Returns:
            Review dict or None
        """
        from .models import DecisionRecord

        try:
            record = DecisionRecord.objects.filter(
                case_id=case_id,
                outcome_check_date__lte=date.today(),
            ).exclude(
                resolution_type='closed',
            ).first()

            if not record:
                return None

            # Check for recent outcome note
            if record.outcome_notes:
                latest_note = record.outcome_notes[-1]
                note_date_str = latest_note.get('date', '')
                if note_date_str:
                    try:
                        note_date = date.fromisoformat(note_date_str[:10])
                        if (date.today() - note_date) < timedelta(days=7):
                            return None  # Recently reviewed
                    except (ValueError, TypeError):
                        pass

            days_overdue = (date.today() - record.outcome_check_date).days
            decided_at = record.decided_at.strftime('%Y-%m-%d') if record.decided_at else '?'

            return {
                'decision_id': str(record.id),
                'decision_text': record.decision_text[:200],
                'resolution_type': getattr(record, 'resolution_type', 'resolved'),
                'resolution_profile': getattr(record, 'resolution_profile', '')[:200],
                'decided_at': decided_at,
                'outcome_check_date': str(record.outcome_check_date),
                'days_overdue': days_overdue,
                'outcome_notes_count': len(record.outcome_notes or []),
            }

        except Exception as e:
            logger.debug(f"Outcome review check failed for case {case_id}: {e}")
            return None
