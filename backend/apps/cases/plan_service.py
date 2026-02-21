"""
Plan service — operations on investigation plans.

All plan mutations go through this service to ensure:
- Versioning (every change creates a new PlanVersion snapshot)
- Event emission (provenance tracking)
- Atomic transactions
"""
import copy
import uuid
from typing import Optional

from django.db import transaction

import logging

logger = logging.getLogger(__name__)

from apps.events.models import EventType, ActorType
from apps.events.services import EventService
from .models import (
    InvestigationPlan,
    PlanVersion,
    CaseStage,
)


class PlanService:
    """Service for investigation plan operations."""

    @staticmethod
    def _trigger_regrounding(case_id, context: str = ''):
        """Trigger brief re-grounding after plan changes. Non-fatal on failure."""
        try:
            from apps.cases.brief_grounding import BriefGroundingEngine
            BriefGroundingEngine.evolve_brief(case_id)
        except Exception:
            logger.exception(
                "brief_regrounding_failed",
                extra={"case_id": str(case_id), "context": context},
            )

    @classmethod
    @transaction.atomic
    def create_initial_plan(cls, case, analysis, inquiries, correlation_id=None):
        """
        Create plan from case analysis (called during create_case_from_analysis).

        Builds initial plan content from analysis data:
        - Single "Initial Investigation" phase containing all inquiries
        - Assumptions from analysis with untested status
        - Decision criteria from analysis (if present)

        Assumption lifecycle is now tracked via graph nodes (apps.graph.models.Node).
        Plan assumptions are stored for display but no longer link to Signal IDs.

        Returns: (plan, version)
        """
        # Build assumption test strategies from analysis (if enhanced prompt provided them)
        test_strategies = analysis.get('assumption_test_strategies', {})

        # Build assumptions for the plan (graph nodes handle lifecycle)
        assumptions = []
        for a_text in analysis.get('assumptions', []):
            assumptions.append({
                "id": str(uuid.uuid4()),
                "text": a_text,
                "status": "untested",
                "test_strategy": test_strategies.get(a_text, ""),
                "evidence_summary": "",
                "risk_level": "medium",
            })

        # Build initial content
        content = {
            "phases": [{
                "id": str(uuid.uuid4()),
                "title": "Initial Investigation",
                "description": "Address the core questions from the conversation analysis",
                "order": 0,
                "inquiry_ids": [str(i.id) for i in inquiries],
            }],
            "assumptions": assumptions,
            "decision_criteria": [
                {
                    "id": str(uuid.uuid4()),
                    "text": c,
                    "is_met": False,
                    "linked_inquiry_id": None,
                }
                for c in analysis.get('decision_criteria', [])
            ],
            "stage_rationale": "Case just created \u2014 exploring the decision space",
        }

        plan = InvestigationPlan.objects.create(
            case=case,
            stage=CaseStage.EXPLORING,
            current_version=0,  # Will be set to 1 by create_snapshot
            position_statement=analysis.get('position_draft', ''),
        )

        version = PlanVersion.create_snapshot(
            plan=plan,
            content=content,
            created_by='system',
            diff_summary='Initial plan from conversation analysis',
        )

        # Emit event
        event = EventService.append(
            event_type=EventType.PLAN_CREATED,
            payload={
                'plan_id': str(plan.id),
                'version': version.version_number,
                'inquiry_count': len(inquiries),
                'assumption_count': len(content['assumptions']),
                'criteria_count': len(content['decision_criteria']),
            },
            actor_type=ActorType.SYSTEM,
            case_id=case.id,
            correlation_id=correlation_id,
        )

        # Backfill provenance link
        plan.created_from_event_id = event.id
        plan.save(update_fields=['created_from_event_id'])

        return plan, version

    @staticmethod
    def merge_plan_diff(current_content: dict, diff_data: dict) -> dict:
        """
        Merge an LLM-generated diff into the current plan state to produce
        a complete proposed_content snapshot.

        This allows the LLM to emit only the diff (added/updated assumptions,
        criteria, stage changes) while the backend reconstructs the full plan
        state. Reduces token usage and avoids the LLM echoing back unchanged
        content.

        Args:
            current_content: Current plan version content dict
            diff_data: The diff from the LLM's <plan_edits> section

        Returns:
            Complete proposed_content dict ready for PlanVersion storage
        """
        content = copy.deepcopy(current_content)

        # --- Apply assumption changes ---
        assumptions = content.get('assumptions', [])
        assumption_map = {a['id']: a for a in assumptions if 'id' in a}

        # Update existing assumptions
        for update in diff_data.get('updated_assumptions', []):
            a_id = update.get('id')
            if a_id and a_id in assumption_map:
                if 'status' in update:
                    assumption_map[a_id]['status'] = update['status']
                if 'evidence_summary' in update:
                    assumption_map[a_id]['evidence_summary'] = update['evidence_summary']
                if 'risk_level' in update:
                    assumption_map[a_id]['risk_level'] = update['risk_level']

        # Add new assumptions
        for new_a in diff_data.get('added_assumptions', []):
            assumptions.append({
                'id': str(uuid.uuid4()),
                'text': new_a.get('text', ''),
                'status': 'untested',
                'test_strategy': new_a.get('test_strategy', ''),
                'evidence_summary': '',
                'risk_level': new_a.get('risk_level', 'medium'),
            })

        content['assumptions'] = assumptions

        # --- Apply criteria changes ---
        criteria = content.get('decision_criteria', [])
        criteria_map = {c['id']: c for c in criteria if 'id' in c}

        # Update existing criteria
        for update in diff_data.get('updated_criteria', []):
            c_id = update.get('id')
            if c_id and c_id in criteria_map:
                if 'is_met' in update:
                    criteria_map[c_id]['is_met'] = update['is_met']

        # Add new criteria
        for new_c in diff_data.get('added_criteria', []):
            criteria.append({
                'id': str(uuid.uuid4()),
                'text': new_c.get('text', ''),
                'is_met': False,
                'priority': new_c.get('priority', 'nice_to_have'),
                'linked_inquiry_id': None,
            })

        content['decision_criteria'] = criteria

        # --- Apply stage change ---
        stage_change = diff_data.get('stage_change')
        if stage_change and isinstance(stage_change, str):
            content['stage_rationale'] = diff_data.get('stage_rationale', f'Stage advanced to {stage_change}')
        elif stage_change and isinstance(stage_change, dict):
            content['stage_rationale'] = stage_change.get('rationale', '')

        return content

    @classmethod
    def get_current_version(cls, case_id):
        """
        Get plan with its current version content.

        Returns: (plan, version)
        Raises: InvestigationPlan.DoesNotExist if no plan exists
        """
        plan = InvestigationPlan.objects.select_related('case').get(case_id=case_id)
        version = PlanVersion.objects.get(plan=plan, version_number=plan.current_version)
        return plan, version

    @classmethod
    @transaction.atomic
    def create_new_version(
        cls,
        case_id,
        content: dict,
        created_by: str,
        diff_summary: str = '',
        diff_data: Optional[dict] = None,
        actor_type=ActorType.SYSTEM,
        actor_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[uuid.UUID] = None,
        trigger_type: str = 'initial',
        generation_context: Optional[dict] = None,
    ):
        """
        Create a new plan version (for accepted AI proposals or user-requested changes).

        Returns: PlanVersion
        """
        plan = InvestigationPlan.objects.get(case_id=case_id)
        version = PlanVersion.create_snapshot(
            plan=plan,
            content=content,
            created_by=created_by,
            diff_summary=diff_summary,
            diff_data=diff_data,
            trigger_type=trigger_type,
            generation_context=generation_context,
        )

        EventService.append(
            event_type=EventType.PLAN_VERSION_CREATED,
            payload={
                'plan_id': str(plan.id),
                'version': version.version_number,
                'diff_summary': diff_summary,
                'created_by': created_by,
            },
            actor_type=actor_type,
            actor_id=actor_id,
            case_id=plan.case_id,
            correlation_id=correlation_id,
        )

        return version

    @classmethod
    @transaction.atomic
    def update_stage(
        cls,
        case_id,
        new_stage: str,
        rationale: str = '',
        actor_id: Optional[uuid.UUID] = None,
    ):
        """
        Update the investigation stage.

        Creates a new version to record the stage change in the version history.
        """
        plan = InvestigationPlan.objects.get(case_id=case_id)
        old_stage = plan.stage
        plan.stage = new_stage
        plan.save(update_fields=['stage', 'updated_at'])

        # Update stage_rationale in current version content and create new version
        current = PlanVersion.objects.get(plan=plan, version_number=plan.current_version)
        content = copy.deepcopy(current.content)
        content['stage_rationale'] = rationale

        PlanVersion.create_snapshot(
            plan=plan,
            content=content,
            created_by='ai_proposal',
            diff_summary=f'Stage changed: {old_stage} \u2192 {new_stage}',
            diff_data={'type': 'stage_change', 'from': old_stage, 'to': new_stage},
            trigger_type='stage_change',
        )

        EventService.append(
            event_type=EventType.PLAN_STAGE_CHANGED,
            payload={
                'plan_id': str(plan.id),
                'old_stage': old_stage,
                'new_stage': new_stage,
                'rationale': rationale,
            },
            actor_type=ActorType.USER if actor_id else ActorType.ASSISTANT,
            actor_id=actor_id,
            case_id=plan.case_id,
        )

        cls._trigger_regrounding(case_id, context='stage_change')

    @classmethod
    @transaction.atomic
    def restore_version(
        cls,
        case_id,
        target_version_number: int,
        actor_id: Optional[uuid.UUID] = None,
    ):
        """
        Revert to a previous plan version by creating a new version with old content.

        This is non-destructive — the old versions remain in history.
        Returns: PlanVersion (the new version with restored content)
        """
        plan = InvestigationPlan.objects.get(case_id=case_id)
        target = PlanVersion.objects.get(plan=plan, version_number=target_version_number)

        version = PlanVersion.create_snapshot(
            plan=plan,
            content=target.content,
            created_by='restore',
            diff_summary=f'Restored from version {target_version_number}',
            diff_data={'type': 'restore', 'restored_from': target_version_number},
            trigger_type='restore',
        )

        EventService.append(
            event_type=EventType.PLAN_RESTORED,
            payload={
                'plan_id': str(plan.id),
                'restored_from': target_version_number,
                'new_version': version.version_number,
            },
            actor_type=ActorType.USER,
            actor_id=actor_id,
            case_id=plan.case_id,
        )

        cls._trigger_regrounding(case_id, context='plan_restore')

        return version

    @classmethod
    @transaction.atomic
    def update_assumption_status(
        cls,
        case_id,
        assumption_id: str,
        new_status: str,
        evidence_summary: str = '',
        actor_id: Optional[uuid.UUID] = None,
    ):
        """
        Update a specific assumption's status, creating a new version.

        Valid statuses: untested, confirmed, challenged, refuted
        Returns: PlanVersion
        Raises: ValueError if assumption not found
        """
        plan, current = cls.get_current_version(case_id)
        content = copy.deepcopy(current.content)

        old_status = None
        assumption_text = ''
        for a in content.get('assumptions', []):
            if a['id'] == assumption_id:
                old_status = a['status']
                a['status'] = new_status
                if evidence_summary:
                    a['evidence_summary'] = evidence_summary
                assumption_text = a['text']
                break

        if old_status is None:
            raise ValueError(f"Assumption {assumption_id} not found in plan")

        version = PlanVersion.create_snapshot(
            plan=plan,
            content=content,
            created_by='ai_proposal',
            diff_summary=f'Assumption "{assumption_text[:50]}" status: {old_status} \u2192 {new_status}',
            diff_data={
                'type': 'assumption_update',
                'assumption_id': assumption_id,
                'from': old_status,
                'to': new_status,
            },
            trigger_type='user_edit',
        )

        # Note: assumption_status sync to Signal removed — assumption lifecycle
        # is now tracked via graph node status in apps.graph.models.Node.

        cls._trigger_regrounding(case_id, context='assumption_update')

        return version

    @classmethod
    @transaction.atomic
    def update_criterion_status(
        cls,
        case_id,
        criterion_id: str,
        is_met: bool,
        actor_id: Optional[uuid.UUID] = None,
    ):
        """
        Mark a decision criterion as met/unmet, creating a new version.

        Returns: PlanVersion
        Raises: ValueError if criterion not found
        """
        plan, current = cls.get_current_version(case_id)
        content = copy.deepcopy(current.content)

        criterion_text = ''
        found = False
        for c in content.get('decision_criteria', []):
            if c['id'] == criterion_id:
                c['is_met'] = is_met
                criterion_text = c['text']
                found = True
                break

        if not found:
            raise ValueError(f"Criterion {criterion_id} not found in plan")

        version = PlanVersion.create_snapshot(
            plan=plan,
            content=content,
            created_by='user_request',
            diff_summary=f'Criterion "{criterion_text[:50]}" marked as {"met" if is_met else "unmet"}',
            diff_data={
                'type': 'criterion_update',
                'criterion_id': criterion_id,
                'is_met': is_met,
            },
            trigger_type='user_edit',
        )

        cls._trigger_regrounding(case_id, context='criterion_update')

        return version
