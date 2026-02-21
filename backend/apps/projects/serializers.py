"""
Project serializers
"""
from django.db import models as db_models
from rest_framework import serializers
from .models import Project, Document, DocumentChunk


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model"""

    case_count_by_status = serializers.SerializerMethodField()
    has_hierarchy = serializers.SerializerMethodField()
    latest_activity = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'description',
            'user',
            'total_cases',
            'total_documents',
            'is_archived',
            'case_count_by_status',
            'has_hierarchy',
            'latest_activity',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'total_cases',
            'total_documents',
            'case_count_by_status',
            'has_hierarchy',
            'latest_activity',
            'created_at',
            'updated_at',
        ]

    def get_case_count_by_status(self, obj):
        """Count cases grouped by status."""
        # Use annotated values from queryset when available
        if hasattr(obj, '_active_case_count'):
            return {
                'active': obj._active_case_count,
                'draft': obj._draft_case_count,
                'archived': obj._archived_case_count,
            }
        # Fallback: per-object query
        from apps.cases.models import Case
        qs = Case.objects.filter(project=obj).values('status').annotate(
            count=db_models.Count('id')
        )
        result = {'active': 0, 'draft': 0, 'archived': 0}
        for row in qs:
            if row['status'] in result:
                result[row['status']] = row['count']
        return result

    def get_has_hierarchy(self, obj):
        """Whether project has a READY cluster hierarchy."""
        if hasattr(obj, '_has_hierarchy'):
            return obj._has_hierarchy
        from apps.graph.models import ClusterHierarchy, HierarchyStatus
        return ClusterHierarchy.objects.filter(
            project=obj, is_current=True, status=HierarchyStatus.READY
        ).exists()

    def get_latest_activity(self, obj):
        """Most recent update timestamp across project entities."""
        return obj.updated_at.isoformat() if obj.updated_at else None


class CreateProjectSerializer(serializers.Serializer):
    """Serializer for creating a project"""
    title = serializers.CharField(max_length=500)
    description = serializers.CharField(required=False, allow_blank=True, default="")


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    
    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'source_type',
            'file_path',
            'file_url',
            'content_text',
            'file_type',
            'file_size',
            'author',
            'published_date',
            'project',
            'case',
            'user',
            'processing_status',
            'extraction_status',
            'extraction_error',
            'processing_progress',
            'chunk_count',
            'indexed_at',
            'scope',
            'user_rating',
            'notes',
            'signals_extracted',  # Deprecated but kept for backward compat
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'processing_status',
            'extraction_status',
            'extraction_error',
            'processing_progress',
            'chunk_count',
            'indexed_at',
            'scope',
            'signals_extracted',
            'created_at',
            'updated_at',
        ]


class DocumentChunkSerializer(serializers.ModelSerializer):
    """Serializer for DocumentChunk model"""
    
    class Meta:
        model = DocumentChunk
        fields = [
            'id',
            'document',
            'chunk_index',
            'chunk_text',
            'token_count',
            'span',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CreateDocumentSerializer(serializers.Serializer):
    """Serializer for creating a document"""
    title = serializers.CharField(max_length=500)
    source_type = serializers.ChoiceField(choices=['upload', 'url', 'text'])
    content_text = serializers.CharField(required=False, allow_blank=True)
    file_url = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    project_id = serializers.UUIDField()
    case_id = serializers.UUIDField(required=False, allow_null=True)
