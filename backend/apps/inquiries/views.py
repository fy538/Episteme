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
