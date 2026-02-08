"""
Assumption Status Cascade

When evidence is linked to or unlinked from an assumption Signal,
recompute the assumption's status based on evidence balance:

- No evidence -> untested
- Only supporting evidence -> confirmed
- Only contradicting evidence -> refuted
- Both supporting AND contradicting -> challenged
- More supporting than contradicting -> confirmed (with note)
- More contradicting than supporting -> challenged

After updating assumption status, trigger brief grounding recalculation
to keep the three-way loop closed:
  Evidence -> Assumption Status -> Brief Grounding
"""
import logging
from typing import Optional

from django.db import transaction

import threading

# Thread-local cascade depth tracking to prevent infinite loops
_cascade_local = threading.local()
MAX_CASCADE_DEPTH = 3

logger = logging.getLogger(__name__)


def recompute_assumption_status(signal) -> Optional[str]:
    """
    Recompute and update an assumption Signal's status based on evidence balance.

    Only applies to Signals with type='Assumption'.

    Returns: The new status string, or None if not applicable.
    """
    from apps.signals.models import SignalType
    if signal.type != SignalType.ASSUMPTION:
        return None

    from django.db.models import Count, Q
    counts = type(signal).objects.filter(pk=signal.pk).aggregate(
        supporting=Count('supported_by_evidence'),
        contradicting=Count('contradicted_by_evidence'),
    )
    supporting_count = counts['supporting']
    contradicting_count = counts['contradicting']
    total = supporting_count + contradicting_count

    if total == 0:
        new_status = 'untested'
    elif contradicting_count == 0:
        new_status = 'confirmed'
    elif supporting_count == 0:
        new_status = 'refuted'
    else:
        # Mixed evidence -- compare balance
        if supporting_count > contradicting_count:
            new_status = 'confirmed'  # Predominantly supported but has contradictions
        else:
            new_status = 'challenged'  # Contested or predominantly contradicted

    # Only update if changed
    old_status = signal.assumption_status
    if old_status != new_status:
        signal.assumption_status = new_status
        signal.save(update_fields=['assumption_status'])

        logger.info(
            "assumption_status_changed",
            extra={
                "signal_id": str(signal.id),
                "old_status": old_status,
                "new_status": new_status,
                "supporting": supporting_count,
                "contradicting": contradicting_count,
            },
        )

        return new_status

    return old_status


@transaction.atomic
def cascade_from_evidence_change(signal, case_id=None) -> dict:
    """
    Full cascade: recompute assumption status, sync to plan, trigger grounding.

    Call this after evidence M2M relationships change on an assumption Signal.
    Includes depth tracking to prevent infinite loops.

    Returns: {status_changed: bool, new_status: str, grounding_updated: bool}
    """
    result = {
        'status_changed': False,
        'new_status': None,
        'plan_synced': False,
        'grounding_updated': False,
    }

    # Guard against infinite cascade loops
    depth = getattr(_cascade_local, 'depth', 0)
    if depth >= MAX_CASCADE_DEPTH:
        logger.warning(
            "cascade_depth_exceeded",
            extra={"signal_id": str(signal.id), "depth": depth},
        )
        return result

    _cascade_local.depth = depth + 1
    try:
        # 1. Recompute assumption status from evidence balance
        old_status = signal.assumption_status
        new_status = recompute_assumption_status(signal)
        result['new_status'] = new_status

        if new_status and new_status != old_status:
            result['status_changed'] = True

            # 2. Sync status to plan if this assumption is linked to a plan
            effective_case_id = case_id or getattr(signal, 'case_id', None)
            if effective_case_id:
                try:
                    _sync_status_to_plan(effective_case_id, signal, new_status)
                    result['plan_synced'] = True
                except Exception as e:
                    logger.warning(
                        "plan_sync_failed",
                        extra={"signal_id": str(signal.id), "error": str(e)},
                    )

                # 3. Trigger grounding recalculation
                try:
                    from apps.cases.brief_grounding import BriefGroundingEngine
                    BriefGroundingEngine.evolve_brief(effective_case_id)
                    result['grounding_updated'] = True
                except Exception as e:
                    logger.warning(
                        "grounding_recalc_failed",
                        extra={"case_id": str(effective_case_id), "error": str(e)},
                    )
    finally:
        _cascade_local.depth = depth  # Restore previous depth

    return result


def _sync_status_to_plan(case_id, signal, new_status: str):
    """
    Sync assumption status back to the plan JSON.

    Finds the plan assumption that references this signal_id
    and updates its status to match.
    """
    from apps.cases.plan_service import PlanService
    from apps.cases.models import InvestigationPlan

    try:
        plan, current_version = PlanService.get_current_version(case_id)
    except InvestigationPlan.DoesNotExist:
        return

    content = current_version.content
    assumptions = content.get('assumptions', [])

    # Find plan assumption linked to this signal
    target_assumption_id = None
    for a in assumptions:
        if a.get('signal_id') == str(signal.id):
            if a.get('status') != new_status:
                target_assumption_id = a['id']
            break

    if target_assumption_id:
        # Build evidence summary
        from django.db.models import Count
        counts = type(signal).objects.filter(pk=signal.pk).aggregate(
            supporting=Count('supported_by_evidence'),
            contradicting=Count('contradicted_by_evidence'),
        )
        supporting = counts['supporting']
        contradicting = counts['contradicting']
        evidence_summary = f"{supporting} supporting, {contradicting} contradicting evidence"

        PlanService.update_assumption_status(
            case_id=case_id,
            assumption_id=target_assumption_id,
            new_status=new_status,
            evidence_summary=evidence_summary,
        )


def _on_evidence_m2m_changed(sender, instance, action, pk_set, **kwargs):
    """
    Django signal handler for M2M changes on Evidence.supports_signals
    and Evidence.contradicts_signals.

    Triggered when evidence is linked to or unlinked from signals.
    """
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return

    from apps.signals.models import Signal, SignalType

    if pk_set:
        # Get the affected assumption signals
        assumption_signals = Signal.objects.filter(
            id__in=pk_set,
            type=SignalType.ASSUMPTION,
        )
        for sig in assumption_signals:
            cascade_from_evidence_change(sig)
