"""
Resolution Service — auto-generates case resolution records from case state.

When a user resolves a case (clicks a resolution type), this service:
1. Assembles the resolution record from case state (position, assumptions, graph)
2. Generates a narrative "resolution profile" via LLM
3. Creates the DecisionRecord and transitions the case

Integration:
    - CaseViewSet.record_decision() calls create_resolution() for the new flow
    - CaseViewSet.resolution_draft() calls generate_resolution_draft() for preview
"""
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.db import transaction

logger = logging.getLogger(__name__)

# Stakes → outcome check offset in days (resolution_type → stakes → days)
_OUTCOME_CHECK_DAYS = {
    'resolved': {'high': 30, 'medium': 60, 'low': 90},
    'closed': {'high': None, 'medium': None, 'low': None},
}


class ResolutionService:
    """Auto-generates and creates case resolution records."""

    @staticmethod
    def generate_resolution_draft(
        case_id,
        resolution_type: str = 'resolved',
    ) -> Dict:
        """
        Build a preview of what the auto-generated resolution would look like.

        Queries case state (position, plan assumptions, graph health) and
        assembles all resolution fields. Does NOT create anything.

        Args:
            case_id: UUID of the case
            resolution_type: 'resolved' or 'closed'

        Returns:
            Dict with all resolution fields ready for display or creation.
        """
        from .models import Case

        case = Case.objects.get(id=case_id)

        # --- Decision text from position ---
        decision_text = (case.position or '').strip()
        if not decision_text:
            decision_text = "No position established"

        # --- Plan assumptions + criteria ---
        assumptions = []
        criteria = []
        try:
            from .plan_service import PlanService
            plan, version = PlanService.get_current_version(case_id)
            content = version.content or {}
            assumptions = content.get('assumptions', [])
            criteria = content.get('decision_criteria', [])
        except Exception:
            logger.debug(f"No plan found for case {case_id}, using minimal resolution")

        # Categorize assumptions
        confirmed = [a for a in assumptions if a.get('status') == 'confirmed']
        untested = [a for a in assumptions if a.get('status') == 'untested']
        challenged = [a for a in assumptions if a.get('status') == 'challenged']
        untested_high_risk = [a for a in untested if a.get('risk_level') == 'high']
        met_criteria = [c for c in criteria if c.get('is_met')]

        # --- Key reasons: confirmed assumptions + met criteria ---
        key_reasons = []
        for a in confirmed:
            text = a.get('text', '')
            if text:
                key_reasons.append(text)
        for c in met_criteria:
            text = c.get('text', '')
            if text and text not in key_reasons:
                key_reasons.append(text)
        if not key_reasons:
            key_reasons = ["Based on investigation findings"]

        # --- Graph health ---
        graph_health = {}
        try:
            from apps.graph.services import GraphService
            graph_health = GraphService.compute_case_graph_health(case_id)
        except Exception:
            logger.debug(f"Could not compute graph health for case {case_id}")

        unresolved_tensions = graph_health.get('unresolved_tensions', 0)
        unsubstantiated_claims = graph_health.get('unsubstantiated_claims', 0)

        # --- Caveats from untested assumptions + tensions ---
        caveat_parts = []
        if untested_high_risk:
            texts = [a.get('text', '')[:80] for a in untested_high_risk[:3]]
            caveat_parts.append(
                f"Untested high-risk assumptions: {'; '.join(t for t in texts if t)}"
            )
        if unresolved_tensions:
            caveat_parts.append(
                f"{unresolved_tensions} unresolved tension(s) remain"
            )
        if challenged:
            texts = [a.get('text', '')[:80] for a in challenged[:2]]
            caveat_parts.append(
                f"Challenged assumptions: {'; '.join(t for t in texts if t)}"
            )
        caveats = ". ".join(caveat_parts)

        # --- Confidence (computed, for system use) ---
        confidence = 80
        confidence -= len(untested_high_risk) * 10
        confidence -= unresolved_tensions * 5
        confidence -= unsubstantiated_claims * 5
        confidence = max(0, min(100, confidence))

        # --- Linked assumption IDs (full snapshot) ---
        linked_assumption_ids = [a.get('id') for a in assumptions if a.get('id')]

        # --- Outcome check date ---
        stakes = getattr(case, 'stakes', 'medium') or 'medium'
        days = _OUTCOME_CHECK_DAYS.get(resolution_type, {}).get(stakes)
        outcome_check_date = (
            (date.today() + timedelta(days=days)).isoformat() if days else None
        )

        # --- Resolution profile (LLM narrative) ---
        resolution_profile = _generate_resolution_profile(
            resolution_type=resolution_type,
            decision_question=case.decision_question or '',
            decision_text=decision_text,
            confirmed_count=len(confirmed),
            untested_count=len(untested),
            high_risk_count=len(untested_high_risk),
            challenged_count=len(challenged),
            total_assumptions=len(assumptions),
            met_criteria_count=len(met_criteria),
            total_criteria=len(criteria),
            tension_count=unresolved_tensions,
        )

        return {
            'resolution_type': resolution_type,
            'decision_text': decision_text,
            'key_reasons': key_reasons,
            'confidence_level': confidence,
            'caveats': caveats,
            'linked_assumption_ids': linked_assumption_ids,
            'outcome_check_date': outcome_check_date,
            'resolution_profile': resolution_profile,
        }

    @staticmethod
    @transaction.atomic
    def create_resolution(
        user: User,
        case_id,
        resolution_type: str = 'resolved',
        overrides: Optional[Dict] = None,
    ):
        """
        Auto-generate and create a resolution record for a case.

        Args:
            user: User resolving the case
            case_id: Case UUID
            resolution_type: How the case was resolved
            overrides: Optional dict of fields to override the auto-generated values

        Returns:
            Created DecisionRecord

        Raises:
            Case.DoesNotExist: If case not found or not owned by user
            ValueError: If case already has a decision or is not active
        """
        from .models import Case, CaseStatus, DecisionRecord
        from apps.events.services import EventService
        from apps.events.models import EventType, ActorType

        case = Case.objects.select_for_update().get(id=case_id, user=user)

        # Validate: can't resolve twice
        if hasattr(case, 'decision'):
            try:
                case.decision
                raise ValueError("Case already has a recorded resolution")
            except DecisionRecord.DoesNotExist:
                pass

        # Validate: case must be active
        if case.status != CaseStatus.ACTIVE:
            raise ValueError(f"Cannot resolve case with status '{case.status}'")

        # Auto-generate all fields
        draft = ResolutionService.generate_resolution_draft(
            case_id=case_id,
            resolution_type=resolution_type,
        )

        # Apply overrides
        if overrides:
            for key, value in overrides.items():
                if key in draft and value:
                    draft[key] = value

        # Parse outcome_check_date from string if needed
        outcome_check_date = draft.get('outcome_check_date')
        if isinstance(outcome_check_date, str):
            outcome_check_date = date.fromisoformat(outcome_check_date)

        # Create record
        record = DecisionRecord.objects.create(
            case=case,
            resolution_type=draft['resolution_type'],
            resolution_profile=draft.get('resolution_profile', ''),
            decision_text=draft['decision_text'],
            key_reasons=draft['key_reasons'],
            confidence_level=max(0, min(100, draft['confidence_level'])),
            caveats=draft.get('caveats', ''),
            linked_assumption_ids=draft.get('linked_assumption_ids', []),
            outcome_check_date=outcome_check_date,
        )

        # Transition case
        case.status = CaseStatus.DECIDED
        case.save(update_fields=['status', 'updated_at'])

        # Emit event
        EventService.append(
            event_type=EventType.DECISION_RECORDED,
            payload={
                'decision_id': str(record.id),
                'resolution_type': resolution_type,
                'decision_text': draft['decision_text'][:200],
                'confidence_level': draft['confidence_level'],
                'reasons_count': len(draft['key_reasons']),
                'has_outcome_check': outcome_check_date is not None,
            },
            actor_type=ActorType.USER,
            actor_id=user.id,
            case_id=case.id,
        )

        logger.info(
            "resolution_created",
            extra={
                'case_id': str(case_id),
                'resolution_type': resolution_type,
                'confidence': draft['confidence_level'],
            }
        )

        # Post-resolution hooks (shared with DecisionService)
        from ._resolution_hooks import schedule_premortem_comparison, schedule_embedding_generation
        schedule_premortem_comparison(case, record)
        embed_text = f"{draft['decision_text']} {' '.join(draft['key_reasons'][:3])}"
        schedule_embedding_generation(record, embed_text)

        return record


def _generate_resolution_profile(
    resolution_type: str,
    decision_question: str,
    decision_text: str,
    confirmed_count: int,
    untested_count: int,
    high_risk_count: int,
    challenged_count: int,
    total_assumptions: int,
    met_criteria_count: int,
    total_criteria: int,
    tension_count: int,
) -> str:
    """
    Generate an LLM narrative characterizing the resolution quality.

    Uses the 'fast' provider with the same async_to_sync pattern as
    CaseAnalysisService._detect_blind_spots.

    Returns:
        2-3 sentence narrative string, or empty string on failure.
    """
    # Skip LLM call if there's almost no case state to characterize
    if not decision_question and total_assumptions == 0:
        return ""

    type_guidance = {
        'resolved': "Describe the confidence basis, what's well-supported and what's being bet on without proof.",
        'closed': "Describe why this was closed without resolution — what remains unclear and what would need to change.",
    }

    prompt = f"""Characterize this case resolution in 2-3 sentences. Be specific and candid — reference the actual numbers.

Decision question: {decision_question}
Position taken: {decision_text}
Resolution type: {resolution_type}

Investigation state:
- Assumptions: {confirmed_count} confirmed, {untested_count} untested ({high_risk_count} high-risk), {challenged_count} challenged out of {total_assumptions} total
- Decision criteria: {met_criteria_count} of {total_criteria} met
- Unresolved tensions: {tension_count}

{type_guidance.get(resolution_type, '')}

Return ONLY the narrative text, no JSON, no labels, no quotes."""

    try:
        from apps.common.llm_providers import get_llm_provider
        provider = get_llm_provider('fast')

        async def _call():
            return await provider.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=(
                    "You generate candid, specific resolution profiles for case investigations. "
                    "Be concise (2-3 sentences). Reference concrete numbers from the investigation state. "
                    "Do not be generic or congratulatory."
                ),
                max_tokens=300,
                temperature=0.3,
            )

        result = async_to_sync(_call)()
        # The result should be plain text, strip any accidental wrapping
        profile = result.strip().strip('"').strip("'")
        return profile
    except Exception:
        logger.warning("Failed to generate resolution profile", exc_info=True)
        return ""
