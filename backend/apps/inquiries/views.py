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
