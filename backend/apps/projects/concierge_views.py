"""
Concierge Endpoint

Returns all card-relevant signals for the project home concierge page.
Pure structured queries — no LLM calls. Designed for fast page loads.

The frontend card selection algorithm uses this data to pick 1-3 cards
to display on the project home page.
"""
import logging
from datetime import date

from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cases.models import (
    Case,
    CaseStatus,
    InvestigationPlan,
    PlanVersion,
    DecisionRecord,
)
from apps.cases.outcome_service import OutcomeReviewService
from apps.graph.models import (
    ClusterHierarchy,
    HierarchyStatus,
    ProjectOrientation,
    OrientationStatus,
    ProjectInsight,
    InsightStatus,
)
from .models import Project, Document

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_concierge(request, pk):
    """
    GET /api/v2/projects/{pk}/concierge/

    Returns card signals for the project home concierge page.
    """
    try:
        project = Project.objects.get(pk=pk, user=request.user, is_archived=False)
    except Project.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    data = {
        'project_id': str(project.id),
        'has_documents': False,
        'has_cases': False,
        'document_count': 0,
        'decisions_at_risk': [],
        'cases_needing_attention': [],
        'recent_active_cases': [],
        'orientation_shift': None,
    }

    # ─── Document count ───
    doc_count = Document.objects.filter(project=project).count()
    data['document_count'] = doc_count
    data['has_documents'] = doc_count > 0

    # ─── Cases overview ───
    cases = list(
        Case.objects.filter(project=project, user=request.user)
        .exclude(status=CaseStatus.ARCHIVED)
        .select_related('plan')
        .order_by('-updated_at')
    )
    data['has_cases'] = len(cases) > 0

    # ─── Decisions at Risk: overdue outcome checks ───
    pending_reviews = OutcomeReviewService.get_pending_reviews(
        user=request.user,
        project_id=str(project.id),
        limit=3,
    )
    for review in pending_reviews:
        data['decisions_at_risk'].append({
            'case_id': review['case_id'],
            'case_title': review['case_title'],
            'decision_text': review['decision_text'],
            'risk_type': 'overdue_outcome',
            'days_overdue': review['days_overdue'],
            'outcome_check_date': review.get('last_note_date') or '',
        })

    # ─── Cases needing attention: untested high-risk assumptions ───
    active_cases = [c for c in cases if c.status == CaseStatus.ACTIVE]
    for case in active_cases[:5]:  # Limit to avoid expensive queries
        try:
            plan = case.plan
            latest_version = (
                PlanVersion.objects
                .filter(plan=plan)
                .order_by('-version_number')
                .values_list('content', flat=True)
                .first()
            )
            if not latest_version:
                continue

            assumptions = latest_version.get('assumptions', [])
            high_risk_untested = [
                a for a in assumptions
                if a.get('risk_level') == 'high' and a.get('status') == 'untested'
            ]

            if high_risk_untested:
                count = len(high_risk_untested)
                data['cases_needing_attention'].append({
                    'case_id': str(case.id),
                    'case_title': case.title[:60],
                    'attention_type': 'untested_load_bearing',
                    'detail': f'{count} high-risk untested assumption{"s" if count != 1 else ""}',
                    'stage': plan.stage,
                })
        except InvestigationPlan.DoesNotExist:
            continue

    # ─── Recent active cases (for "Resume Work" cards) ───
    for case in active_cases[:3]:
        try:
            plan = case.plan
            stage = plan.stage
        except InvestigationPlan.DoesNotExist:
            stage = 'exploring'

        # Build progress summary from inquiries
        from apps.cases.models import Inquiry, InquiryStatus
        inquiry_stats = Inquiry.objects.filter(case=case).values_list('status', flat=True)
        total = len(inquiry_stats)
        resolved = sum(1 for s in inquiry_stats if s == InquiryStatus.RESOLVED)
        progress = f'{resolved}/{total} inquiries resolved' if total > 0 else 'Just started'

        data['recent_active_cases'].append({
            'case_id': str(case.id),
            'case_title': case.title[:60],
            'last_activity': case.updated_at.isoformat(),
            'stage': stage,
            'progress_summary': progress,
        })

    # ─── Orientation shift: hierarchy rebuilt but orientation stale ───
    try:
        current_hierarchy = ClusterHierarchy.objects.filter(
            project=project,
            is_current=True,
            status=HierarchyStatus.READY,
        ).first()

        current_orientation = ProjectOrientation.objects.filter(
            project=project,
            is_current=True,
            status=OrientationStatus.READY,
        ).first()

        has_shift = False
        hierarchy_status = 'none'

        if current_hierarchy:
            hierarchy_status = 'ready'
            if current_orientation:
                # Hierarchy was rebuilt after orientation was generated
                if current_hierarchy.updated_at > current_orientation.created_at:
                    has_shift = True
            else:
                # Hierarchy exists but no orientation yet
                has_shift = True

        data['orientation_shift'] = {
            'has_shift': has_shift,
            'hierarchy_status': hierarchy_status,
        }
    except Exception as e:
        logger.debug(f'Orientation shift check failed: {e}')
        data['orientation_shift'] = {
            'has_shift': False,
            'hierarchy_status': 'none',
        }

    # ─── Worth Exploring: best unacted-on insights from orientation ───
    worth_exploring = []
    if current_orientation and current_orientation.status == OrientationStatus.READY:
        insights = (
            ProjectInsight.objects.filter(
                orientation=current_orientation,
                status=InsightStatus.ACTIVE,
            )
            .exclude(linked_thread__isnull=False)
            .order_by('display_order')[:3]
        )
        for insight in insights:
            worth_exploring.append({
                'insight_id': str(insight.id),
                'title': insight.title,
                'insight_type': insight.insight_type,
                'confidence': insight.confidence,
            })

    data['worth_exploring'] = worth_exploring

    return Response(data)
