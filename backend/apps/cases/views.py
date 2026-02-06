"""
Case views
"""
import logging

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Case, WorkingView, CaseDocument, ReadinessChecklistItem, DEFAULT_READINESS_CHECKLIST
from .brief_models import BriefSection, BriefAnnotation
from .serializers import (
    CaseSerializer,
    WorkingViewSerializer,
    CreateCaseSerializer,
    UpdateCaseSerializer,
    ReadinessChecklistItemSerializer,
    CreateChecklistItemSerializer,
    UpdateChecklistItemSerializer,
    UserConfidenceSerializer,
)
from .brief_serializers import (
    BriefSectionSerializer,
    BriefSectionCreateSerializer,
    BriefSectionUpdateSerializer,
    BriefSectionReorderSerializer,
    BriefOverviewSerializer,
    BriefAnnotationSerializer,
)
from .document_serializers import (
    CaseDocumentSerializer,
    CaseDocumentListSerializer,
    CaseDocumentCreateSerializer,
    DocumentCitationSerializer,
)
from .services import CaseService
from .document_service import CaseDocumentService
from apps.chat.models import ChatThread
from apps.chat.serializers import ChatThreadSerializer, ChatThreadDetailSerializer


class CaseViewSet(viewsets.ModelViewSet):
    """ViewSet for cases"""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Case.objects.filter(user=self.request.user)
    
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

        # Record session receipt if created from a thread
        thread_id = serializer.validated_data.get('thread_id')
        if thread_id:
            try:
                from apps.companion.receipts import SessionReceiptService
                SessionReceiptService.record_case_created(
                    thread_id=thread_id,
                    case=case
                )
            except Exception as e:
                logger.warning(f"Failed to record case creation receipt: {e}")

        return Response(
            {
                'case': CaseSerializer(case).data,
                'main_brief': CaseDocumentSerializer(case_brief, context={'request': request}).data
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
    
    @action(detail=True, methods=['get'])
    def work(self, request, pk=None):
        """
        Get the working view for this case
        
        GET /api/cases/{id}/work/
        
        Returns the latest WorkingView snapshot
        """
        case = self.get_object()
        
        # Get or create working view
        working_view = CaseService.refresh_working_view(case.id)
        
        return Response(WorkingViewSerializer(working_view).data)
    
    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """
        Force refresh the working view for this case
        
        POST /api/cases/{id}/refresh/
        """
        case = self.get_object()
        
        # Force create new working view
        working_view = CaseService.refresh_working_view(case.id)
        
        return Response(
            WorkingViewSerializer(working_view).data,
            status=status.HTTP_201_CREATED
        )
    
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
        
        case = self.get_object()
        skill_ids = request.data.get('skill_ids', [])
        
        # TODO: Filter by organization when org relationship exists
        # For now, just validate that skills exist and are active
        skills = Skill.objects.filter(
            id__in=skill_ids,
            status='active'
        )
        
        # Set active skills for this case
        case.active_skills.set(skills)
        
        return Response({
            'case_id': str(case.id),
            'active_skills': SkillListSerializer(skills, many=True).data
        })
    
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
        case.save()
        
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
        from apps.skills.conversion import CaseSkillConverter
        from apps.skills.serializers import SkillSerializer
        
        case = self.get_object()
        skill_name = request.data.get('name')
        scope = request.data.get('scope', 'personal')
        custom_description = request.data.get('description')
        
        if not skill_name:
            return Response(
                {'error': 'Skill name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert case to skill
        skill = CaseSkillConverter.case_to_skill(
            case=case,
            skill_name=skill_name,
            scope=scope,
            user=request.user,
            custom_description=custom_description
        )
        
        return Response(
            {
                'skill': SkillSerializer(skill).data,
                'case': CaseSerializer(case).data
            },
            status=status.HTTP_201_CREATED
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
        from apps.signals.models import Signal
        from apps.inquiries.models import Inquiry, InquiryStatus

        case = self.get_object()

        # Count evidence mentions (no direction metadata available on Signal model)
        evidence_signals = Signal.objects.filter(case=case, type='EvidenceMention')
        total_evidence = evidence_signals.count()
        evidence = {
            'total': total_evidence,
            'supporting': 0,  # Direction not tracked on Signal model
            'contradicting': 0,
            'neutral': total_evidence,
        }

        # Count assumptions and their validation status
        assumption_signals = Signal.objects.filter(case=case, type='Assumption')
        total_assumptions = assumption_signals.count()

        # An assumption is validated if it has a linked inquiry that is resolved
        validated_assumptions = 0
        untested_list = []

        for assumption in assumption_signals:
            # Check if there's an inquiry investigating this assumption
            linked_inquiry = Inquiry.objects.filter(
                case=case,
                signals=assumption
            ).first()

            if linked_inquiry and linked_inquiry.status == InquiryStatus.RESOLVED:
                validated_assumptions += 1
            else:
                untested_list.append({
                    'id': str(assumption.id),
                    'text': assumption.text[:200] if assumption.text else '',
                    'inquiry_id': str(linked_inquiry.id) if linked_inquiry else None,
                })

        assumptions = {
            'total': total_assumptions,
            'validated': validated_assumptions,
            'untested': total_assumptions - validated_assumptions,
            'untested_list': untested_list[:10],  # Limit to 10
        }

        # Count inquiries by status
        inquiries = case.inquiries.exclude(status=InquiryStatus.ARCHIVED)
        inquiry_counts = {
            'total': inquiries.count(),
            'open': inquiries.filter(status=InquiryStatus.OPEN).count(),
            'investigating': inquiries.filter(status=InquiryStatus.INVESTIGATING).count(),
            'resolved': inquiries.filter(status=InquiryStatus.RESOLVED).count(),
        }

        # Find claims from the brief (metadata not available on Signal model)
        unlinked_claims = []
        if case.main_brief:
            claim_signals = Signal.objects.filter(
                case=case,
                type='Claim',
            )[:5]
            for claim in claim_signals:
                unlinked_claims.append({
                    'text': claim.text[:150] if claim.text else '',
                    'location': 'brief',
                })

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

    @action(detail=True, methods=['get', 'post'], url_path='readiness-checklist')
    def readiness_checklist(self, request, pk=None):
        """
        Get or create checklist items for this case.

        GET /api/cases/{id}/readiness-checklist/
        Returns list of checklist items.

        POST /api/cases/{id}/readiness-checklist/
        Creates a new checklist item.
        Body: {description, is_required?, linked_inquiry?, linked_assumption_signal?}
        """
        case = self.get_object()

        if request.method == 'GET':
            items = case.readiness_checklist.all()
            serializer = ReadinessChecklistItemSerializer(items, many=True)

            # Calculate progress
            total = items.count()
            completed = items.filter(is_complete=True).count()
            required = items.filter(is_required=True).count()
            required_completed = items.filter(is_required=True, is_complete=True).count()

            return Response({
                'items': serializer.data,
                'progress': {
                    'completed': completed,
                    'required': required,
                    'required_completed': required_completed,
                    'total': total,
                }
            })

        elif request.method == 'POST':
            serializer = CreateChecklistItemSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Get next order
            max_order = case.readiness_checklist.order_by('-order').values_list('order', flat=True).first() or 0

            item = ReadinessChecklistItem.objects.create(
                case=case,
                description=serializer.validated_data['description'],
                is_required=serializer.validated_data.get('is_required', True),
                linked_inquiry_id=serializer.validated_data.get('linked_inquiry'),
                linked_assumption_signal_id=serializer.validated_data.get('linked_assumption_signal'),
                order=max_order + 1,
            )

            return Response(
                ReadinessChecklistItemSerializer(item).data,
                status=status.HTTP_201_CREATED
            )

    @action(detail=True, methods=['patch', 'delete'], url_path=r'readiness-checklist/(?P<item_id>[^/.]+)')
    def readiness_checklist_item(self, request, pk=None, item_id=None):
        """
        Update or delete a specific checklist item.

        PATCH /api/cases/{id}/readiness-checklist/{item_id}/
        Body: {description?, is_required?, is_complete?, order?}

        DELETE /api/cases/{id}/readiness-checklist/{item_id}/
        """
        case = self.get_object()

        try:
            item = case.readiness_checklist.get(id=item_id)
        except ReadinessChecklistItem.DoesNotExist:
            return Response(
                {'error': 'Checklist item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.method == 'DELETE':
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH
        serializer = UpdateChecklistItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if 'description' in serializer.validated_data:
            item.description = serializer.validated_data['description']
        if 'is_required' in serializer.validated_data:
            item.is_required = serializer.validated_data['is_required']
        if 'order' in serializer.validated_data:
            item.order = serializer.validated_data['order']

        # Handle completion toggle
        if 'is_complete' in serializer.validated_data:
            was_complete = item.is_complete
            item.is_complete = serializer.validated_data['is_complete']

            if item.is_complete and not was_complete:
                item.completed_at = timezone.now()
            elif not item.is_complete:
                item.completed_at = None

        item.save()

        return Response(ReadinessChecklistItemSerializer(item).data)

    @action(detail=True, methods=['post'], url_path='readiness-checklist/init-defaults')
    def init_default_checklist(self, request, pk=None):
        """
        Initialize checklist with default items.

        POST /api/cases/{id}/readiness-checklist/init-defaults/

        Only creates items if checklist is empty.
        """
        case = self.get_object()

        if case.readiness_checklist.exists():
            return Response({
                'message': 'Checklist already has items',
                'items': ReadinessChecklistItemSerializer(
                    case.readiness_checklist.all(), many=True
                ).data
            })

        items = []
        for idx, item_data in enumerate(DEFAULT_READINESS_CHECKLIST):
            item = ReadinessChecklistItem.objects.create(
                case=case,
                description=item_data['description'],
                is_required=item_data['is_required'],
                order=idx,
            )
            items.append(item)

        return Response({
            'message': 'Default checklist initialized',
            'items': ReadinessChecklistItemSerializer(items, many=True).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='readiness-checklist/generate')
    def generate_checklist(self, request, pk=None):
        """
        Generate AI-powered checklist items for this case.

        POST /api/cases/{id}/readiness-checklist/generate/

        Analyzes case context (assumptions, inquiries, decision question)
        and creates smart checklist items. Does not replace existing items.
        """
        from apps.cases.checklist_service import generate_smart_checklist
        import asyncio

        case = self.get_object()

        # Generate items based on case context
        items_data = asyncio.run(generate_smart_checklist(case))

        # Create checklist items in two passes: parents first, then children

        created_items = []
        parent_map = {}  # description -> created parent item
        max_order = case.readiness_checklist.order_by('-order').values_list('order', flat=True).first() or -1

        # Debug: Log what we're receiving
        logger.info(f"View received {len(items_data)} items")
        for item in items_data:
            logger.debug(f"  - {item['description'][:40]}: parent_matched={item.get('parent_description_matched')}")

        # Pass 1: Create parent items (items with no parent_description_matched)
        for idx, item_data in enumerate(items_data):
            if not item_data.get('parent_description_matched'):
                item = ReadinessChecklistItem.objects.create(
                    case=case,
                    description=item_data['description'],
                    is_required=item_data.get('is_required', True),
                    why_important=item_data.get('why_important', ''),
                    linked_inquiry_id=item_data.get('linked_inquiry_id'),
                    item_type=item_data.get('item_type', 'custom'),
                    order=max_order + idx + 1,
                    created_by_ai=True,
                    parent=None,  # Explicitly no parent
                )
                created_items.append(item)
                parent_map[item_data['description']] = item

        # Pass 2: Create child items (items with parent_description_matched)
        child_order = len(created_items)
        for item_data in items_data:
            parent_desc = item_data.get('parent_description_matched')
            if parent_desc and parent_desc in parent_map:
                parent_item = parent_map[parent_desc]
                item = ReadinessChecklistItem.objects.create(
                    case=case,
                    description=item_data['description'],
                    is_required=item_data.get('is_required', True),
                    why_important=item_data.get('why_important', ''),
                    linked_inquiry_id=item_data.get('linked_inquiry_id'),
                    item_type=item_data.get('item_type', 'custom'),
                    order=max_order + child_order + 1,
                    created_by_ai=True,
                    parent=parent_item,
                )
                created_items.append(item)
                child_order += 1

        return Response({
            'message': f'Generated {len(created_items)} checklist items ({len(parent_map)} parents, {len(created_items) - len(parent_map)} children)',
            'items': ReadinessChecklistItemSerializer(created_items, many=True, context={'include_children': True}).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='suggest-inquiries')
    def suggest_inquiries(self, request, pk=None):
        """
        Get AI-suggested inquiries based on case context.

        POST /api/cases/{id}/suggest-inquiries/

        Returns: [{title, description, reason, priority}]
        """
        from apps.common.llm_providers import get_llm_provider
        from apps.intelligence.case_prompts import build_inquiry_suggestion_prompt
        import asyncio
        import json

        case = self.get_object()
        prompt = build_inquiry_suggestion_prompt(case)

        provider = get_llm_provider('fast')

        async def generate():
            full_response = ""
            async for chunk in provider.stream_chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You suggest inquiries to help make better decisions."
            ):
                full_response += chunk.content

            # Parse JSON response
            try:
                response_text = full_response.strip()
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()
                return json.loads(response_text)
            except Exception:
                return []

        suggestions = asyncio.run(generate())
        return Response(suggestions)

    @action(detail=True, methods=['post'], url_path='analyze-gaps')
    def analyze_gaps(self, request, pk=None):
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
        from apps.common.llm_providers import get_llm_provider
        from apps.intelligence.case_prompts import build_gap_analysis_prompt
        import asyncio
        import json

        case = self.get_object()
        prompt = build_gap_analysis_prompt(case)

        provider = get_llm_provider('fast')

        async def generate():
            full_response = ""
            async for chunk in provider.stream_chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You analyze decision cases to find gaps and blind spots."
            ):
                full_response += chunk.content

            # Parse JSON response
            try:
                response_text = full_response.strip()
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()
                return json.loads(response_text)
            except Exception:
                return {
                    'missing_perspectives': [],
                    'unvalidated_assumptions': [],
                    'contradictions': [],
                    'evidence_gaps': [],
                    'recommendations': []
                }

        analysis = asyncio.run(generate())

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
    def suggest_evidence_sources(self, request, pk=None):
        """
        Get AI-suggested evidence sources for an inquiry.

        POST /api/cases/{id}/suggest-evidence-sources/
        Body: {"inquiry_id": "uuid"}

        Returns: [{suggestion, source_type, why_helpful, how_to_find}]
        """
        from apps.common.llm_providers import get_llm_provider
        from apps.intelligence.case_prompts import build_evidence_suggestion_prompt
        from apps.inquiries.models import Inquiry
        import asyncio
        import json

        case = self.get_object()
        inquiry_id = request.data.get('inquiry_id')

        if not inquiry_id:
            return Response(
                {'error': 'inquiry_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            inquiry = Inquiry.objects.get(id=inquiry_id, case=case)
        except Inquiry.DoesNotExist:
            return Response(
                {'error': 'Inquiry not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        prompt = build_evidence_suggestion_prompt(case, inquiry)
        provider = get_llm_provider('fast')

        async def generate():
            full_response = ""
            async for chunk in provider.stream_chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You suggest evidence sources to help validate inquiries."
            ):
                full_response += chunk.content

            # Parse JSON response
            try:
                response_text = full_response.strip()
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()
                return json.loads(response_text)
            except Exception:
                return []

        suggestions = asyncio.run(generate())
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
            ).prefetch_related(
                'annotations', 'annotations__source_signals',
                'subsections', 'subsections__annotations',
                'inquiry'
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

            # Determine order
            if 'after_section_id' in data and data['after_section_id']:
                try:
                    after_section = BriefSection.objects.get(
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
                    pass

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
                    pass
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
                section.is_linked = section.tagged_signals.exists()

        section.save()
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
        section.save()

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

        section.inquiry = None
        section.is_linked = section.tagged_signals.exists()
        section.grounding_status = 'empty'
        section.grounding_data = {}
        section.save()

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
                        )
                    )
                finally:
                    loop.close()

            else:
                # Minimal scaffold
                title = request.data.get('title', 'New Case')
                decision_question = request.data.get('decision_question')

                result = CaseScaffoldService.scaffold_minimal(
                    title=title,
                    user=request.user,
                    project_id=project_id,
                    decision_question=decision_question,
                )

            # Serialize response
            case_data = CaseSerializer(result['case']).data
            brief_data = CaseDocumentSerializer(result['brief']).data
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


class WorkingViewViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for working views
    Working views are created via CaseService
    """
    serializer_class = WorkingViewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see working views for their own cases
        return WorkingView.objects.filter(case__user=self.request.user)


class CaseDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for case documents - briefs, research, debates, etc.
    
    Supports:
    - CRUD operations on documents
    - Citation management
    - Filtering by case, inquiry, type
    - Edit permission enforcement
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CaseDocumentListSerializer
        elif self.action == 'create':
            return CaseDocumentCreateSerializer
        return CaseDocumentSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        # Users can only see documents from their own cases
        queryset = CaseDocument.objects.filter(case__user=self.request.user)
        
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
                updated_doc = CaseDocumentService.update_document_content(
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
        
        outgoing = document.outgoing_citations.all()
        incoming = document.incoming_citations.all()
        
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
    def integrate_content(self, request, pk=None):
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
        from apps.common.llm_providers import get_llm_provider
        import asyncio
        
        document = self.get_object()
        content_to_add = request.data.get('content', '')
        hint = request.data.get('hint', 'general')
        message_id = request.data.get('message_id')
        
        if not content_to_add:
            return Response(
                {'error': 'Content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # AI prompt to find best integration point
        provider = get_llm_provider('fast')
        system_prompt = "You are an AI editor that helps integrate new information into structured documents."
        
        user_prompt = f"""
Current document:
{document.content_markdown}

New content to integrate:
"{content_to_add}"

Content type: {hint}

Instructions:
1. Analyze the document structure
2. Find the most appropriate section to add this content
3. Rewrite the content if needed to match document style and flow
4. Add a citation marker: [^chat] at the end
5. Return the FULL updated document with the new content integrated

Return JSON:
{{
    "updated_content": "full updated markdown",
    "insertion_section": "section name where content was added",
    "rewritten_content": "how the content was adapted"
}}
"""
        
        async def generate():
            full_response = ""
            async for chunk in provider.stream_chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt
            ):
                full_response += chunk.content
            
            # Parse JSON response
            import json
            try:
                return json.loads(full_response)
            except (json.JSONDecodeError, ValueError) as e:
                # Fallback: append to end
                logger.warning(f"Failed to parse document insertion response: {e}")
                return {
                    "updated_content": f"{document.content_markdown}\n\n{content_to_add}\n\n[^chat]",
                    "insertion_section": "End of document",
                    "rewritten_content": content_to_add
                }
        
        result = asyncio.run(generate())
        return Response(result)
    
    @action(detail=True, methods=['post'], url_path='generate-suggestions')
    def generate_suggestions(self, request, pk=None):
        """
        Generate AI suggestions for improving this document.

        POST /api/case-documents/{id}/generate-suggestions/

        Returns: [{
            id, section_id, suggestion_type, current_content,
            suggested_content, reason, linked_signal_id, confidence, status
        }]
        """
        from .suggestions import generate_brief_suggestions
        from apps.signals.models import Signal

        document = self.get_object()
        case = document.case

        # Build case context
        inquiries = list(case.inquiries.values('id', 'title', 'status', 'conclusion'))
        signals = list(Signal.objects.filter(case=case).values(
            'id', 'type', 'text'
        )[:20])

        # Get gaps if available (cached or generate)
        gaps = {}
        try:
            from apps.intelligence.case_prompts import build_gap_analysis_prompt
            from apps.common.llm_providers import get_llm_provider
            import asyncio
            import json

            prompt = build_gap_analysis_prompt(case)
            provider = get_llm_provider('fast')

            async def get_gaps():
                full_response = ""
                async for chunk in provider.stream_chat(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You analyze decision cases to find gaps."
                ):
                    full_response += chunk.content
                try:
                    response_text = full_response.strip()
                    if response_text.startswith("```"):
                        response_text = response_text.split("```")[1]
                        if response_text.startswith("json"):
                            response_text = response_text[4:]
                        response_text = response_text.strip()
                    return json.loads(response_text)
                except Exception:
                    return {}

            gaps = asyncio.run(get_gaps())
        except Exception:
            pass

        case_context = {
            'decision_question': case.decision_question,
            'inquiries': inquiries,
            'signals': signals,
            'gaps': gaps,
        }

        max_suggestions = request.data.get('max_suggestions', 5)
        suggestions = generate_brief_suggestions(
            brief_content=document.content_markdown,
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
        from .suggestions import apply_suggestion

        document = self.get_object()
        suggestion = request.data.get('suggestion')

        if not suggestion:
            return Response(
                {'error': 'suggestion is required'},
                status=status.HTTP_400_BAD_REQUEST
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
        from apps.signals.models import Signal

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
        signals = list(Signal.objects.filter(case=case).values(
            'id', 'type', 'text'
        )[:20])

        case_context = {
            'decision_question': case.decision_question,
            'inquiries': inquiries,
            'signals': signals,
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
        from apps.signals.models import Signal

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
        signals = list(Signal.objects.filter(case=case).values(
            'id', 'type', 'text'
        )[:20])

        case_context = {
            'decision_question': case.decision_question,
            'inquiries': inquiries,
            'signals': signals,
        }

        # Execute the task
        result = execute_agentic_task(
            task_description=task_description,
            document_content=document.content_markdown,
            case_context=case_context
        )

        return Response(result)

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

        document.content_markdown = final_content
        document.save(update_fields=['content_markdown', 'updated_at'])

        return Response({
            'success': True,
            'message': 'Task result applied successfully'
        })

    @action(detail=True, methods=['get'], url_path='evidence-links')
    def evidence_links(self, request, pk=None):
        """
        Extract claims and link them to available evidence.

        GET /api/case-documents/{id}/evidence-links/

        Returns claims with their evidence links and coverage metrics.
        """
        from .evidence_linker import extract_and_link_claims
        from apps.signals.models import Signal

        document = self.get_object()
        case = document.case

        # Get signals for this case
        signals = list(Signal.objects.filter(case=case).values(
            'id', 'type', 'text'
        ))

        # Get inquiries
        inquiries = list(case.inquiries.values('id', 'title', 'status'))

        # Extract and link claims
        result = extract_and_link_claims(
            document_content=document.content_markdown,
            signals=signals,
            inquiries=inquiries
        )

        return Response(result)

    @action(detail=True, methods=['post'], url_path='add-citations')
    def add_citations(self, request, pk=None):
        """
        Add inline citations to the document based on evidence links.

        POST /api/case-documents/{id}/add-citations/

        Automatically adds citation markers to substantiated claims
        and creates a sources section.
        """
        from .evidence_linker import extract_and_link_claims, create_inline_citations
        from apps.signals.models import Signal

        document = self.get_object()
        case = document.case

        # Get signals
        signals = list(Signal.objects.filter(case=case).values(
            'id', 'type', 'text'
        ))

        # Extract and link claims
        link_result = extract_and_link_claims(
            document_content=document.content_markdown,
            signals=signals
        )

        # Create inline citations
        cited_content = create_inline_citations(
            document_content=document.content_markdown,
            linked_claims=link_result.get('claims', [])
        )

        # Optionally save (controlled by request)
        save = request.data.get('save', False)
        if save:
            document.content_markdown = cited_content
            document.save(update_fields=['content_markdown', 'updated_at'])

        return Response({
            'cited_content': cited_content,
            'claims_cited': link_result.get('summary', {}).get('substantiated', 0),
            'saved': save
        })

    @action(detail=True, methods=['post'])
    def detect_assumptions(self, request, pk=None):
        """
        AI analyzes document to identify all assumptions.
        Cross-references with existing inquiries and assumption signals.
        
        POST /api/case-documents/{id}/detect_assumptions/
        Returns: [{
            text, status, risk_level, inquiry_id, validation_approach
        }]
        """
        from apps.common.llm_providers import get_llm_provider
        from apps.signals.models import Signal
        import asyncio
        import json
        
        document = self.get_object()
        case = document.case
        
        # Get existing context
        inquiries = list(case.inquiries.all())
        assumption_signals = list(Signal.objects.filter(
            case=case,
            type='Assumption'
        ))
        
        # AI prompt
        provider = get_llm_provider('fast')
        system_prompt = "You are an AI that identifies and analyzes assumptions in decision documents."
        
        user_prompt = f"""
Analyze this case brief and identify ALL assumptions (stated or implied):

Brief:
{document.content_markdown}

Existing inquiries being investigated:
{[f"- {i.title} (status: {i.status})" for i in inquiries]}

Previously extracted assumption signals:
{[f"- {s.text}" for s in assumption_signals[:5]]}

For each assumption, provide:
1. text: The exact assumption text (quote from document)
2. status: "untested" | "investigating" | "validated"
   - investigating if matching inquiry exists
   - validated if inquiry resolved
   - untested otherwise
3. risk_level: "low" | "medium" | "high" based on impact if assumption is wrong
4. inquiry_id: UUID if matching inquiry exists (match by similarity)
5. validation_approach: Brief suggestion for how to validate

Return JSON array:
[{{
    "text": "assumption text",
    "status": "untested",
    "risk_level": "high",
    "inquiry_id": null,
    "validation_approach": "Research market data"
}}]

Return ONLY the JSON array, no other text.
"""
        
        async def generate():
            full_response = ""
            async for chunk in provider.stream_chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt
            ):
                full_response += chunk.content
            
            try:
                # Parse JSON response
                assumptions = json.loads(full_response.strip())
                
                # Enhance with inquiry links
                for assumption in assumptions:
                    # Find matching inquiry by title similarity
                    assumption_text = assumption['text'].lower()
                    for inquiry in inquiries:
                        if (
                            assumption_text in inquiry.title.lower() or
                            inquiry.title.lower() in assumption_text
                        ):
                            assumption['inquiry_id'] = str(inquiry.id)
                            assumption['status'] = 'validated' if inquiry.status == 'resolved' else 'investigating'
                            break
                
                return assumptions
            except Exception as e:
                logger.warning(f"Failed to extract assumptions: {e}")
                return []
        
        assumptions = asyncio.run(generate())
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
            CaseDocumentSerializer(research_doc, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def generate_debate(self, request):
        """
        Generate AI debate document with multiple personas.
        
        POST /api/case-documents/generate_debate/
        {
            "inquiry_id": "uuid",
            "personas": [
                {"name": "Engineering Lead", "role": "Performance-focused"},
                {"name": "Finance Director", "role": "Cost-conscious"}
            ]
        }
        """
        from apps.agents.document_generator import AIDocumentGenerator
        from apps.inquiries.models import Inquiry
        
        inquiry_id = request.data.get('inquiry_id')
        personas = request.data.get('personas', [])
        
        if not inquiry_id:
            return Response(
                {'error': 'inquiry_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not personas or len(personas) < 2:
            return Response(
                {'error': 'At least 2 personas required for debate'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            inquiry = Inquiry.objects.get(id=inquiry_id, case__user=request.user)
        except Inquiry.DoesNotExist:
            return Response(
                {'error': 'Inquiry not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate debate
        generator = AIDocumentGenerator()
        debate_doc = generator.generate_debate_for_inquiry(
            inquiry=inquiry,
            personas=personas,
            user=request.user
        )
        
        return Response(
            CaseDocumentSerializer(debate_doc, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def generate_critique(self, request):
        """
        Generate AI critique document (devil's advocate).
        
        POST /api/case-documents/generate_critique/
        {
            "inquiry_id": "uuid"
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
        
        # Generate critique
        generator = AIDocumentGenerator()
        critique_doc = generator.generate_critique_for_inquiry(
            inquiry=inquiry,
            user=request.user
        )
        
        return Response(
            CaseDocumentSerializer(critique_doc, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
