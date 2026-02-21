"""
Plan-related viewset actions, extracted from CaseViewSet for maintainability.

Provides a mixin class with all investigation-plan endpoints:
  - plan (get current)
  - plan_versions (list)
  - plan_version_detail (get specific)
  - plan_stage (update stage)
  - plan_restore (restore to version)
  - plan_accept_diff (accept proposed diff)
  - plan_assumption_update
  - plan_criterion_update
  - generate_plan
"""
import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import InvestigationPlan, PlanVersion
from .serializers import (
    InvestigationPlanSerializer,
    PlanVersionSerializer,
    PlanStageUpdateSerializer,
    PlanRestoreSerializer,
    PlanDiffProposalSerializer,
    AssumptionStatusSerializer,
    CriterionStatusSerializer,
)
from .plan_service import PlanService

logger = logging.getLogger(__name__)


class PlanActionsMixin:
    """Mixin providing investigation-plan actions for CaseViewSet."""

    @action(detail=True, methods=['get'])
    def plan(self, request, pk=None):
        """
        Get current investigation plan with latest version content.

        GET /api/cases/{id}/plan/
        """
        case = self.get_object()
        try:
            plan_obj = case.plan
        except InvestigationPlan.DoesNotExist:
            return Response(
                {'detail': 'No plan exists for this case'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(InvestigationPlanSerializer(plan_obj).data)

    @action(detail=True, methods=['get'], url_path='plan/versions')
    def plan_versions(self, request, pk=None):
        """
        List all plan versions for history/undo UI.

        GET /api/cases/{id}/plan/versions/
        """
        case = self.get_object()
        versions = PlanVersion.objects.filter(
            plan__case=case
        ).order_by('-version_number')
        return Response(PlanVersionSerializer(versions, many=True).data)

    @action(
        detail=True, methods=['get'],
        url_path=r'plan/versions/(?P<version_num>[0-9]+)'
    )
    def plan_version_detail(self, request, pk=None, version_num=None):
        """
        Get a specific plan version.

        GET /api/cases/{id}/plan/versions/{num}/
        """
        case = self.get_object()
        try:
            version = PlanVersion.objects.get(
                plan__case=case,
                version_number=int(version_num)
            )
        except PlanVersion.DoesNotExist:
            return Response(
                {'detail': 'Version not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(PlanVersionSerializer(version).data)

    @action(detail=True, methods=['post'], url_path='plan/stage')
    def plan_stage(self, request, pk=None):
        """
        Update investigation stage.

        POST /api/cases/{id}/plan/stage/
        Body: {"stage": "investigating", "rationale": "..."}
        """
        case = self.get_object()
        serializer = PlanStageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PlanService.update_stage(
            case_id=case.id,
            new_stage=serializer.validated_data['stage'],
            rationale=serializer.validated_data.get('rationale', ''),
            actor_id=request.user.id,
        )
        plan_obj = case.plan
        return Response(InvestigationPlanSerializer(plan_obj).data)

    @action(detail=True, methods=['post'], url_path='plan/restore')
    def plan_restore(self, request, pk=None):
        """
        Restore plan to a previous version.

        POST /api/cases/{id}/plan/restore/
        Body: {"version_number": 1}
        """
        case = self.get_object()
        serializer = PlanRestoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = PlanService.restore_version(
            case_id=case.id,
            target_version_number=serializer.validated_data['version_number'],
            actor_id=request.user.id,
        )
        return Response(PlanVersionSerializer(version).data)

    @action(detail=True, methods=['post'], url_path='plan/accept-diff')
    def plan_accept_diff(self, request, pk=None):
        """
        Accept a proposed plan diff (creates new version).

        POST /api/cases/{id}/plan/accept-diff/
        Body: {"content": {...}, "diff_summary": "...", "diff_data": {...}}
        """
        from apps.events.models import ActorType
        case = self.get_object()
        serializer = PlanDiffProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        diff_data = serializer.validated_data.get('diff_data') or {}

        version = PlanService.create_new_version(
            case_id=case.id,
            content=serializer.validated_data['content'],
            created_by='ai_proposal',
            diff_summary=serializer.validated_data['diff_summary'],
            diff_data=diff_data,
            actor_type=ActorType.USER,
            actor_id=request.user.id,
            trigger_type=serializer.validated_data.get('trigger_type', 'ai_proposal_accepted'),
            generation_context=serializer.validated_data.get('generation_context', {}),
        )

        stage_change = diff_data.get('stage_change')
        if stage_change:
            new_stage = stage_change if isinstance(stage_change, str) else stage_change.get('to')
            rationale = stage_change.get('rationale', '') if isinstance(stage_change, dict) else ''
            if new_stage:
                from .models import CaseStage
                valid_stages = {s.value for s in CaseStage}
                if new_stage in valid_stages:
                    PlanService.update_stage(
                        case_id=case.id,
                        new_stage=new_stage,
                        rationale=rationale,
                        actor_id=request.user.id,
                    )

        return Response(PlanVersionSerializer(version).data)

    @action(
        detail=True, methods=['patch'],
        url_path=r'plan/assumptions/(?P<assumption_id>[^/.]+)'
    )
    def plan_assumption_update(self, request, pk=None, assumption_id=None):
        """
        Update an assumption's status.

        PATCH /api/cases/{id}/plan/assumptions/{assumption_id}/
        Body: {"status": "confirmed", "evidence_summary": "..."}
        """
        case = self.get_object()
        serializer = AssumptionStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = PlanService.update_assumption_status(
                case_id=case.id,
                assumption_id=assumption_id,
                new_status=serializer.validated_data['status'],
                evidence_summary=serializer.validated_data.get('evidence_summary', ''),
                actor_id=request.user.id,
            )
        except ValueError as e:
            logger.exception("Failed to update assumption %s for case %s", assumption_id, case.id)
            return Response(
                {'detail': 'Assumption not found or could not be updated.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(PlanVersionSerializer(version).data)

    @action(
        detail=True, methods=['patch'],
        url_path=r'plan/criteria/(?P<criterion_id>[^/.]+)'
    )
    def plan_criterion_update(self, request, pk=None, criterion_id=None):
        """
        Update a decision criterion's met status.

        PATCH /api/cases/{id}/plan/criteria/{criterion_id}/
        Body: {"is_met": true}
        """
        case = self.get_object()
        serializer = CriterionStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = PlanService.update_criterion_status(
                case_id=case.id,
                criterion_id=criterion_id,
                is_met=serializer.validated_data['is_met'],
                actor_id=request.user.id,
            )
        except ValueError as e:
            logger.exception("Failed to update criterion %s for case %s", criterion_id, case.id)
            return Response(
                {'detail': 'Criterion not found or could not be updated.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(PlanVersionSerializer(version).data)

    @action(detail=True, methods=['post'], url_path='generate-plan')
    def generate_plan(self, request, pk=None):
        """
        Generate an investigation plan for a case that doesn't have one.

        POST /api/cases/{id}/generate-plan/
        """
        case = self.get_object()

        try:
            existing = case.plan  # noqa: F841
            return Response(
                {'error': 'Case already has a plan'},
                status=status.HTTP_409_CONFLICT
            )
        except InvestigationPlan.DoesNotExist:
            pass

        from apps.inquiries.models import Inquiry
        inquiries = list(
            Inquiry.objects.filter(case=case).order_by('sequence_index')
        )

        analysis = {
            'assumptions': [],
            'decision_criteria': [],
            'position_draft': case.position or '',
        }

        if case.main_brief:
            from apps.cases.brief_models import BriefSection
            for section in BriefSection.objects.filter(
                brief=case.main_brief
            ):
                if section.section_type == 'assumptions':
                    for line in (section.content or '').split('\n'):
                        line = line.strip().lstrip('- •')
                        if line:
                            analysis['assumptions'].append(line)

        plan, version = PlanService.create_initial_plan(
            case=case,
            analysis=analysis,
            inquiries=inquiries,
        )

        return Response(
            InvestigationPlanSerializer(plan).data,
            status=status.HTTP_201_CREATED,
        )
