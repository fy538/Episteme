"""
Project views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Project, Document, DocumentChunk
from .serializers import (
    ProjectSerializer,
    CreateProjectSerializer,
    DocumentSerializer,
    CreateDocumentSerializer,
    DocumentChunkSerializer,
)
from .services import ProjectService, DocumentService


class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for projects"""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateProjectSerializer
        return ProjectSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new project"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        project = ProjectService.create_project(
            user=request.user,
            title=serializer.validated_data['title'],
            description=serializer.validated_data.get('description', ''),
        )
        
        return Response(
            ProjectSerializer(project).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def refresh_stats(self, request, pk=None):
        """Refresh cached statistics for a project"""
        project = self.get_object()
        ProjectService.update_project_stats(project.id)
        
        return Response(ProjectSerializer(project).data)


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for documents"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentSerializer
    
    def get_queryset(self):
        # Users can only see their own documents
        queryset = Document.objects.filter(user=self.request.user)
        
        # Filter by project
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by case
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateDocumentSerializer
        return DocumentSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new document and trigger processing"""
        # Handle file upload if present
        file_obj = request.FILES.get('file')
        
        if file_obj:
            # File upload
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            document = DocumentService.create_document(
                user=request.user,
                project_id=serializer.validated_data['project_id'],
                title=serializer.validated_data['title'],
                source_type='upload',
                content_text='',
                file_url='',
                case_id=serializer.validated_data.get('case_id'),
            )
            
            # Save uploaded file
            document.file_path = file_obj
            document.file_type = file_obj.name.split('.')[-1] if '.' in file_obj.name else ''
            document.file_size = file_obj.size
            document.save()
        else:
            # Text or URL
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            document = DocumentService.create_document(
                user=request.user,
                project_id=serializer.validated_data['project_id'],
                title=serializer.validated_data['title'],
                source_type=serializer.validated_data['source_type'],
                content_text=serializer.validated_data.get('content_text', ''),
                file_url=serializer.validated_data.get('file_url', ''),
                case_id=serializer.validated_data.get('case_id'),
            )
        
        # Trigger new chunking/indexing workflow (async)
        from tasks.workflows import process_document_workflow
        process_document_workflow.delay(str(document.id))
        
        return Response(
            DocumentSerializer(document).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def chunks(self, request, pk=None):
        """
        Get all chunks for a document.
        
        GET /api/documents/{id}/chunks/
        """
        document = self.get_object()
        chunks = document.chunks.all().order_by('chunk_index')
        
        serializer = DocumentChunkSerializer(chunks, many=True)
        return Response({
            'document_id': str(document.id),
            'document_title': document.title,
            'total_chunks': chunks.count(),
            'chunks': serializer.data
        })
