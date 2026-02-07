"""
Artifact views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from apps.artifacts.models import Artifact, ArtifactVersion
from apps.artifacts.serializers import (
    ArtifactSerializer,
    ArtifactVersionSerializer,
    CreateArtifactSerializer,
    EditBlockSerializer,
    GenerateResearchSerializer,
    GenerateCritiqueSerializer,
    GenerateBriefSerializer,
)
from apps.artifacts.workflows import (
    generate_research_artifact_v2,
    generate_critique_artifact,
    generate_brief_artifact,
)


class ArtifactViewSet(viewsets.ModelViewSet):
    """ViewSet for artifacts"""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Artifact.objects.select_related('current_version', 'case')
        
        # Filter by case
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        
        # Filter by type
        artifact_type = self.request.query_params.get('type')
        if artifact_type:
            queryset = queryset.filter(type=artifact_type)
        
        # Only user's artifacts
        return queryset.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateArtifactSerializer
        return ArtifactSerializer
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        Get version history for artifact.
        
        GET /api/artifacts/{id}/versions/
        """
        artifact = self.get_object()
        versions = artifact.versions.order_by('-version')
        
        serializer = ArtifactVersionSerializer(versions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def edit_block(self, request, pk=None):
        """
        Edit a specific block (creates new version).
        
        PATCH /api/artifacts/{id}/edit_block/
        {
            "block_id": "uuid",
            "content": "new content"
        }
        """
        artifact = self.get_object()
        serializer = EditBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        block_id = serializer.validated_data['block_id']
        new_content = serializer.validated_data['content']
        
        # Get current blocks
        current_version = artifact.current_version
        if not current_version:
            return Response(
                {'error': 'No current version'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        blocks = current_version.blocks.copy()
        
        # Find and update block
        block_found = False
        old_content = None
        
        for block in blocks:
            if block.get('id') == block_id:
                old_content = block['content']
                block['content'] = new_content
                block_found = True
                break
        
        if not block_found:
            return Response(
                {'error': f'Block {block_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create new version
        with transaction.atomic():
            new_version = ArtifactVersion.objects.create(
                artifact=artifact,
                version=current_version.version + 1,
                blocks=blocks,
                parent_version=current_version,
                diff={
                    'modified_blocks': [{
                        'block_id': block_id,
                        'old_content': old_content,
                        'new_content': new_content,
                    }]
                },
                created_by=request.user,
            )
            
            artifact.current_version = new_version
            artifact.version_count += 1
            artifact.save()
        
        return Response(self.get_serializer(artifact).data)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Mark artifact as published.
        
        POST /api/artifacts/{id}/publish/
        """
        from django.utils import timezone
        
        artifact = self.get_object()
        artifact.is_published = True
        artifact.published_at = timezone.now()
        artifact.save()
        
        return Response(self.get_serializer(artifact).data)
    
    @action(detail=False, methods=['post'])
    def generate_research(self, request):
        """
        Generate research artifact.
        
        POST /api/artifacts/generate_research/
        {
            "case_id": "uuid",
            "topic": "Alternatives to PostgreSQL"
        }
        """
        serializer = GenerateResearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Trigger async generation via multi-step research loop
        import uuid
        correlation_id = str(uuid.uuid4())
        task = generate_research_artifact_v2.delay(
            case_id=str(serializer.validated_data['case_id']),
            topic=serializer.validated_data['topic'],
            user_id=request.user.id,
            correlation_id=correlation_id,
        )
        
        return Response(
            {'task_id': task.id, 'status': 'generating'},
            status=status.HTTP_202_ACCEPTED
        )
    
    @action(detail=False, methods=['post'])
    def generate_critique(self, request):
        """
        Generate critique artifact.
        
        POST /api/artifacts/generate_critique/
        {
            "case_id": "uuid",
            "target_signal_id": "uuid"
        }
        """
        serializer = GenerateCritiqueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        task = generate_critique_artifact.delay(
            case_id=str(serializer.validated_data['case_id']),
            target_signal_id=str(serializer.validated_data['target_signal_id']),
            user_id=request.user.id
        )
        
        return Response(
            {'task_id': task.id, 'status': 'generating'},
            status=status.HTTP_202_ACCEPTED
        )
    
    @action(detail=False, methods=['post'])
    def generate_brief(self, request):
        """
        Generate brief artifact.
        
        POST /api/artifacts/generate_brief/
        {
            "case_id": "uuid"
        }
        """
        serializer = GenerateBriefSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        task = generate_brief_artifact.delay(
            case_id=str(serializer.validated_data['case_id']),
            user_id=request.user.id
        )
        
        return Response(
            {'task_id': task.id, 'status': 'generating'},
            status=status.HTTP_202_ACCEPTED
        )
