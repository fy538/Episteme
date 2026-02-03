"""
Views for Inquiry endpoints
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.inquiries.models import Inquiry, InquiryStatus, Evidence, Objection
from apps.inquiries.serializers import (
    InquirySerializer,
    InquiryListSerializer,
    InquiryCreateSerializer,
    EvidenceSerializer,
    EvidenceCreateSerializer,
    ObjectionSerializer,
    ObjectionCreateSerializer,
)


class InquiryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing inquiries.
    
    Provides CRUD operations plus custom actions for:
    - Resolving inquiries
    - Changing priority
    - Filtering by status
    """
    queryset = Inquiry.objects.all()
    serializer_class = InquirySerializer
    
    def get_serializer_class(self):
        if self.action == 'list':
            return InquiryListSerializer
        elif self.action == 'create':
            return InquiryCreateSerializer
        return InquirySerializer
    
    def get_queryset(self):
        queryset = Inquiry.objects.all()
        
        # Filter by case
        case_id = self.request.query_params.get('case', None)
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter active only
        active_only = self.request.query_params.get('active', None)
        if active_only == 'true':
            queryset = queryset.filter(status__in=[InquiryStatus.OPEN, InquiryStatus.INVESTIGATING])
        
        return queryset.select_related('case').prefetch_related('related_signals')
    
    @action(detail=True, methods=['get'])
    def confidence_history(self, request, pk=None):
        """
        Get confidence evolution timeline for an inquiry.
        
        GET /api/inquiries/{id}/confidence-history/
        
        Returns array of confidence changes with timestamps and reasons.
        """
        from apps.companion.models import InquiryHistory
        from apps.companion.serializers import InquiryHistorySerializer
        
        inquiry = self.get_object()
        
        # Get confidence history ordered by time
        history = InquiryHistory.objects.filter(inquiry=inquiry).order_by('timestamp')
        
        serializer = InquiryHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """
        Resolve an inquiry with a conclusion.
        
        POST /inquiries/{id}/resolve/
        Body: {
            "conclusion": "PostgreSQL handles current load but not projected peak",
            "conclusion_confidence": 0.85
        }
        """
        inquiry = self.get_object()
        
        conclusion = request.data.get('conclusion')
        conclusion_confidence = request.data.get('conclusion_confidence')
        
        if not conclusion:
            return Response(
                {'error': 'Conclusion is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inquiry.conclusion = conclusion
        inquiry.conclusion_confidence = conclusion_confidence
        inquiry.status = InquiryStatus.RESOLVED
        inquiry.save()
        
        serializer = self.get_serializer(inquiry)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start_investigation(self, request, pk=None):
        """
        Mark inquiry as investigating and return guided workflow steps.
        
        POST /api/inquiries/{id}/start_investigation/
        
        Core experience improvement - provides clear path to investigate.
        """
        inquiry = self.get_object()
        
        if inquiry.status != InquiryStatus.OPEN:
            return Response(
                {'error': 'Only open inquiries can start investigation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status
        inquiry.status = InquiryStatus.INVESTIGATING
        inquiry.save()
        
        # Generate guided workflow steps
        workflow_steps = [
            {
                'step': 1,
                'action': 'review_inquiry',
                'title': 'Review inquiry question',
                'description': 'Ensure the question is clear and specific',
                'completed': True  # They're starting, so this is implicitly done
            },
            {
                'step': 2,
                'action': 'search_documents',
                'title': 'Search case documents for relevant evidence',
                'description': 'Look for information in uploaded documents',
                'endpoint': f'/api/projects/search/?case_id={inquiry.case_id}&query={inquiry.title}',
                'completed': False
            },
            {
                'step': 3,
                'action': 'add_evidence',
                'title': 'Add evidence from findings',
                'description': 'Cite specific sources that support or contradict',
                'endpoint': f'/api/evidence/?inquiry_id={inquiry.id}',
                'completed': False
            },
            {
                'step': 4,
                'action': 'consider_objections',
                'title': 'Consider alternative perspectives',
                'description': 'What objections or counterarguments exist?',
                'endpoint': f'/api/objections/?inquiry_id={inquiry.id}',
                'completed': False
            },
            {
                'step': 5,
                'action': 'resolve',
                'title': 'Write conclusion',
                'description': 'Synthesize evidence into a clear answer',
                'endpoint': f'/api/inquiries/{inquiry.id}/resolve/',
                'completed': False
            }
        ]
        
        return Response({
            'inquiry': self.get_serializer(inquiry).data,
            'workflow_steps': workflow_steps,
            'status': 'investigating'
        })
    
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """
        Reopen a resolved inquiry.
        
        POST /inquiries/{id}/reopen/
        """
        inquiry = self.get_object()
        
        if inquiry.status != InquiryStatus.RESOLVED:
            return Response(
                {'error': 'Only resolved inquiries can be reopened'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inquiry.status = InquiryStatus.OPEN
        inquiry.conclusion = ''
        inquiry.conclusion_confidence = None
        inquiry.resolved_at = None
        inquiry.save()
        
        serializer = self.get_serializer(inquiry)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_priority(self, request, pk=None):
        """
        Update inquiry priority.
        
        PATCH /inquiries/{id}/update_priority/
        Body: {"priority": 5}
        """
        inquiry = self.get_object()
        new_priority = request.data.get('priority')
        
        if new_priority is None:
            return Response(
                {'error': 'Priority is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inquiry.priority = int(new_priority)
        inquiry.save()
        
        serializer = self.get_serializer(inquiry)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def evidence_summary(self, request, pk=None):
        """
        Get aggregated evidence summary for inquiry.
        
        GET /api/inquiries/{id}/evidence_summary/
        
        Returns evidence grouped by direction with aggregate confidence.
        Core experience improvement - helps users know if they're ready to resolve.
        """
        from django.db.models import Avg
        
        inquiry = self.get_object()
        evidence = Evidence.objects.filter(inquiry=inquiry).select_related('document')
        
        # Group by direction
        supporting = evidence.filter(direction='SUPPORTS')
        contradicting = evidence.filter(direction='CONTRADICTS')
        neutral = evidence.filter(direction='NEUTRAL')
        
        # Calculate aggregate confidence
        total_count = evidence.count()
        
        if total_count > 0:
            support_ratio = supporting.count() / total_count
            contradict_ratio = contradicting.count() / total_count
            
            # Get average credibility from user ratings
            avg_credibility = evidence.aggregate(
                Avg('user_credibility_rating')
            )['user_credibility_rating__avg'] or 0.0
            
            # Aggregate confidence formula:
            # High if: many supporting, few contradicting, high credibility
            # Weight support positively, contradiction negatively
            aggregate_confidence = (
                (support_ratio - contradict_ratio * 0.5) * (avg_credibility / 5.0)
            )
            aggregate_confidence = max(0.0, min(1.0, aggregate_confidence))  # Clamp 0-1
            
        else:
            aggregate_confidence = 0.0
            avg_credibility = 0.0
        
        # Determine strength category
        if aggregate_confidence > 0.7:
            strength = 'strong'
        elif aggregate_confidence > 0.4:
            strength = 'moderate'
        else:
            strength = 'weak'
        
        # Check if ready to resolve
        ready_to_resolve = (
            aggregate_confidence > 0.6 and
            total_count >= 2 and
            avg_credibility >= 3.0
        )
        
        # Generate recommended conclusion if strong evidence
        recommended_conclusion = None
        if aggregate_confidence > 0.7 and total_count >= 3:
            if support_ratio > 0.7:
                recommended_conclusion = f"Evidence strongly supports investigating {inquiry.title}"
            elif contradict_ratio > 0.7:
                recommended_conclusion = f"Evidence suggests {inquiry.title} may not be the right approach"
        
        return Response({
            'supporting': EvidenceSerializer(supporting, many=True).data,
            'contradicting': EvidenceSerializer(contradicting, many=True).data,
            'neutral': EvidenceSerializer(neutral, many=True).data,
            'summary': {
                'total_evidence': total_count,
                'supporting_count': supporting.count(),
                'contradicting_count': contradicting.count(),
                'neutral_count': neutral.count(),
                'avg_credibility': round(avg_credibility, 2),
                'aggregate_confidence': round(aggregate_confidence, 2),
                'strength': strength,
                'ready_to_resolve': ready_to_resolve,
                'recommended_conclusion': recommended_conclusion
            }
        })
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get inquiry dashboard with status summary and next actions.
        
        GET /inquiries/dashboard/?case_id={id}
        
        Returns organized view of all inquiries for a case with actionable insights.
        """
        from django.db.models import Count, Q
        
        case_id = request.query_params.get('case_id')
        if not case_id:
            return Response(
                {'error': 'case_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all inquiries for the case
        inquiries = Inquiry.objects.filter(case_id=case_id).select_related('case')
        
        # Group by status
        by_status = {
            'open': InquiryListSerializer(
                inquiries.filter(status=InquiryStatus.OPEN).order_by('-priority', 'sequence_index'),
                many=True
            ).data,
            'investigating': InquiryListSerializer(
                inquiries.filter(status=InquiryStatus.INVESTIGATING).order_by('-priority', 'sequence_index'),
                many=True
            ).data,
            'resolved': InquiryListSerializer(
                inquiries.filter(status=InquiryStatus.RESOLVED).order_by('-resolved_at'),
                many=True
            ).data,
            'archived': InquiryListSerializer(
                inquiries.filter(status=InquiryStatus.ARCHIVED),
                many=True
            ).data
        }
        
        # Calculate summary stats
        total = inquiries.count()
        resolved = inquiries.filter(status=InquiryStatus.RESOLVED).count()
        completion_rate = (resolved / total * 100) if total > 0 else 0
        
        # Suggest next actions
        next_actions = []
        
        # Priority 1: Start investigating open inquiries
        open_inquiries = inquiries.filter(status=InquiryStatus.OPEN).order_by('-priority')
        if open_inquiries.exists():
            first_open = open_inquiries.first()
            next_actions.append({
                'type': 'start_investigation',
                'inquiry_id': str(first_open.id),
                'title': f'Start investigating: {first_open.title}',
                'priority': 1
            })
        
        # Priority 2: Resolve investigating inquiries with evidence
        investigating = inquiries.filter(status=InquiryStatus.INVESTIGATING)
        for inq in investigating:
            evidence_count = Evidence.objects.filter(inquiry=inq).count()
            if evidence_count >= 2:  # Has enough evidence
                next_actions.append({
                    'type': 'resolve_inquiry',
                    'inquiry_id': str(inq.id),
                    'title': f'Ready to resolve: {inq.title}',
                    'priority': 2
                })
        
        return Response({
            'by_status': by_status,
            'summary': {
                'total': total,
                'open': inquiries.filter(status=InquiryStatus.OPEN).count(),
                'investigating': inquiries.filter(status=InquiryStatus.INVESTIGATING).count(),
                'resolved': resolved,
                'completion_rate': round(completion_rate, 1)
            },
            'next_actions': next_actions[:5]  # Top 5 actions
        })
    
    @action(detail=False, methods=['post'])
    def generate_title(self, request):
        """
        Generate inquiry title from selected text using AI.
        
        POST /inquiries/generate_title/
        Body: {"text": "selected assumption text"}
        Returns: {"title": "AI-generated inquiry question"}
        """
        from apps.common.llm_providers import get_llm_provider
        import asyncio
        
        selected_text = request.data.get('text', '')
        if not selected_text:
            return Response(
                {'error': 'Text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # AI prompt to generate validation question
        provider = get_llm_provider('fast')
        system_prompt = "You are an AI that helps formulate research questions from assumptions."
        
        user_prompt = f"""
Given this statement or assumption from a decision brief:

"{selected_text}"

Generate a clear, focused research question to validate or investigate this assumption.

Guidelines:
- Start with "Will...", "Can...", "Is...", or "What..."
- Be specific and testable
- Focus on one question
- Keep under 100 characters

Return only the question, nothing else.
"""
        
        async def generate():
            full_response = ""
            async for chunk in provider.stream_chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt
            ):
                full_response += chunk.content
            return full_response.strip()
        
        title = asyncio.run(generate())
        
        return Response({'title': title})
    
    @action(detail=False, methods=['post'])
    def create_from_assumption(self, request):
        """
        Quick action to create inquiry from a highlighted assumption.
        
        POST /api/inquiries/create_from_assumption/
        
        Body:
        {
            "case_id": "uuid",
            "assumption_text": "Device is Class II",
            "auto_generate_title": true  # Optional: use AI to create title
        }
        
        Core experience improvement - one-click from assumption to inquiry.
        """
        from apps.inquiries.services import InquiryService
        from apps.cases.models import Case
        from apps.common.llm_providers import get_llm_provider
        import asyncio
        
        case_id = request.data.get('case_id')
        assumption_text = request.data.get('assumption_text')
        auto_generate = request.data.get('auto_generate_title', True)
        
        if not case_id or not assumption_text:
            return Response(
                {'error': 'case_id and assumption_text are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            case = Case.objects.get(id=case_id)
        except Case.DoesNotExist:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate title if requested
        if auto_generate:
            provider = get_llm_provider('fast')
            
            async def generate_title():
                prompt = f"""Convert this assumption into an investigation question:

Assumption: "{assumption_text}"

Generate a clear, specific question that would validate or invalidate this assumption.
Keep it under 100 characters. Return only the question.

Example:
Assumption: "Device is Class II"
Question: "What FDA classification applies to our device?"
"""
                full_response = ""
                async for chunk in provider.stream_chat(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You generate investigation questions from assumptions."
                ):
                    full_response += chunk.content
                return full_response.strip()
            
            title = asyncio.run(generate_title())
        else:
            # Use assumption text as title
            title = assumption_text if len(assumption_text) <= 100 else assumption_text[:97] + "..."
        
        # Create inquiry
        inquiry = InquiryService.create_inquiry(
            case=case,
            title=title,
            description=f"Validating assumption: {assumption_text}",
            user=request.user,
            elevation_reason='USER_CREATED',
            origin_text=assumption_text
        )
        
        return Response(
            self.get_serializer(inquiry).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def generate_brief_update(self, request, pk=None):
        """
        Generate AI suggestion for updating case brief based on inquiry resolution.
        
        POST /inquiries/{id}/generate_brief_update/
        Body: {"brief_id": "uuid"}
        Returns: {
            "updated_content": "full brief with updates",
            "changes": [{"type": "replace", "old": "...", "new": "..."}]
        }
        """
        from apps.common.llm_providers import get_llm_provider
        from apps.cases.models import CaseDocument
        import asyncio
        import json
        
        inquiry = self.get_object()
        brief_id = request.data.get('brief_id')
        
        if not brief_id:
            return Response(
                {'error': 'brief_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            brief = CaseDocument.objects.get(id=brief_id)
        except CaseDocument.DoesNotExist:
            return Response(
                {'error': 'Brief not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # AI prompt to generate updated brief
        provider = get_llm_provider('fast')
        system_prompt = "You are an AI editor that updates decision briefs based on research findings."
        
        user_prompt = f"""
Original case brief:
{brief.content_markdown}

Inquiry that was just resolved:
Question: {inquiry.title}
Conclusion: {inquiry.conclusion}
Confidence: {inquiry.conclusion_confidence or 'N/A'}

{f'Origin text in brief: "{inquiry.origin_text}"' if inquiry.origin_text else ''}

Task:
1. Update the brief to incorporate this inquiry conclusion
2. If origin_text exists, update or replace that assumption
3. If no origin_text, find the most relevant section to add this finding
4. Add citation: [[inquiry:{inquiry.id}]]
5. Maintain markdown formatting and document structure
6. Be concise - don't rewrite sections that don't need updating

Return JSON:
{{
    "updated_content": "full updated markdown brief",
    "changes": [
        {{"type": "replace", "old": "text that changed", "new": "updated text"}},
        {{"type": "add", "section": "section name", "content": "what was added"}}
    ],
    "summary": "brief summary of changes made"
}}
"""
        
        async def generate():
            full_response = ""
            async for chunk in provider.stream_chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt
            ):
                full_response += chunk.content
            
            try:
                return json.loads(full_response)
            except:
                # Fallback
                fallback_content = f"{brief.content_markdown}\n\n## Updated based on: {inquiry.title}\n\n{inquiry.conclusion}\n\n[[inquiry:{inquiry.id}]]"
                return {
                    "updated_content": fallback_content,
                    "changes": [{"type": "add", "section": "End", "content": inquiry.conclusion}],
                    "summary": "Added inquiry conclusion at end of document"
                }
        
        result = asyncio.run(generate())
        return Response(result)
    
    @action(detail=True, methods=['post'])
    async def generate_investigation_plan(self, request, pk=None):
        """
        Generate AI investigation plan for inquiry.
        
        POST /api/inquiries/{id}/generate_investigation_plan/
        Body: { brief_context: str }
        Returns: { plan_markdown: str }
        """
        from apps.common.llm_providers import get_llm_provider
        from asgiref.sync import sync_to_async
        
        inquiry = await sync_to_async(self.get_object)()
        brief_context = request.data.get('brief_context', '')
        
        # Get case for context
        case = await sync_to_async(lambda: inquiry.case)()
        
        provider = get_llm_provider('fast')
        system_prompt = "You create structured investigation plans for research questions."
        
        user_prompt = f"""Create an investigation plan for this research question:

Question: {inquiry.title}
{f'Context from brief: {brief_context}' if brief_context else ''}
{f'Case background: {case.position}' if case.position else ''}

Generate a structured investigation plan with these sections:

## Hypothesis
One clear sentence: What specific assumption or claim are we testing?

## Research Approaches
3-5 specific, actionable methods to investigate this question.
Be concrete - name actual activities (e.g., "Survey 20 target users", not "do user research")

## Evidence Needed
Bulleted list of specific evidence types that would confirm or refute the hypothesis

## Success Criteria
1-2 sentences: What constitutes "resolved"? What confidence level or evidence threshold do we need?

Return ONLY the markdown plan with these 4 sections. Be specific and actionable.
"""
        
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt
        ):
            full_response += chunk.content
        
        return Response({'plan_markdown': full_response.strip()})


class EvidenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing evidence for inquiries.
    
    Evidence can come from documents, experiments, or user observations.
    """
    queryset = Evidence.objects.all()
    serializer_class = EvidenceSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EvidenceCreateSerializer
        return EvidenceSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        queryset = Evidence.objects.all()
        
        # Filter by inquiry
        inquiry_id = self.request.query_params.get('inquiry')
        if inquiry_id:
            queryset = queryset.filter(inquiry_id=inquiry_id)
        
        # Filter by direction
        direction = self.request.query_params.get('direction')
        if direction:
            queryset = queryset.filter(direction=direction)
        
        # Filter by document
        document_id = self.request.query_params.get('document')
        if document_id:
            queryset = queryset.filter(source_document_id=document_id)
        
        return queryset.select_related('inquiry', 'source_document', 'created_by')
    
    @action(detail=False, methods=['post'])
    def cite_document(self, request):
        """
        Create evidence by citing a document or specific chunks.
        
        POST /api/evidence/cite_document/
        {
            "inquiry_id": "uuid",
            "document_id": "uuid",
            "chunk_ids": ["uuid1", "uuid2"],  // optional
            "evidence_text": "User's interpretation",
            "direction": "supports",
            "strength": 0.8
        }
        """
        inquiry_id = request.data.get('inquiry_id')
        document_id = request.data.get('document_id')
        chunk_ids = request.data.get('chunk_ids', [])
        
        if not inquiry_id or not document_id:
            return Response(
                {'error': 'inquiry_id and document_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Determine evidence type
        evidence_type = 'document_chunks' if chunk_ids else 'document_full'
        
        # Create evidence
        serializer = EvidenceCreateSerializer(
            data={
                'inquiry': inquiry_id,
                'evidence_type': evidence_type,
                'source_document': document_id,
                'chunk_ids': chunk_ids,
                'evidence_text': request.data.get('evidence_text', ''),
                'direction': request.data.get('direction', 'neutral'),
                'strength': request.data.get('strength', 0.5),
                'credibility': request.data.get('credibility', 0.5),
            },
            context={'request': request}
        )
        
        serializer.is_valid(raise_exception=True)
        evidence = serializer.save()
        
        return Response(
            EvidenceSerializer(evidence).data,
            status=status.HTTP_201_CREATED
        )


class ObjectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing objections to inquiries.
    
    Objections challenge reasoning and surface alternative perspectives.
    """
    queryset = Objection.objects.all()
    serializer_class = ObjectionSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ObjectionCreateSerializer
        return ObjectionSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        queryset = Objection.objects.all()
        
        # Filter by inquiry
        inquiry_id = self.request.query_params.get('inquiry')
        if inquiry_id:
            queryset = queryset.filter(inquiry_id=inquiry_id)
        
        # Filter by status
        obj_status = self.request.query_params.get('status')
        if obj_status:
            queryset = queryset.filter(status=obj_status)
        
        # Filter by source
        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(source=source)
        
        return queryset.select_related('inquiry', 'source_document', 'created_by')
    
    @action(detail=True, methods=['post'])
    def address(self, request, pk=None):
        """
        Mark an objection as addressed.
        
        POST /api/objections/{id}/address/
        Body: {"addressed_how": "Explanation of how this was resolved"}
        """
        objection = self.get_object()
        addressed_how = request.data.get('addressed_how')
        
        if not addressed_how:
            return Response(
                {'error': 'addressed_how is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        objection.status = 'addressed'
        objection.addressed_how = addressed_how
        objection.save()
        
        return Response(ObjectionSerializer(objection).data)
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """
        Dismiss an objection.
        
        POST /api/objections/{id}/dismiss/
        """
        objection = self.get_object()
        objection.status = 'dismissed'
        objection.save()
        
        return Response(ObjectionSerializer(objection).data)
