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
