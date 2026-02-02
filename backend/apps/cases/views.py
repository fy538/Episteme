"""
Case views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Case, WorkingView, CaseDocument
from .serializers import (
    CaseSerializer,
    WorkingViewSerializer,
    CreateCaseSerializer,
    UpdateCaseSerializer,
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
            except:
                # Fallback: append to end
                return {
                    "updated_content": f"{document.content_markdown}\n\n{content_to_add}\n\n[^chat]",
                    "insertion_section": "End of document",
                    "rewritten_content": content_to_add
                }
        
        result = asyncio.run(generate())
        return Response(result)
    
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
            signal_type='assumption'
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
{[f"- {s.content}" for s in assumption_signals[:5]]}

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
            except:
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
