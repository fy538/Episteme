"""
Case views
"""
import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Case, CaseStatus, WorkingDocument, WorkingDocumentVersion, InvestigationPlan
from .brief_models import BriefSection
from .serializers import (
    CaseSerializer,
    CaseWithDecisionSerializer,
    CreateCaseSerializer,
    UpdateCaseSerializer,
    UserConfidenceSerializer,
    InvestigationPlanSerializer,
)
from .brief_views import BriefActionsMixin
from .plan_views import PlanActionsMixin
from .brief_serializers import (
    BriefSectionSerializer,
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
from apps.chat.serializers import ChatThreadDetailSerializer


class CaseViewSet(BriefActionsMixin, PlanActionsMixin, viewsets.ModelViewSet):
    """ViewSet for cases — brief and plan actions extracted to mixins."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = (
            Case.objects
            .filter(user=self.request.user)
            .exclude(status=CaseStatus.ARCHIVED)
            .select_related('based_on_skill', 'became_skill')
            .prefetch_related('caseactiveskill_set__skill')
        )
        # Filter by project when ?project=<uuid> is provided
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        # For list actions with project filter, use enhanced queryset
        if project_id and self.action == 'list':
            qs = qs.select_related('plan', 'decision')
        return qs

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
        # Use enhanced serializer when project filter is active
        project_id = self.request.query_params.get('project')
        if self.action == 'list' and project_id:
            return CaseWithDecisionSerializer
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
            decision_question=serializer.validated_data.get('decision_question', ''),
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
        except Exception as e:
            logger.debug("Unlinked claims lookup failed: %s", e)

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
                from asgiref.sync import async_to_sync
                result = async_to_sync(CaseScaffoldService.scaffold_from_chat)(
                    transcript=transcript,
                    user=request.user,
                    project_id=project_id,
                    thread_id=thread_id,
                    skill_context=scaffold_skill_context,
                )

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
            logger.exception("Scaffold failed for project %s", request.data.get('project_id'))
            return Response(
                {'error': 'Scaffolding failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ═══ Case Extraction Endpoints ══════════════════════════════════

    @action(detail=True, methods=['get'], url_path='extraction-status')
    def extraction_status(self, request, pk=None):
        """
        GET /api/cases/{case_id}/extraction-status/

        Returns current extraction pipeline status from case.metadata.
        Polled by frontend during extraction.

        Includes stale detection: if extraction has been in a running phase
        for >15 minutes, auto-marks it as failed (covers worker OOM/SIGKILL).
        """
        from datetime import datetime, timedelta
        from django.utils import timezone as tz

        case = self.get_object()
        metadata = case.metadata or {}

        extraction_status_val = metadata.get('extraction_status', 'none')
        running_phases = {'pending', 'retrieving', 'extracting', 'integrating', 'analyzing'}

        # Stale detection: if stuck in a running phase for >15 minutes,
        # the worker likely crashed. Auto-recover by marking as failed.
        if extraction_status_val in running_phases:
            started_at = metadata.get('extraction_started_at')
            if started_at:
                try:
                    started = datetime.fromisoformat(started_at)
                    if started.tzinfo is None:
                        started = started.replace(tzinfo=tz.utc)
                    stale_threshold = tz.now() - timedelta(minutes=15)
                    if started < stale_threshold:
                        logger.warning(
                            "Stale extraction detected for case %s "
                            "(started %s, status %s). Marking as failed.",
                            case.id, started_at, extraction_status_val,
                        )
                        metadata['extraction_status'] = 'failed'
                        metadata['extraction_error'] = (
                            'Extraction timed out (no progress for 15+ minutes). '
                            'The worker may have crashed. You can try re-extracting.'
                        )
                        case.metadata = metadata
                        case.save(update_fields=['metadata', 'updated_at'])
                        extraction_status_val = 'failed'
                except (ValueError, TypeError):
                    pass  # Malformed timestamp — skip stale check

        return Response({
            'extraction_status': extraction_status_val,
            'extraction_started_at': metadata.get('extraction_started_at'),
            'extraction_completed_at': metadata.get('extraction_completed_at'),
            'extraction_error': metadata.get('extraction_error'),
            'extraction_result': metadata.get('extraction_result'),
            'chunks_retrieved': metadata.get('chunks_retrieved', 0),
        })

    @action(detail=True, methods=['get'], url_path='analysis')
    def case_analysis(self, request, pk=None):
        """
        GET /api/cases/{case_id}/analysis/

        Returns CaseAnalysis results from case.metadata['analysis'].
        Available after extraction pipeline completes.
        """
        case = self.get_object()
        metadata = case.metadata or {}
        analysis = metadata.get('analysis')
        if not analysis:
            return Response(
                {'error': 'No analysis available. Extraction may still be in progress.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(analysis)

    @action(detail=True, methods=['post'], url_path='re-extract')
    def re_extract(self, request, pk=None):
        """
        POST /api/cases/{case_id}/re-extract/

        Re-runs the extraction pipeline with current chunks + any new documents.
        Useful when user adds documents to the project.
        """
        case = self.get_object()
        return self._schedule_extraction(case, incremental=False)

    @action(detail=True, methods=['post'], url_path='extract-additional')
    def extract_additional(self, request, pk=None):
        """
        POST /api/cases/{case_id}/extract-additional/

        Incremental extraction — expand chunk search and extract additional nodes.
        For when the user wants broader coverage.
        """
        case = self.get_object()
        return self._schedule_extraction(case, incremental=True)

    def _schedule_extraction(self, case, incremental: bool = False):
        """Shared helper: validate, clear stale data, and dispatch extraction."""
        if not case.decision_question:
            return Response(
                {'error': 'Case must have a decision question to run extraction.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_status = (case.metadata or {}).get('extraction_status', 'none')
        if current_status in ('retrieving', 'extracting', 'integrating', 'analyzing'):
            return Response(
                {'error': 'Extraction is already in progress.'},
                status=status.HTTP_409_CONFLICT,
            )

        from apps.cases.tasks import run_case_extraction_pipeline
        case.metadata = case.metadata or {}
        case.metadata['extraction_status'] = 'pending'
        # Clear stale data from previous runs
        case.metadata.pop('extraction_error', None)
        case.metadata.pop('extraction_result', None)
        case.metadata.pop('extraction_completed_at', None)
        case.metadata.pop('analysis', None)
        case.save(update_fields=['metadata'])
        run_case_extraction_pipeline.delay(str(case.id), incremental=incremental)

        return Response({'status': 'scheduled'}, status=status.HTTP_202_ACCEPTED)

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
            logger.exception("Export validation error for case %s", case.id)
            return Response(
                {'error': 'Invalid export parameters.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Export failed for case %s", case.id)
            return Response(
                {'error': 'Export failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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

    # ===== Decision Capture =====

    @action(detail=True, methods=['post'], url_path='record-decision')
    def record_decision(self, request, pk=None):
        """Record a formal decision / resolution for this case.

        Supports two flows:
        - **Legacy**: caller sends decision_text + key_reasons + confidence_level
          → routes to DecisionService.record_decision()
        - **New (auto-resolution)**: caller sends resolution_type (and optional
          overrides) → routes to ResolutionService.create_resolution()
        """
        from .serializers import RecordDecisionSerializer, DecisionRecordSerializer

        serializer = RecordDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Legacy detection: if caller explicitly provides all three required
        # fields from the old modal, use the legacy DecisionService path.
        is_legacy = (
            data.get('decision_text')
            and data.get('key_reasons')
            and data.get('confidence_level') is not None
        )

        try:
            if is_legacy:
                logger.info(
                    "legacy_decision_path_used",
                    extra={'case_id': str(pk), 'user_id': request.user.id},
                )
                from .decision_service import DecisionService
                record = DecisionService.record_decision(
                    user=request.user,
                    case_id=pk,
                    **data,
                )
            else:
                from .resolution_service import ResolutionService
                resolution_type = data.pop('resolution_type', 'resolved')
                # Everything else is an optional override
                overrides = {k: v for k, v in data.items() if v} or None
                record = ResolutionService.create_resolution(
                    user=request.user,
                    case_id=pk,
                    resolution_type=resolution_type,
                    overrides=overrides,
                )
        except ValueError as e:
            logger.warning("Failed to record decision for case %s: %s", pk, e)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(DecisionRecordSerializer(record).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='resolution-draft')
    def resolution_draft(self, request, pk=None):
        """Preview auto-generated resolution without creating anything.

        GET /api/cases/{id}/resolution-draft/?type=decision
        """
        from .resolution_service import ResolutionService

        self.get_object()  # ownership check
        resolution_type = request.query_params.get('type', 'resolved')

        try:
            draft = ResolutionService.generate_resolution_draft(
                case_id=pk,
                resolution_type=resolution_type,
            )
        except Exception:
            logger.exception("Resolution draft failed for case %s", pk)
            return Response(
                {'error': 'Could not generate resolution draft.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # confidence_level is internal only — don't expose to frontend
        draft.pop('confidence_level', None)
        return Response(draft)

    @action(detail=True, methods=['patch'], url_path='update-resolution')
    def update_resolution(self, request, pk=None):
        """Update editable fields on an existing resolution.

        PATCH /api/cases/{id}/update-resolution/
        Body: { decision_text?, key_reasons?, caveats?, outcome_check_date? }
        """
        from .serializers import UpdateResolutionSerializer, DecisionRecordSerializer
        from .models import DecisionRecord

        case = self.get_object()
        try:
            record = case.decision
        except DecisionRecord.DoesNotExist:
            return Response(
                {'error': 'No resolution recorded for this case'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdateResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        update_fields = []
        for field, value in serializer.validated_data.items():
            setattr(record, field, value)
            update_fields.append(field)

        if update_fields:
            update_fields.append('updated_at')
            record.save(update_fields=update_fields)

        return Response(DecisionRecordSerializer(record).data)

    @action(detail=True, methods=['get'], url_path='decision')
    def get_decision(self, request, pk=None):
        """Get the decision record for this case."""
        from .serializers import DecisionRecordSerializer
        from .models import DecisionRecord

        case = self.get_object()
        try:
            record = case.decision
        except DecisionRecord.DoesNotExist:
            return Response({'detail': 'No decision recorded'}, status=status.HTTP_404_NOT_FOUND)

        return Response(DecisionRecordSerializer(record).data)

    @action(detail=True, methods=['post'], url_path='outcome-note')
    def add_outcome_note(self, request, pk=None):
        """Add an outcome observation note."""
        from .serializers import OutcomeNoteSerializer, DecisionRecordSerializer
        from .decision_service import DecisionService
        from .models import DecisionRecord

        serializer = OutcomeNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            record = DecisionService.add_outcome_note(
                user=request.user,
                case_id=pk,
                **serializer.validated_data,
            )
        except DecisionRecord.DoesNotExist:
            return Response(
                {'error': 'No decision recorded for this case'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(DecisionRecordSerializer(record).data)

    # ═══ Position Update Proposals ══════════════════════════════════

    @action(detail=True, methods=['post'], url_path='accept-position-update')
    def accept_position_update(self, request, pk=None):
        """
        Accept a position update proposal from fact promotion.

        POST /api/cases/{id}/accept-position-update/
        Body: { "new_position": "...", "reason": "...", "message_id": "..." }

        Updates Case.position and InvestigationPlan.position_statement,
        then clears the proposal from the source message metadata.
        """
        case = self.get_object()
        new_position = request.data.get('new_position', '').strip()
        message_id = request.data.get('message_id')

        if not new_position:
            return Response(
                {'error': 'new_position is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update case position
        case.position = new_position
        case.save(update_fields=['position', 'updated_at'])

        # Also update plan position_statement if plan exists
        try:
            plan = case.plan
            plan.position_statement = new_position
            plan.save(update_fields=['position_statement', 'updated_at'])
        except InvestigationPlan.DoesNotExist:
            pass

        # Clear the proposal from the message metadata
        if message_id:
            from apps.chat.models import Message
            try:
                msg = Message.objects.get(id=message_id)
                msg_meta = msg.metadata or {}
                msg_meta.pop('position_update_proposal', None)
                msg.metadata = msg_meta
                msg.save(update_fields=['metadata'])
            except Message.DoesNotExist:
                pass

        return Response(CaseSerializer(case).data)

    @action(detail=True, methods=['post'], url_path='dismiss-position-update')
    def dismiss_position_update(self, request, pk=None):
        """
        Dismiss a position update proposal without applying it.

        POST /api/cases/{id}/dismiss-position-update/
        Body: { "message_id": "..." }

        Clears the proposal from the source message metadata.
        """
        self.get_object()  # ownership check
        message_id = request.data.get('message_id')

        if not message_id:
            return Response(
                {'error': 'message_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.chat.models import Message
        try:
            msg = Message.objects.get(id=message_id)
            msg_meta = msg.metadata or {}
            msg_meta.pop('position_update_proposal', None)
            msg.metadata = msg_meta
            msg.save(update_fields=['metadata'])
        except Message.DoesNotExist:
            pass

        return Response({'status': 'dismissed'})


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
                logger.exception("Permission denied updating document %s", document.id)
                return Response(
                    {'error': 'You do not have permission to edit this document.'},
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
