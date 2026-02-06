"""
Project serializers
"""
from rest_framework import serializers
from .models import Project, Document, DocumentChunk


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model"""
    
    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'description',
            'user',
            'total_signals',
            'total_cases',
            'total_documents',
            'top_themes',
            'is_archived',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'total_signals',
            'total_cases',
            'total_documents',
            'top_themes',
            'created_at',
            'updated_at',
        ]


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
            'chunk_count',
            'indexed_at',
            'user_rating',
            'notes',
            'signals_extracted',  # Deprecated but kept for backward compat
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'processing_status',
            'chunk_count',
            'indexed_at',
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
            'summary',
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
