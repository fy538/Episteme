"""
Case views
"""
import logging

from django.db import models, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Case, CaseStatus, WorkingDocument, WorkingDocumentVersion, InvestigationPlan, PlanVersion
from .brief_models import BriefSection, BriefAnnotation
from .serializers import (
    CaseSerializer,
    CreateCaseSerializer,
    UpdateCaseSerializer,
    UserConfidenceSerializer,
    InvestigationPlanSerializer,
    PlanVersionSerializer,
    PlanStageUpdateSerializer,
    PlanRestoreSerializer,
    PlanDiffProposalSerializer,
    AssumptionStatusSerializer,
    CriterionStatusSerializer,
)
from .plan_service import PlanService
from .brief_serializers import (
    BriefSectionSerializer,
    BriefSectionCreateSerializer,
    BriefSectionUpdateSerializer,
    BriefSectionReorderSerializer,
    BriefOverviewSerializer,
    BriefAnnotationSerializer,
)
from .document_serializers import (
    WorkingDocumentSerializer,
    WorkingDocumentListSerializer,
    WorkingDocumentCreateSerializer,
    DocumentCitationSerializer,
)
from .services import CaseService
from .document_service import WorkingDocumentService
from apps.chat.models import ChatThread
from apps.chat.serializers import ChatThreadSerializer, ChatThreadDetailSerializer


class CaseViewSet(viewsets.ModelViewSet):
    """ViewSet for cases"""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Case.objects
            .filter(user=self.request.user)
            .exclude(status=CaseStatus.ARCHIVED)
            .select_related('based_on_skill', 'became_skill')
            .prefetch_related('caseactiveskill_set__skill')
        )

    def destroy(self, request, *args, **kwargs):
        """Soft delete — sets status to ARCHIVED instead of removing the row."""
        case = self.get_object()
        case.status = CaseStatus.ARCHIVED
        case.save(update_fields=['status', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateCaseSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateCaseSerializer
        return CaseSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new case with auto-generated brief"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        case, case_brief = CaseService.create_case(
            user=request.user,
            title=serializer.validated_data['title'],
            position=serializer.validated_data.get('position', ''),
            stakes=serializer.validated_data.get('stakes'),
            thread_id=serializer.validated_data.get('thread_id'),
            project_id=serializer.validated_data.get('project_id'),  # Phase 2
        )

        return Response(
            {
                'case': CaseSerializer(case).data,
                'main_brief': WorkingDocumentSerializer(case_brief, context={'request': request}).data
            },
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Update a case"""
        case = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        updated_case = CaseService.update_case(
            case_id=case.id,
            user=request.user,
            **serializer.validated_data
        )
        
        return Response(CaseSerializer(updated_case).data)
    
    def partial_update(self, request, *args, **kwargs):
        """Partial update of a case"""
        return self.update(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'], url_path='threads')
    def get_threads(self, request, pk=None):
        """
        Get all chat threads for this case
        
        GET /api/cases/{id}/threads/
        
        Returns list of all chat threads associated with this case.
        Supports multiple threads per case for different purposes.
        """
        case = self.get_object()
        
        # Get all threads linked to this case
        threads = ChatThread.objects.filter(
            primary_case=case,
            user=request.user
        ).order_by('-updated_at')
        
        serializer = ChatThreadDetailSerializer(threads, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='threads/create')
    def create_thread(self, request, pk=None):
        """
        Create a new chat thread for this case
        
        POST /api/cases/{id}/threads/create/
        
        Body:
        {
            "title": "Research Thread",  # optional
            "thread_type": "research"     # optional: general, research, inquiry, document
        }
        """
        case = self.get_object()
        
        title = request.data.get('title', f'Chat: {case.title}')
        thread_type = request.data.get('thread_type', 'general')
        
        # Create new thread linked to this case
        thread = ChatThread.objects.create(
            user=request.user,
            title=title,
            thread_type=thread_type,
            primary_case=case,
            project=case.project  # Link to same project
        )
        
        serializer = ChatThreadDetailSerializer(thread)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='generate-brief-outline')
    def generate_brief_outline(self, request, pk=None):
        """
        Generate an AI-powered brief outline for a new case
        
        POST /api/cases/{id}/generate-brief-outline/
        
        Creates an initial structure for the case brief based on:
        - Case title and position
        - Stakes level
        - Any initial chat messages or context
        """
        case = self.get_object()
        
        # Simple outline template for now
        # In production, this would use an LLM to generate contextual outline
        outline = f"""# {case.title}

## Position
{case.position or '_Describe your current position or thesis_'}

## Stakes
This is a **{case.stakes}** stakes decision.

## Background
_Provide context about this decision_

## Key Questions
- _What are the main questions to resolve?_
- _What assumptions are critical?_
- _What evidence would change your mind?_

## Analysis
_Your research and thinking goes here_

## Decision Criteria
_What factors will determine the right choice?_

## Next Steps
_What actions follow from this decision?_
"""
        
        return Response({
            'outline': outline,
            'case_id': str(case.id)
        })
    
    @action(detail=True, methods=['post'])
    def activate_skills(self, request, pk=None):
        """
        Activate skills for this case

        POST /api/cases/{id}/activate_skills/

        Request body:
        {
            "skill_ids": ["uuid1", "uuid2", ...]
        }

        Returns: Updated case with active skills
        """
        from apps.skills.models import Skill
        from apps.skills.serializers import SkillListSerializer
        from apps.cases.models import CaseActiveSkill

        case = self.get_object()
        skill_ids = request.data.get('skill_ids', [])

        # Validate that skills exist and are active
        skills_by_id = {
            str(s.id): s
            for s in Skill.objects.filter(id__in=skill_ids, status='active')
        }

        # Preserve client-supplied ordering
        ordered_skills = [
            skills_by_id[sid] for sid in skill_ids if sid in skills_by_id
        ]

        # Clear existing and re-add with ordering (through model) — atomic
        with transaction.atomic():
            CaseActiveSkill.objects.filter(case=case).delete()
            CaseActiveSkill.objects.bulk_create([
                CaseActiveSkill(case=case, skill=skill, order=i)
                for i, skill in enumerate(ordered_skills)
            ])

        return Response({
            'case_id': str(case.id),
            'active_skills': SkillListSerializer(ordered_skills, many=True).data
        })

    @action(detail=True, methods=['post'], url_path='activate-pack')
    def activate_pack(self, request, pk=None):
        """
        Activate all skills from a skill pack for this case.

        POST /api/cases/{id}/activate-pack/

        SkillPack was removed during skill system cleanup.
        """
        return Response(
            {'error': 'Skill packs are no longer available'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=True, methods=['get'])
    def onboarding(self, request, pk=None):
        """
        Get onboarding data for newly created case
        
        GET /api/cases/{id}/onboarding/
        
        Shows what was auto-created and suggests next steps.
        Core experience improvement - helps users understand what the system did for them.
        """
        from apps.inquiries.models import Inquiry
        from apps.inquiries.serializers import InquiryListSerializer
        
        case = self.get_object()
        
        # Get auto-created items
        inquiries = Inquiry.objects.filter(case=case).order_by('sequence_index')
        brief = case.main_brief
        
        # Extract assumptions from brief if exists
        assumptions = []
        if brief and brief.ai_structure:
            assumptions = brief.ai_structure.get('assumptions', [])
        
        # Determine next steps
        next_steps = []
        
        # Step 1: Review assumptions
        if assumptions:
            next_steps.append({
                'action': 'review_assumptions',
                'title': 'Review untested assumptions',
                'description': f'{len(assumptions)} assumptions were detected in your conversation',
                'completed': False,
                'priority': 1
            })
        
        # Step 2: Start first inquiry
        open_inquiries = inquiries.filter(status='OPEN')
        if open_inquiries.exists():
            first_inquiry = open_inquiries.first()
            next_steps.append({
                'action': 'start_first_inquiry',
                'title': f'Investigate: {first_inquiry.title}',
                'description': 'Begin your first investigation',
                'inquiry_id': str(first_inquiry.id),
                'completed': False,
                'priority': 2
            })
        
        # Step 3: Gather evidence
        next_steps.append({
            'action': 'gather_evidence',
            'title': 'Upload relevant documents',
            'description': 'Add documents to extract evidence from',
            'completed': False,
            'priority': 3
        })
        
        # Calculate if user is new (first case)
        user_case_count = Case.objects.filter(user=request.user).count()
        is_first_case = user_case_count == 1
        
        return Response({
            'auto_created': {
                'inquiries': InquiryListSerializer(inquiries, many=True).data,
                'assumptions': assumptions,
                'brief_exists': brief is not None,
                'brief_id': str(brief.id) if brief else None
            },
            'next_steps': next_steps,
            'first_time_user': is_first_case,
            'summary': {
                'total_inquiries': inquiries.count(),
                'assumptions_count': len(assumptions),
                'from_conversation': case.linked_thread is not None
            }
        })
    
    @action(detail=True, methods=['get'])
    def active_skills(self, request, pk=None):
        """
        Get active skills for this case
        
        GET /api/cases/{id}/active_skills/
        
        Returns: List of active skills
        """
        from apps.skills.serializers import SkillListSerializer
        
        case = self.get_object()
        skills = case.active_skills.filter(status='active')
        
        return Response(SkillListSerializer(skills, many=True).data)
    
    @action(detail=True, methods=['post'])
    def toggle_skill_mode(self, request, pk=None):
        """
        Toggle skill template mode for this case
        
        POST /api/cases/{id}/toggle_skill_mode/
        
        Request body:
        {
            "enable": true,
            "scope": "personal"  # or "team", "organization"
        }
        
        Returns: Case + skill preview
        """
        from apps.skills.preview import SkillPreviewService
        
        case = self.get_object()
        enable = request.data.get('enable', True)
        scope = request.data.get('scope', 'personal')
        
        case.is_skill_template = enable
        if enable:
            case.template_scope = scope
        else:
            case.template_scope = None
        case.save(update_fields=['is_skill_template', 'template_scope', 'updated_at'])
        
        # Generate preview
        preview = None
        if enable:
            preview = SkillPreviewService.analyze_case(case)
        
        return Response({
            'case': CaseSerializer(case).data,
            'skill_preview': preview
        })
    
    @action(detail=True, methods=['post'])
    def save_as_skill(self, request, pk=None):
        """
        Save this case as a skill
        
        POST /api/cases/{id}/save_as_skill/
        
        Request body:
        {
            "name": "Legal Framework",
            "scope": "personal",
            "description": "Optional custom description"
        }
        
        Returns: Created skill
        """
        # CaseSkillConverter was removed during skill system cleanup
        return Response(
            {'error': 'Case-to-skill conversion is not currently available'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )
    
    @action(detail=True, methods=['get'])
    def skill_preview(self, request, pk=None):
        """
        Preview what skill would be created from this case

        GET /api/cases/{id}/skill_preview/

        Returns: Skill preview data
        """
        from apps.skills.preview import SkillPreviewService

        case = self.get_object()
        preview = SkillPreviewService.analyze_case(case)

        return Response(preview)

    @action(detail=True, methods=['get'], url_path='evidence-landscape')
    def evidence_landscape(self, request, pk=None):
        """
        Get evidence landscape (counts, not scores).

        GET /api/cases/{id}/evidence-landscape/

        Returns objective counts of evidence, assumptions, and inquiries
        without computing arbitrary scores.

        Returns: {
            evidence: {supporting, contradicting, neutral},
            assumptions: {total, validated, untested, untested_list},
            inquiries: {total, open, investigating, resolved},
            unlinked_claims: [{text, location}]
        }
        """
        from apps.inquiries.models import Inquiry, InquiryStatus

        case = self.get_object()

        # Evidence counts now come from graph Node(type=EVIDENCE) + Edge(type=SUPPORTS/CONTRADICTS)
        try:
            from apps.graph.models import Node, Edge, EdgeType
            evidence_nodes = Node.objects.filter(
                project=case.project,
                node_type='evidence',
            )
            total_evidence = evidence_nodes.count()
            total_supporting = Edge.objects.filter(
                source_node__in=evidence_nodes,
                edge_type=EdgeType.SUPPORTS,
            ).count()
            total_contradicting = Edge.objects.filter(
                source_node__in=evidence_nodes,
                edge_type=EdgeType.CONTRADICTS,
            ).count()
            total_neutral = total_evidence - total_supporting - total_contradicting
        except Exception:
            total_evidence = 0
            total_supporting = 0
            total_contradicting = 0
            total_neutral = 0

        evidence = {
            'total': total_evidence,
            'supporting': total_supporting,
            'contradicting': total_contradicting,
            'neutral': max(0, total_neutral),
        }

        # Count assumptions from the graph layer (Node model)
        try:
            from apps.graph.models import Node
            assumption_nodes = Node.objects.filter(
                project=case.project,
                node_type='assumption',
            )
            total_assumptions = assumption_nodes.count()
            validated_assumptions = assumption_nodes.filter(
                status__in=['confirmed', 'refuted']
            ).count()
            untested_nodes = assumption_nodes.exclude(
                status__in=['confirmed', 'refuted']
            )[:10]
            untested_list = [
                {
                    'id': str(node.id),
                    'text': node.content[:200] if node.content else '',
                    'status': node.status,
                }
                for node in untested_nodes
            ]
        except Exception:
            total_assumptions = 0
            validated_assumptions = 0
            untested_list = []

        assumptions = {
            'total': total_assumptions,
            'validated': validated_assumptions,
            'untested': total_assumptions - validated_assumptions,
            'untested_list': untested_list,
        }

        # Count inquiries by status — single aggregate query
        from django.db.models import Count, Q
        inquiries_qs = case.inquiries.exclude(status=InquiryStatus.ARCHIVED)
        inquiry_counts = inquiries_qs.aggregate(
            total=Count('id'),
            open=Count('id', filter=Q(status=InquiryStatus.OPEN)),
            investigating=Count('id', filter=Q(status=InquiryStatus.INVESTIGATING)),
            resolved=Count('id', filter=Q(status=InquiryStatus.RESOLVED)),
        )

        # Find unvalidated claims from the graph layer
        unlinked_claims = []
        try:
            from apps.graph.models import Node
            claim_nodes = Node.objects.filter(
                project=case.project,
                node_type='claim',
                status='unvalidated',
            )[:5]
            for node in claim_nodes:
                unlinked_claims.append({
                    'text': node.content[:150] if node.content else '',
                    'location': 'graph',
                })
        except Exception:
            pass

        return Response({
            'evidence': evidence,
            'assumptions': assumptions,
            'inquiries': inquiry_counts,
            'unlinked_claims': unlinked_claims,
        })

    @action(detail=True, methods=['patch'], url_path='user-confidence')
    def user_confidence(self, request, pk=None):
        """
        Set user's self-assessed confidence.

        PATCH /api/cases/{id}/user-confidence/

        Body: {
            user_confidence: int (0-100),
            what_would_change_mind: str (optional)
        }

        This is the user's own assessment, not a computed score.
        """
        case = self.get_object()
        serializer = UserConfidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        case.user_confidence = serializer.validated_data['user_confidence']
        case.user_confidence_updated_at = timezone.now()

        if 'what_would_change_mind' in serializer.validated_data:
            case.what_would_change_mind = serializer.validated_data['what_would_change_mind']

        case.save(update_fields=[
            'user_confidence',
            'user_confidence_updated_at',
            'what_would_change_mind',
            'updated_at'
        ])

        return Response({
            'user_confidence': case.user_confidence,
            'user_confidence_updated_at': case.user_confidence_updated_at,
            'what_would_change_mind': case.what_would_change_mind,
        })

    @action(detail=True, methods=['patch'], url_path='premortem')
    def premortem(self, request, pk=None):
        """
        Save user's premortem text.

        PATCH /api/cases/{id}/premortem/
        Body: { "premortem_text": "..." }
        """
        case = self.get_object()
        premortem_text = request.data.get('premortem_text', '')

        case.premortem_text = premortem_text
        if premortem_text and not case.premortem_at:
            case.premortem_at = timezone.now()
        case.save(update_fields=['premortem_text', 'premortem_at', 'updated_at'])

        return Response({
            'premortem_text': case.premortem_text,
            'premortem_at': case.premortem_at,
        })

    @action(detail=True, methods=['post'], url_path='suggest-inquiries')
    async def suggest_inquiries(self, request, pk=None):
        """
        Get AI-suggested inquiries based on case context.

        POST /api/cases/{id}/suggest-inquiries/

        Returns: [{title, description, reason, priority}]
        """
        from apps.common.llm_providers import get_llm_provider, stream_json
        from apps.intelligence.case_prompts import build_inquiry_suggestion_prompt
        from asgiref.sync import sync_to_async

        case = await sync_to_async(self.get_object)()
        prompt = await sync_to_async(build_inquiry_suggestion_prompt)(case)

        provider = get_llm_provider('fast')
        suggestions = await stream_json(
            provider,
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You suggest inquiries to help make better decisions.",
            fallback=[],
            description="inquiry suggestions",
        )
        return Response(suggestions)

    @action(detail=True, methods=['post'], url_path='analyze-gaps')
    async def analyze_gaps(self, request, pk=None):
        """
        Analyze gaps and return as prompts for reflection.

        POST /api/cases/{id}/analyze-gaps/

        Returns prompts (not deficiencies) to encourage reflection:
        {
            prompts: [
                {type, text, action, signal_id?}
            ],
            # Legacy format also included for backwards compatibility
            missing_perspectives: [str],
            unvalidated_assumptions: [str],
            contradictions: [str],
            evidence_gaps: [str],
            recommendations: [str]
        }
        """
        from apps.common.llm_providers import get_llm_provider, stream_json
        from apps.intelligence.case_prompts import build_gap_analysis_prompt
        from asgiref.sync import sync_to_async

        case = await sync_to_async(self.get_object)()
        prompt = await sync_to_async(build_gap_analysis_prompt)(case)

        provider = get_llm_provider('fast')
        analysis = await stream_json(
            provider,
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You analyze decision cases to find gaps and blind spots.",
            fallback={
                'missing_perspectives': [],
                'unvalidated_assumptions': [],
                'contradictions': [],
                'evidence_gaps': [],
                'recommendations': []
            },
            description="gap analysis",
        )

        # Convert to prompts format (new approach)
        prompts = []

        # Convert missing perspectives to prompts
        for perspective in analysis.get('missing_perspectives', []):
            prompts.append({
                'type': 'alternative',
                'text': f"Have you considered: {perspective}",
                'action': 'create_inquiry',
            })

        # Convert unvalidated assumptions to prompts
        for assumption in analysis.get('unvalidated_assumptions', []):
            prompts.append({
                'type': 'assumption',
                'text': f"You're assuming: {assumption}. Want to validate this?",
                'action': 'investigate',
            })

        # Convert evidence gaps to prompts
        for gap in analysis.get('evidence_gaps', []):
            prompts.append({
                'type': 'evidence_gap',
                'text': gap,
                'action': 'add_evidence',
            })

        # Include prompts in response alongside legacy format
        analysis['prompts'] = prompts[:10]  # Limit to 10 prompts

        return Response(analysis)

    @action(detail=True, methods=['post'], url_path='suggest-evidence-sources')
    async def suggest_evidence_sources(self, request, pk=None):
        """
        Get AI-suggested evidence sources for an inquiry.

        POST /api/cases/{id}/suggest-evidence-sources/
        Body: {"inquiry_id": "uuid"}

        Returns: [{suggestion, source_type, why_helpful, how_to_find}]
        """
        from apps.common.llm_providers import get_llm_provider, stream_json
        from apps.intelligence.case_prompts import build_evidence_suggestion_prompt
        from apps.inquiries.models import Inquiry
        from asgiref.sync import sync_to_async

        case = await sync_to_async(self.get_object)()
        inquiry_id = request.data.get('inquiry_id')

        if not inquiry_id:
            return Response(
                {'error': 'inquiry_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            inquiry = await sync_to_async(Inquiry.objects.get)(id=inquiry_id, case=case)
        except Inquiry.DoesNotExist:
            return Response(
                {'error': 'Inquiry not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        prompt = await sync_to_async(build_evidence_suggestion_prompt)(case, inquiry)
        provider = get_llm_provider('fast')

        suggestions = await stream_json(
            provider,
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You suggest evidence sources to help validate inquiries.",
            fallback=[],
            description="evidence source suggestions",
        )
        return Response(suggestions)

    # ── Brief Section Endpoints ──────────────────────────────────────

    @action(detail=True, methods=['get', 'post'], url_path='brief-sections')
    def brief_sections(self, request, pk=None):
        """
        List or create brief sections for this case's main brief.

        GET /api/cases/{id}/brief-sections/
        Returns all sections with annotations.

        POST /api/cases/{id}/brief-sections/
        Creates a new section and inserts markdown marker.
        Body: {heading, section_type?, order?, parent_section?, inquiry?, after_section_id?}
        """
        case = self.get_object()

        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        brief = case.main_brief

        if request.method == 'GET':
            # Return top-level sections (subsections nested via serializer)
            sections = BriefSection.objects.filter(
                brief=brief,
                parent_section__isnull=True
            ).select_related(
                'inquiry'
            ).prefetch_related(
                'annotations',
                'subsections',
                'subsections__annotations',
                'subsections__inquiry',
            ).order_by('order')

            serializer = BriefSectionSerializer(sections, many=True)
            return Response({
                'sections': serializer.data,
                'brief_id': str(brief.id),
            })

        elif request.method == 'POST':
            serializer = BriefSectionCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            # Determine order (inside transaction to prevent duplicate ordering)
            with transaction.atomic():
                if 'after_section_id' in data and data['after_section_id']:
                    try:
                        after_section = BriefSection.objects.select_for_update().get(
                            brief=brief, section_id=data['after_section_id']
                        )
                        order = after_section.order + 1
                        # Shift subsequent sections
                        BriefSection.objects.filter(
                            brief=brief, order__gte=order
                        ).update(order=models.F('order') + 1)
                    except BriefSection.DoesNotExist:
                        order = data.get('order', 0)
                elif 'order' in data:
                    order = data['order']
                else:
                    max_order = BriefSection.objects.filter(
                        brief=brief
                    ).order_by('-order').values_list('order', flat=True).first() or 0
                    order = max_order + 1

            # Resolve parent section
            parent_section = None
            if data.get('parent_section'):
                try:
                    parent_section = BriefSection.objects.get(
                        id=data['parent_section'], brief=brief
                    )
                except BriefSection.DoesNotExist:
                    logger.debug("Parent section %s not found, skipping", data.get('parent_section'))

            # Resolve inquiry
            inquiry = None
            if data.get('inquiry'):
                from apps.inquiries.models import Inquiry
                try:
                    inquiry = Inquiry.objects.get(id=data['inquiry'], case=case)
                except Inquiry.DoesNotExist:
                    return Response(
                        {'error': 'Inquiry not found in this case'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Generate section ID and create
            section_id = BriefSection.generate_section_id()
            section = BriefSection.objects.create(
                brief=brief,
                section_id=section_id,
                heading=data['heading'],
                order=order,
                section_type=data.get('section_type', 'custom'),
                inquiry=inquiry,
                parent_section=parent_section,
                created_by='user',
                is_linked=bool(inquiry),
            )

            # Insert markdown marker into brief content
            marker = f'\n<!-- section:{section_id} -->\n## {data["heading"]}\n\n'
            if brief.content_markdown:
                brief.content_markdown += marker
            else:
                brief.content_markdown = marker
            brief.save(update_fields=['content_markdown', 'updated_at'])

            # Emit provenance event
            from apps.events.services import EventService
            from apps.events.models import EventType, ActorType
            EventService.append(
                event_type=EventType.BRIEF_SECTION_WRITTEN,
                payload={
                    'section_id': str(section.id),
                    'section_title': section.heading,
                    'section_type': section.section_type,
                    'authored_by': 'user',
                },
                actor_type=ActorType.USER,
                actor_id=request.user.id,
                case_id=case.id,
            )

            return Response(
                BriefSectionSerializer(section).data,
                status=status.HTTP_201_CREATED
            )

    @action(detail=True, methods=['patch', 'delete'], url_path=r'brief-sections/(?P<section_id>[^/.]+)')
    def brief_section_detail(self, request, pk=None, section_id=None):
        """
        Update or delete a specific brief section.

        PATCH /api/cases/{id}/brief-sections/{section_id}/
        Body: {heading?, order?, section_type?, inquiry?, parent_section?, is_collapsed?}

        DELETE /api/cases/{id}/brief-sections/{section_id}/
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            section = BriefSection.objects.get(id=section_id, brief=case.main_brief)
        except BriefSection.DoesNotExist:
            return Response(
                {'error': 'Brief section not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.method == 'DELETE':
            # Remove markdown marker
            marker_tag = f'<!-- section:{section.section_id} -->'
            if case.main_brief.content_markdown:
                case.main_brief.content_markdown = case.main_brief.content_markdown.replace(
                    marker_tag, ''
                )
                case.main_brief.save(update_fields=['content_markdown', 'updated_at'])
            section.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH
        serializer = BriefSectionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if 'heading' in data:
            # Update heading in markdown too
            old_heading = section.heading
            new_heading = data['heading']
            if case.main_brief.content_markdown and old_heading:
                case.main_brief.content_markdown = case.main_brief.content_markdown.replace(
                    f'## {old_heading}', f'## {new_heading}', 1
                )
                case.main_brief.save(update_fields=['content_markdown', 'updated_at'])
            section.heading = new_heading

        if 'order' in data:
            section.order = data['order']
        if 'section_type' in data:
            section.section_type = data['section_type']
        if 'is_collapsed' in data:
            section.is_collapsed = data['is_collapsed']

        if 'parent_section' in data:
            if data['parent_section']:
                try:
                    parent = BriefSection.objects.get(
                        id=data['parent_section'], brief=case.main_brief
                    )
                    section.parent_section = parent
                except BriefSection.DoesNotExist:
                    logger.debug("Parent section %s not found, skipping", data.get('parent_section'))
            else:
                section.parent_section = None

        if 'inquiry' in data:
            if data['inquiry']:
                from apps.inquiries.models import Inquiry
                try:
                    inquiry = Inquiry.objects.get(id=data['inquiry'], case=case)
                    section.inquiry = inquiry
                    section.is_linked = True
                except Inquiry.DoesNotExist:
                    return Response(
                        {'error': 'Inquiry not found in this case'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                section.inquiry = None
                section.is_linked = False

        # Track if content-related fields changed for provenance
        content_changed = 'heading' in data or 'section_type' in data or 'inquiry' in data
        _section_update_fields = ['updated_at']
        for _f in ('heading', 'order', 'section_type', 'is_collapsed',
                    'parent_section', 'inquiry', 'is_linked'):
            if _f in data or _f == 'is_linked':
                _section_update_fields.append(_f)
        section.save(update_fields=_section_update_fields)

        if content_changed:
            from apps.events.services import EventService
            from apps.events.models import EventType, ActorType
            EventService.append(
                event_type=EventType.BRIEF_SECTION_REVISED,
                payload={
                    'section_id': str(section.id),
                    'section_title': section.heading,
                    'revised_by': 'user',
                },
                actor_type=ActorType.USER,
                actor_id=request.user.id,
                case_id=case.id,
            )

        return Response(BriefSectionSerializer(section).data)

    @action(detail=True, methods=['post'], url_path='brief-sections/reorder')
    def brief_sections_reorder(self, request, pk=None):
        """
        Bulk reorder brief sections.

        POST /api/cases/{id}/brief-sections/reorder/
        Body: {sections: [{id, order}, ...]}
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BriefSectionReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for item in serializer.validated_data['sections']:
            BriefSection.objects.filter(
                id=item['id'], brief=case.main_brief
            ).update(order=item['order'])

        return Response({'status': 'reordered'})

    @action(detail=True, methods=['post'], url_path=r'brief-sections/(?P<section_id>[^/.]+)/link-inquiry')
    def brief_section_link_inquiry(self, request, pk=None, section_id=None):
        """
        Link a brief section to an inquiry.

        POST /api/cases/{id}/brief-sections/{section_id}/link-inquiry/
        Body: {inquiry_id: UUID}
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            section = BriefSection.objects.get(id=section_id, brief=case.main_brief)
        except BriefSection.DoesNotExist:
            return Response(
                {'error': 'Brief section not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        inquiry_id = request.data.get('inquiry_id')
        if not inquiry_id:
            return Response(
                {'error': 'inquiry_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.inquiries.models import Inquiry
        try:
            inquiry = Inquiry.objects.get(id=inquiry_id, case=case)
        except Inquiry.DoesNotExist:
            return Response(
                {'error': 'Inquiry not found in this case'},
                status=status.HTTP_404_NOT_FOUND
            )

        section.inquiry = inquiry
        section.is_linked = True
        section.section_type = 'inquiry_brief'
        section.save(update_fields=['inquiry', 'is_linked', 'section_type', 'updated_at'])

        return Response(BriefSectionSerializer(section).data)

    @action(detail=True, methods=['post'], url_path=r'brief-sections/(?P<section_id>[^/.]+)/unlink-inquiry')
    def brief_section_unlink_inquiry(self, request, pk=None, section_id=None):
        """
        Unlink a brief section from its inquiry.

        POST /api/cases/{id}/brief-sections/{section_id}/unlink-inquiry/
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            section = BriefSection.objects.get(id=section_id, brief=case.main_brief)
        except BriefSection.DoesNotExist:
            return Response(
                {'error': 'Brief section not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            section.inquiry = None
            section.is_linked = False
            section.grounding_status = 'empty'
            section.grounding_data = {}
            section.save(update_fields=[
                'inquiry', 'is_linked', 'grounding_status',
                'grounding_data', 'updated_at',
            ])

            # Clear annotations that came from the inquiry link
            section.annotations.filter(source_inquiry__isnull=False).delete()

        return Response(BriefSectionSerializer(section).data)

    @action(
        detail=True, methods=['post'],
        url_path=r'brief-sections/(?P<section_id>[^/.]+)/dismiss-annotation/(?P<annotation_id>[^/.]+)'
    )
    def brief_section_dismiss_annotation(self, request, pk=None, section_id=None, annotation_id=None):
        """
        Dismiss an annotation on a brief section.

        POST /api/cases/{id}/brief-sections/{section_id}/dismiss-annotation/{annotation_id}/
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            section = BriefSection.objects.get(id=section_id, brief=case.main_brief)
            annotation = section.annotations.get(id=annotation_id)
        except (BriefSection.DoesNotExist, BriefAnnotation.DoesNotExist):
            return Response(
                {'error': 'Section or annotation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        annotation.dismissed_at = timezone.now()
        annotation.save(update_fields=['dismissed_at', 'updated_at'])

        return Response({'status': 'dismissed'})

    @action(detail=True, methods=['post'], url_path='evolve-brief')
    def evolve_brief(self, request, pk=None):
        """
        Trigger brief grounding recomputation.

        POST /api/cases/{id}/evolve-brief/
        Recomputes grounding status and annotations for all brief sections.
        Uses a cache-based lock to prevent concurrent evolve operations.
        """
        from django.core.cache import cache as django_cache

        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prevent concurrent evolve requests for the same case
        lock_key = f"evolve_brief_lock:{case.id}"
        if not django_cache.add(lock_key, True, timeout=120):
            return Response(
                {'status': 'already_evolving', 'message': 'Brief evolution already in progress'},
                status=status.HTTP_409_CONFLICT
            )

        try:
            from apps.cases.brief_grounding import BriefGroundingEngine
            delta = BriefGroundingEngine.evolve_brief(case.id)

            # Build detailed diff for the frontend
            section_changes = []
            for s in delta.get('updated_sections', []):
                section_changes.append({
                    'id': s['id'],
                    'heading': s['heading'],
                    'old_status': s.get('old_status', ''),
                    'new_status': s.get('new_status', ''),
                })

            new_anns = []
            for a in delta.get('new_annotations', []):
                new_anns.append({
                    'id': a['id'],
                    'type': a['type'],
                    'section_heading': a.get('section_heading', ''),
                })

            resolved_anns = []
            for a in delta.get('resolved_annotations', []):
                resolved_anns.append({
                    'id': a['id'],
                    'type': a['type'],
                    'section_heading': a.get('section_heading', ''),
                })

            return Response({
                'status': 'evolved',
                'updated_sections': len(section_changes),
                'new_annotations': len(new_anns),
                'resolved_annotations': len(resolved_anns),
                'readiness_created': delta.get('readiness_created', 0),
                'readiness_auto_completed': delta.get('readiness_auto_completed', 0),
                'diff': {
                    'section_changes': section_changes,
                    'new_annotations': new_anns,
                    'resolved_annotations': resolved_anns,
                },
            })
        except Exception as e:
            logger.error(f"Failed to evolve brief for case {case.id}: {e}")
            return Response(
                {'error': 'Failed to evolve brief', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            django_cache.delete(lock_key)

    @action(detail=True, methods=['get'], url_path='brief-overview')
    def brief_overview(self, request, pk=None):
        """
        Get lightweight brief overview with grounding status.

        GET /api/cases/{id}/brief-overview/
        Returns sections with status + annotation counts only.
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BriefOverviewSerializer(case.main_brief)
        return Response(serializer.data)

    # ── Case Scaffolding ─────────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='scaffold')
    def scaffold(self, request):
        """
        Scaffold a new case from a chat transcript or minimal input.

        POST /api/cases/scaffold/

        Body (chat mode):
            { "project_id": "uuid", "thread_id": "uuid", "mode": "chat" }

        Body (minimal mode):
            { "project_id": "uuid", "title": "...", "decision_question": "...", "mode": "minimal" }

        Returns: { case, brief, inquiries, sections }
        """
        from .scaffold_service import CaseScaffoldService

        mode = request.data.get('mode', 'minimal')
        project_id = request.data.get('project_id')

        if not project_id:
            return Response(
                {'error': 'project_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if mode == 'chat':
                thread_id = request.data.get('thread_id')
                if not thread_id:
                    return Response(
                        {'error': 'thread_id is required for chat scaffolding'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Get thread transcript
                from apps.chat.models import ChatThread, Message

                try:
                    thread = ChatThread.objects.get(
                        id=thread_id,
                        user=request.user
                    )
                except ChatThread.DoesNotExist:
                    return Response(
                        {'error': 'Thread not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                messages = Message.objects.filter(
                    thread=thread
                ).order_by('created_at')

                transcript = [
                    {'role': m.role, 'content': m.content}
                    for m in messages
                ]

                # Load skill context from thread's case (if any)
                scaffold_skill_context = None
                try:
                    from apps.skills.injection import build_skill_context
                    _case = thread.primary_case
                    if _case:
                        _skills = list(_case.active_skills.filter(status='active'))
                        if _skills:
                            scaffold_skill_context = build_skill_context(_skills, 'brief')
                except Exception as e:
                    logger.warning(f"Could not load skills for chat scaffold: {e}")

                # Run async scaffold
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(
                        CaseScaffoldService.scaffold_from_chat(
                            transcript=transcript,
                            user=request.user,
                            project_id=project_id,
                            thread_id=thread_id,
                            skill_context=scaffold_skill_context,
                        )
                    )
                finally:
                    loop.close()

            else:
                # Minimal scaffold
                title = request.data.get('title', 'New Case')
                decision_question = request.data.get('decision_question')

                # Optionally load skill sections for minimal scaffold
                skill_sections = None
                skill_id = request.data.get('skill_id')
                pack_slug = request.data.get('pack_slug')

                if pack_slug:
                    # SkillPack was removed during skill system cleanup
                    logger.warning(f"pack_slug provided but SkillPack no longer exists: {pack_slug}")

                elif skill_id:
                    try:
                        from apps.skills.models import Skill
                        from apps.skills.injection import extract_brief_sections_from_skill
                        skill = Skill.objects.get(id=skill_id)
                        skill_sections = extract_brief_sections_from_skill(skill)
                    except (Skill.DoesNotExist, ValueError) as e:
                        logger.warning(f"Could not load skill for minimal scaffold: {e}")

                result = CaseScaffoldService.scaffold_minimal(
                    title=title,
                    user=request.user,
                    project_id=project_id,
                    decision_question=decision_question,
                    skill_sections=skill_sections,
                )

            # Serialize response
            case_data = CaseSerializer(result['case']).data
            brief_data = WorkingDocumentSerializer(result['brief']).data
            sections_data = BriefSectionSerializer(result['sections'], many=True).data

            return Response({
                'case': case_data,
                'brief': brief_data,
                'inquiries': [
                    {'id': str(inq.id), 'title': inq.title}
                    for inq in result.get('inquiries', [])
                ],
                'sections': sections_data,
                'signals_count': len(result.get('signals', [])),
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Scaffold failed: {e}")
            return Response(
                {'error': 'Scaffolding failed', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ═══ Export Endpoints ═════════════════════════════════════════════

    @action(detail=True, methods=['get'], url_path='export')
    def export_brief(self, request, pk=None):
        """
        Export the full brief reasoning graph as structured JSON.

        GET /api/cases/{id}/export/?type=full
        GET /api/cases/{id}/export/?type=executive_summary
        GET /api/cases/{id}/export/?type=per_section&sections=sf-abc123,sf-def456

        Returns the BriefExportGraph IR — a structured representation of the
        case's reasoning chain (claims → evidence → assumptions → confidence)
        suitable for rendering into slides, memos, or reports.
        """
        case = self.get_object()
        export_type = request.query_params.get('type', 'full')
        section_ids_param = request.query_params.get('sections', '')
        section_ids = [s.strip() for s in section_ids_param.split(',') if s.strip()] or None

        valid_types = ('full', 'executive_summary', 'per_section')
        if export_type not in valid_types:
            return Response(
                {'error': f"Invalid export type: {export_type}. Must be one of: {', '.join(valid_types)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if export_type == 'per_section' and not section_ids:
            return Response(
                {'error': 'sections parameter required for per_section export type'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from apps.cases.export_service import BriefExportService
            export_data = BriefExportService.export(
                case_id=case.id,
                export_type=export_type,
                section_ids=section_ids,
                user=request.user,
            )
            return Response(export_data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Export failed for case {case.id}: {e}", exc_info=True)
            return Response(
                {'error': 'Export failed', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ═══ Investigation Plan Endpoints ════════════════════════════════

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
        # Return the updated plan
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
        version = PlanService.create_new_version(
            case_id=case.id,
            content=serializer.validated_data['content'],
            created_by='ai_proposal',
            diff_summary=serializer.validated_data['diff_summary'],
            diff_data=serializer.validated_data.get('diff_data'),
            actor_type=ActorType.USER,
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
            return Response(
                {'detail': str(e)},
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
            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(PlanVersionSerializer(version).data)

    # ═══ Case Home (Aggregated) ══════════════════════════════════════

    @action(detail=True, methods=['get'])
    def home(self, request, pk=None):
        """
        Aggregated endpoint for the case home workspace.

        GET /api/cases/{id}/home/

        Returns everything needed to render the case home in one call:
        plan, inquiries with evidence counts, recent signals, activity, health.
        """
        case = self.get_object()

        # Plan + current version
        plan_data = None
        try:
            plan_obj = case.plan
            plan_data = InvestigationPlanSerializer(plan_obj).data
        except InvestigationPlan.DoesNotExist:
            logger.debug("No plan for case %s", case.id)

        # Inquiries
        from apps.inquiries.models import Inquiry

        inquiries = (
            Inquiry.objects.filter(case=case)
            .order_by('sequence_index')
        )
        inquiry_data = []
        for inq in inquiries:
            inquiry_data.append({
                'id': str(inq.id),
                'title': inq.title,
                'status': inq.status,
                'priority': inq.priority,
                'sequence_index': inq.sequence_index,
                'conclusion': inq.conclusion,
            })

        # Recent provenance events (last 5)
        from apps.events.models import Event, EventCategory
        recent_events = Event.objects.filter(
            case_id=case.id,
            category=EventCategory.PROVENANCE,
        ).order_by('-timestamp')[:5]
        event_data = [{
            'id': str(e.id),
            'type': e.type,
            'payload': e.payload,
            'timestamp': e.timestamp.isoformat(),
            'actor_type': e.actor_type,
        } for e in recent_events]

        return Response({
            'case': CaseSerializer(case).data,
            'plan': plan_data,
            'inquiries': inquiry_data,
            'activity': {
                'recent_events': event_data,
            },
        })

    # ═══ Plan Generation ══════════════════════════════════════

    @action(detail=True, methods=['post'], url_path='generate-plan')
    def generate_plan(self, request, pk=None):
        """
        Generate an investigation plan for a case that doesn't have one.

        POST /api/cases/{id}/generate-plan/

        Uses existing case data (brief sections, inquiries) to bootstrap a plan.
        Returns 409 if the case already has a plan.
        """
        case = self.get_object()

        # Check if plan already exists
        try:
            existing = case.plan  # noqa: F841
            return Response(
                {'error': 'Case already has a plan'},
                status=status.HTTP_409_CONFLICT
            )
        except InvestigationPlan.DoesNotExist:
            pass

        # Gather case data to build plan from
        from apps.inquiries.models import Inquiry
        inquiries = list(
            Inquiry.objects.filter(case=case).order_by('sequence_index')
        )

        # Build analysis dict from existing case data
        analysis = {
            'assumptions': [],
            'decision_criteria': [],
            'position_draft': case.position or '',
        }

        # Extract assumptions from brief sections if available
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

    @action(detail=True, methods=['get'], url_path='section-judgment-summary')
    def section_judgment_summary(self, request, pk=None):
        """
        Get synthesis summary comparing user judgment vs structural grounding.

        GET /api/cases/{id}/section-judgment-summary/

        Returns per-section comparison and highlighted mismatches.
        """
        from apps.cases.brief_models import BriefSection, GroundingStatus  # noqa: F811

        case = self.get_object()
        if not case.main_brief:
            return Response({'sections': [], 'mismatches': []})

        sections = BriefSection.objects.filter(
            brief=case.main_brief,
        ).exclude(section_type='decision_frame').order_by('order')

        # Map grounding status to a numeric strength for comparison
        grounding_strength = {
            'empty': 0,
            'weak': 1,
            'moderate': 2,
            'strong': 3,
            'conflicted': 1,  # Conflicted is structurally weak
        }

        results = []
        mismatches = []

        for section in sections:
            structural_strength = grounding_strength.get(section.grounding_status, 0)
            user_rating = section.user_confidence  # 1-4 or None

            section_data = {
                'section_id': section.section_id,
                'heading': section.heading,
                'section_type': section.section_type,
                'grounding_status': section.grounding_status,
                'grounding_strength': structural_strength,
                'user_confidence': user_rating,
                'evidence_count': section.grounding_data.get('evidence_count', 0),
                'tensions_count': section.grounding_data.get('tensions_count', 0),
            }
            results.append(section_data)

            # Detect mismatches
            if user_rating is not None:
                # User says high confidence (3-4) but structure is weak (0-1)
                if user_rating >= 3 and structural_strength <= 1:
                    mismatches.append({
                        'section_id': section.section_id,
                        'heading': section.heading,
                        'type': 'overconfident',
                        'description': f'You rated high confidence but evidence is {section.grounding_status}',
                        'user_confidence': user_rating,
                        'grounding_status': section.grounding_status,
                    })
                # User says low confidence (1-2) but structure is strong (3)
                elif user_rating <= 2 and structural_strength >= 3:
                    mismatches.append({
                        'section_id': section.section_id,
                        'heading': section.heading,
                        'type': 'underconfident',
                        'description': 'You rated low confidence but evidence is strong',
                        'user_confidence': user_rating,
                        'grounding_status': section.grounding_status,
                    })

        return Response({
            'sections': results,
            'mismatches': mismatches,
            'rated_count': sum(1 for s in results if s['user_confidence'] is not None),
            'total_count': len(results),
        })


class WorkingDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for case documents - briefs, research, sources, notes, etc.
    
    Supports:
    - CRUD operations on documents
    - Citation management
    - Filtering by case, inquiry, type
    - Edit permission enforcement
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return WorkingDocumentListSerializer
        elif self.action == 'create':
            return WorkingDocumentCreateSerializer
        return WorkingDocumentSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        """Validate case ownership, set created_by, emit provenance event."""
        case = serializer.validated_data.get('case')
        if case and case.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot create documents in another user's case.")
        document = serializer.save(created_by=self.request.user)
        from apps.events.services import EventService
        from apps.events.models import EventType, ActorType
        EventService.append(
            event_type=EventType.DOCUMENT_ADDED,
            payload={
                'document_id': str(document.id),
                'document_name': document.title,
                'document_type': document.document_type,
                'source': 'upload',
            },
            actor_type=ActorType.USER,
            actor_id=self.request.user.id,
            case_id=document.case_id,
        )

    def get_queryset(self):
        # Users can only see documents from their own cases
        queryset = WorkingDocument.objects.filter(case__user=self.request.user)
        
        # Filter by case
        case_id = self.request.query_params.get('case')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        
        # Filter by inquiry
        inquiry_id = self.request.query_params.get('inquiry')
        if inquiry_id:
            queryset = queryset.filter(inquiry_id=inquiry_id)
        
        # Filter by document type
        doc_type = self.request.query_params.get('type')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)
        
        # Filter by AI-generated
        ai_only = self.request.query_params.get('ai_only')
        if ai_only == 'true':
            queryset = queryset.filter(generated_by_ai=True)
        
        return queryset.select_related('case', 'inquiry', 'created_by').order_by('-created_at')
    
    def update(self, request, pk=None):
        """
        Update document content with automatic citation parsing.
        
        Enforces edit friction rules.
        """
        document = self.get_object()
        
        new_content = request.data.get('content_markdown')
        if new_content is not None:
            try:
                updated_doc = WorkingDocumentService.update_document_content(
                    document=document,
                    new_content=new_content,
                    user=request.user
                )
                
                serializer = self.get_serializer(updated_doc)
                return Response(serializer.data)
                
            except PermissionError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # If no content update, use default update
        return super().update(request, pk)
    
    @action(detail=True, methods=['get'])
    def citations(self, request, pk=None):
        """
        Get all citations to/from this document.
        
        GET /api/case-documents/{id}/citations/
        
        Returns:
        {
            "outgoing": [...],  // Documents this cites
            "incoming": [...],  // Documents that cite this
            "outgoing_count": 3,
            "incoming_count": 5
        }
        """
        document = self.get_object()

        outgoing = document.outgoing_citations.select_related('from_document', 'to_document').all()
        incoming = document.incoming_citations.select_related('from_document', 'to_document').all()
        
        return Response({
            'outgoing': DocumentCitationSerializer(outgoing, many=True).data,
            'incoming': DocumentCitationSerializer(incoming, many=True).data,
            'outgoing_count': outgoing.count(),
            'incoming_count': incoming.count(),
        })
    
    @action(detail=True, methods=['post'])
    def reparse_citations(self, request, pk=None):
        """
        Manually trigger citation reparsing.
        
        POST /api/case-documents/{id}/reparse_citations/
        
        Useful if citations were broken or need updating.
        """
        from apps.cases.citation_parser import CitationParser
        
        document = self.get_object()
        citations_created = CitationParser.create_citation_links(document)
        
        return Response({
            'message': f'Reparsed citations for {document.title}',
            'citations_created': citations_created
        })
    
    @action(detail=True, methods=['post'])
    async def integrate_content(self, request, pk=None):
        """
        Intelligently integrate content from chat into document.
        AI determines best placement, formatting, and citation.

        POST /api/case-documents/{id}/integrate_content/
        Body: {
            "content": "content to integrate",
            "hint": "evidence|assumption|conclusion",
            "message_id": "optional-message-uuid"
        }
        Returns: {"updated_content": "...", "insertion_section": "..."}
        """
        from apps.common.llm_providers import get_llm_provider, stream_json
        from apps.intelligence.case_prompts import build_content_integration_prompt
        from asgiref.sync import sync_to_async

        document = await sync_to_async(self.get_object)()
        content_to_add = request.data.get('content', '')
        hint = request.data.get('hint', 'general')
        message_id = request.data.get('message_id')

        if not content_to_add:
            return Response(
                {'error': 'Content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        doc_content = await sync_to_async(lambda: document.content_markdown)()

        system_prompt, user_prompt = build_content_integration_prompt(
            document_content=doc_content,
            content_to_add=content_to_add,
            hint=hint,
        )

        provider = get_llm_provider('fast')
        result = await stream_json(
            provider,
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            fallback={
                "updated_content": f"{doc_content}\n\n{content_to_add}\n\n[^chat]",
                "insertion_section": "End of document",
                "rewritten_content": content_to_add
            },
            description="document content integration",
        )
        return Response(result)
    
    @action(detail=True, methods=['post'], url_path='generate-suggestions')
    async def generate_suggestions(self, request, pk=None):
        """
        Generate AI suggestions for improving this document.

        POST /api/case-documents/{id}/generate-suggestions/

        Returns: [{
            id, section_id, suggestion_type, current_content,
            suggested_content, reason, linked_signal_id, confidence, status
        }]
        """
        from .suggestions import generate_brief_suggestions
        from apps.common.llm_providers import get_llm_provider, stream_json
        from apps.intelligence.case_prompts import build_gap_analysis_prompt
        from asgiref.sync import sync_to_async

        document = await sync_to_async(self.get_object)()
        case = await sync_to_async(lambda: document.case)()

        # Build case context (sync ORM queries wrapped)
        @sync_to_async
        def _build_context():
            inquiries = list(case.inquiries.values('id', 'title', 'status', 'conclusion'))
            return inquiries

        inquiries = await _build_context()

        # Get gaps via LLM
        gaps = {}
        try:
            prompt = await sync_to_async(build_gap_analysis_prompt)(case)
            provider = get_llm_provider('fast')
            gaps = await stream_json(
                provider,
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You analyze decision cases to find gaps.",
                fallback={},
                description="gap analysis for suggestions",
            )
        except Exception as e:
            logger.debug("Gap analysis failed for case document: %s", e)

        # Include grounding data + annotations from BriefSections
        @sync_to_async
        def _build_grounding():
            grounding_data = []
            try:
                from apps.cases.brief_models import BriefSection
                sections = BriefSection.objects.filter(
                    brief=document,
                    parent_section__isnull=True,
                ).prefetch_related('annotations').order_by('order')
                for sec in sections:
                    active_annotations = [
                        {
                            'type': a.annotation_type,
                            'description': a.description,
                            'priority': a.priority,
                        }
                        for a in sec.annotations.all()
                        if a.dismissed_at is None and a.resolved_at is None
                    ]
                    grounding_data.append({
                        'section_id': sec.section_id,
                        'heading': sec.heading,
                        'grounding_status': sec.grounding_status,
                        'is_linked': sec.is_linked,
                        'annotations': active_annotations,
                    })
            except Exception as e:
                logger.warning("Failed to build grounding data: %s", e)
            return grounding_data

        grounding_data = await _build_grounding()

        case_context = {
            'decision_question': case.decision_question,
            'inquiries': inquiries,
            'gaps': gaps,
            'grounding': grounding_data,
        }

        max_suggestions = request.data.get('max_suggestions', 5)
        brief_content = await sync_to_async(lambda: document.content_markdown)()
        suggestions = await sync_to_async(generate_brief_suggestions)(
            brief_content=brief_content,
            case_context=case_context,
            max_suggestions=max_suggestions
        )

        return Response(suggestions)

    @action(detail=True, methods=['post'], url_path='apply-suggestion')
    def apply_suggestion(self, request, pk=None):
        """
        Apply a suggestion to document content.

        POST /api/case-documents/{id}/apply-suggestion/
        Body: {
            suggestion: {id, suggestion_type, current_content, suggested_content, ...}
        }

        Returns: {updated_content, suggestion_applied}
        """
        from django.db import transaction
        from .suggestions import apply_suggestion

        document = self.get_object()
        suggestion = request.data.get('suggestion')

        if not suggestion:
            return Response(
                {'error': 'suggestion is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Snapshot before overwriting
            WorkingDocumentVersion.create_snapshot(
                document,
                created_by='ai_suggestion',
                diff_summary=f"Before applying suggestion: {suggestion.get('suggestion_type', 'unknown')}",
                task_description=suggestion.get('reason', ''),
            )

            # Apply the suggestion
            updated_content = apply_suggestion(
                document_content=document.content_markdown,
                suggestion=suggestion
            )

            # Save the updated content
            document.content_markdown = updated_content
            document.save(update_fields=['content_markdown', 'updated_at'])

        return Response({
            'updated_content': updated_content,
            'suggestion_applied': suggestion.get('id')
        })

    @action(detail=True, methods=['post'], url_path='inline-complete')
    def inline_complete(self, request, pk=None):
        """
        Get inline completion for ghost text.

        POST /api/case-documents/{id}/inline-complete/
        Body: {
            context_before: str,
            context_after: str,
            max_length: int (optional, default 50)
        }

        Returns: {completion: str | null}
        """
        from .suggestions import get_inline_completion

        document = self.get_object()
        context_before = request.data.get('context_before', '')
        context_after = request.data.get('context_after', '')
        max_length = request.data.get('max_length', 50)

        if len(context_before) < 10:
            return Response({'completion': None})

        completion = get_inline_completion(
            context_before=context_before,
            context_after=context_after,
            max_length=max_length
        )

        return Response({'completion': completion})

    @action(detail=True, methods=['get'], url_path='background-analysis')
    def background_analysis(self, request, pk=None):
        """
        Get or trigger background analysis for this document.

        GET /api/case-documents/{id}/background-analysis/

        Query params:
        - force: bool (default false) - Force re-analysis even if cached

        Returns comprehensive analysis including health score, issues,
        suggestions, evidence gaps, and metrics.
        """
        from .background_analysis import (
            should_reanalyze,
            get_cached_analysis,
            run_background_analysis
        )

        document = self.get_object()
        case = document.case
        force = request.query_params.get('force', 'false').lower() == 'true'

        # Check if we need to analyze
        if not force and not should_reanalyze(str(document.id), document.content_markdown):
            cached = get_cached_analysis(str(document.id))
            if cached:
                return Response(cached)

        # Build case context
        inquiries = list(case.inquiries.values('id', 'title', 'status'))

        case_context = {
            'decision_question': case.decision_question,
            'inquiries': inquiries,
        }

        # Run analysis
        analysis = run_background_analysis(
            document_id=str(document.id),
            content=document.content_markdown,
            case_context=case_context
        )

        return Response(analysis)

    @action(detail=True, methods=['get'], url_path='health')
    def document_health(self, request, pk=None):
        """
        Get quick health metrics for this document.

        GET /api/case-documents/{id}/health/

        Returns cached health score and issue counts.
        """
        from .background_analysis import get_document_health

        document = self.get_object()
        health = get_document_health(str(document.id))

        if health is None:
            return Response({
                'health_score': None,
                'message': 'No analysis available. Trigger background-analysis first.'
            })

        return Response(health)

    @action(detail=True, methods=['post'], url_path='execute-task')
    def execute_task(self, request, pk=None):
        """
        Execute an agentic document editing task.

        POST /api/case-documents/{id}/execute-task/
        Body: {
            task: str (e.g., "Add citations to all claims")
        }

        Returns the task result with plan, changes, and final content.
        """
        from .agentic_tasks import execute_agentic_task

        document = self.get_object()
        case = document.case
        task_description = request.data.get('task')

        if not task_description:
            return Response(
                {'error': 'task is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build case context
        inquiries = list(case.inquiries.values('id', 'title', 'status', 'conclusion'))

        case_context = {
            'decision_question': case.decision_question,
            'inquiries': inquiries,
        }

        # Execute the task
        result = execute_agentic_task(
            task_description=task_description,
            document_content=document.content_markdown,
            case_context=case_context
        )

        return Response(result)

    @action(detail=True, methods=['post'], url_path='execute-task-stream')
    def execute_task_stream(self, request, pk=None):
        """
        Streaming version of execute-task. Returns SSE events as the task progresses.

        POST /api/case-documents/{id}/execute-task-stream/
        Body: { task: str }

        Events: phase, plan, step_start, step_complete, review, done, error
        """
        import json as json_mod
        from django.http import StreamingHttpResponse
        from .agentic_tasks import stream_agentic_task

        document = self.get_object()
        case = document.case
        task_description = request.data.get('task')

        if not task_description:
            return Response(
                {'error': 'task is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        inquiries = list(case.inquiries.values('id', 'title', 'status', 'conclusion'))

        case_context = {
            'decision_question': case.decision_question,
            'inquiries': inquiries,
        }

        def event_stream():
            for event in stream_agentic_task(
                task_description=task_description,
                document_content=document.content_markdown,
                case_context=case_context,
            ):
                event_type = event.get('event', 'message')
                data = json_mod.dumps(event.get('data', {}), default=str)
                yield f"event: {event_type}\ndata: {data}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        origin = request.headers.get('Origin', 'http://localhost:3000')
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Credentials'] = 'true'
        return response

    @action(detail=True, methods=['post'], url_path='apply-task-result')
    def apply_task_result(self, request, pk=None):
        """
        Apply the result of an agentic task to the document.

        POST /api/case-documents/{id}/apply-task-result/
        Body: {
            final_content: str
        }

        Saves the final content from a task execution.
        """
        document = self.get_object()
        final_content = request.data.get('final_content')

        if not final_content:
            return Response(
                {'error': 'final_content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Snapshot before overwriting
        task_desc = request.data.get('task_description', '')
        WorkingDocumentVersion.create_snapshot(
            document,
            created_by='ai_task',
            diff_summary='Before applying agentic task result',
            task_description=task_desc,
        )

        document.content_markdown = final_content
        document.save(update_fields=['content_markdown', 'updated_at'])

        return Response({
            'success': True,
            'message': 'Task result applied successfully'
        })

    @action(detail=True, methods=['get'], url_path='version-history')
    def version_history(self, request, pk=None):
        """
        Get version history for a document.

        GET /api/case-documents/{id}/version-history/

        Returns list of version snapshots ordered by newest first.
        """
        document = self.get_object()
        versions = WorkingDocumentVersion.objects.filter(
            document=document
        ).order_by('-version')[:50]

        include_content = request.query_params.get('include_content', 'false').lower() == 'true'
        return Response([
            {
                'id': str(v.id),
                'version': v.version,
                'diff_summary': v.diff_summary,
                'created_by': v.created_by,
                'task_description': v.task_description,
                'created_at': v.created_at.isoformat(),
                **(
                    {'content_markdown': v.content_markdown}
                    if include_content else {}
                ),
            }
            for v in versions
        ])

    @action(detail=True, methods=['post'], url_path='restore-version')
    def restore_version(self, request, pk=None):
        """
        Restore document content from a version snapshot.

        POST /api/case-documents/{id}/restore-version/
        Body: { version_id: str }

        Creates a new version snapshot of the current content (as 'restore'),
        then overwrites with the target version's content.
        """
        document = self.get_object()
        version_id = request.data.get('version_id')

        if not version_id:
            return Response(
                {'error': 'version_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_version = WorkingDocumentVersion.objects.get(
                id=version_id,
                document=document
            )
        except WorkingDocumentVersion.DoesNotExist:
            return Response(
                {'error': 'Version not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Snapshot current content before restoring
        WorkingDocumentVersion.create_snapshot(
            document,
            created_by='restore',
            diff_summary=f'Before restoring to v{target_version.version}',
        )

        # Restore
        document.content_markdown = target_version.content_markdown
        document.save(update_fields=['content_markdown', 'updated_at'])

        return Response({
            'success': True,
            'restored_to_version': target_version.version,
            'content': document.content_markdown,
        })

    @action(detail=True, methods=['get'], url_path='validate-markers')
    def validate_markers(self, request, pk=None):
        """
        Validate section marker integrity for a brief document.

        GET /api/case-documents/{id}/validate-markers/

        Returns:
        {
            "valid": true/false,
            "missing_markers": ["sf-abc123"],   // in DB, not in content
            "orphaned_markers": ["sf-xyz789"],   // in content, no DB row
            "matched": ["sf-def456"]
        }
        """
        from .document_service import validate_section_markers

        document = self.get_object()
        result = validate_section_markers(document)
        return Response(result)

    @action(detail=True, methods=['post'])
    async def detect_assumptions(self, request, pk=None):
        """
        AI analyzes document to identify all assumptions.
        Cross-references with existing inquiries and assumption signals.

        POST /api/case-documents/{id}/detect_assumptions/
        Returns: [{
            text, status, risk_level, inquiry_id, validation_approach
        }]
        """
        from apps.common.llm_providers import get_llm_provider, stream_json
        from asgiref.sync import sync_to_async

        document = await sync_to_async(self.get_object)()

        @sync_to_async
        def _get_context():
            case = document.case
            inqs = list(case.inquiries.all())
            # Assumptions are now graph nodes, not signals
            try:
                from apps.graph.models import Node
                assumption_nodes = list(Node.objects.filter(
                    project=case.project,
                    node_type='assumption',
                ))
            except Exception:
                assumption_nodes = []
            return case, inqs, assumption_nodes

        case, inquiries, assumption_signals = await _get_context()

        doc_content = await sync_to_async(lambda: document.content_markdown)()

        from apps.intelligence.case_prompts import build_assumption_detection_prompt
        system_prompt, user_prompt = build_assumption_detection_prompt(
            document_content=doc_content,
            inquiries=inquiries,
            assumption_signals=assumption_signals,
        )

        provider = get_llm_provider('fast')
        assumptions = await stream_json(
            provider,
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            fallback=[],
            description="assumption detection",
        )

        # Enhance with inquiry links (pure Python, no ORM)
        if isinstance(assumptions, list):
            for assumption in assumptions:
                assumption_text = assumption.get('text', '').lower()
                for inquiry in inquiries:
                    if (
                        assumption_text in inquiry.title.lower() or
                        inquiry.title.lower() in assumption_text
                    ):
                        assumption['inquiry_id'] = str(inquiry.id)
                        assumption['status'] = 'validated' if inquiry.status == 'resolved' else 'investigating'
                        break

        return Response(assumptions)
    
    @action(detail=False, methods=['post'])
    def generate_research(self, request):
        """
        Generate AI research document.
        
        POST /api/case-documents/generate_research/
        {
            "inquiry_id": "uuid",
            "topic": "PostgreSQL performance analysis"  // optional, uses inquiry title if not provided
        }
        """
        from apps.agents.document_generator import AIDocumentGenerator
        from apps.inquiries.models import Inquiry
        
        inquiry_id = request.data.get('inquiry_id')
        
        if not inquiry_id:
            return Response(
                {'error': 'inquiry_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            inquiry = Inquiry.objects.get(id=inquiry_id, case__user=request.user)
        except Inquiry.DoesNotExist:
            return Response(
                {'error': 'Inquiry not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate research
        generator = AIDocumentGenerator()
        research_doc = generator.generate_research_for_inquiry(
            inquiry=inquiry,
            user=request.user
        )
        
        return Response(
            WorkingDocumentSerializer(research_doc, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'], url_path='generate-research-async')
    def generate_research_async(self, request):
        """
        Trigger async research generation via the multi-step research loop.

        POST /api/working-documents/generate-research-async/
        {
            "case_id": "uuid",
            "topic": "Research topic"
        }
        """
        case_id = request.data.get('case_id')
        topic = request.data.get('topic')

        if not case_id or not topic:
            return Response(
                {'error': 'case_id and topic are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.cases.models import Case
        try:
            Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        import uuid as uuid_module
        correlation_id = str(uuid_module.uuid4())

        from apps.agents.research_workflow import generate_research_document
        task = generate_research_document.delay(
            case_id=str(case_id),
            topic=topic,
            user_id=request.user.id,
            correlation_id=correlation_id,
        )

        return Response(
            {'task_id': task.id, 'status': 'generating'},
            status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=['patch'], url_path='section-confidence')
    def section_confidence(self, request, pk=None):
        """
        Set user's confidence for a brief section.

        PATCH /api/case-documents/{id}/section-confidence/
        Body: { "section_id": "sf-xxx", "confidence": 1-4 }
        """
        from apps.cases.brief_models import BriefSection

        document = self.get_object()
        section_id = request.data.get('section_id')
        confidence = request.data.get('confidence')

        if not section_id or confidence not in [1, 2, 3, 4, None]:
            return Response(
                {'error': 'section_id required, confidence must be 1-4 or null'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            section = BriefSection.objects.get(
                brief=document,
                section_id=section_id,
            )
        except BriefSection.DoesNotExist:
            return Response({'error': 'Section not found'}, status=status.HTTP_404_NOT_FOUND)

        section.user_confidence = confidence
        section.user_confidence_at = timezone.now() if confidence else None
        section.save(update_fields=['user_confidence', 'user_confidence_at', 'updated_at'])

        return Response({
            'section_id': section.section_id,
            'user_confidence': section.user_confidence,
            'user_confidence_at': section.user_confidence_at,
        })
