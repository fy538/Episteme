"""
Evidence serializers
"""
from rest_framework import serializers
from apps.projects.models import Evidence


class EvidenceSerializer(serializers.ModelSerializer):
    """Serializer for Evidence model"""
    
    document_title = serializers.CharField(source='document.title', read_only=True)
    chunk_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Evidence
        fields = [
            'id',
            'text',
            'type',
            'chunk',
            'document',
            'document_title',
            'chunk_preview',
            'extraction_confidence',
            'user_credibility_rating',
            'embedding',
            'source_url',
            'source_title',
            'source_domain',
            'source_published_date',
            'retrieval_method',
            'extracted_at',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'chunk',
            'document',
            'extraction_confidence',
            'embedding',
            'source_url',
            'source_title',
            'source_domain',
            'source_published_date',
            'retrieval_method',
            'extracted_at',
            'created_at',
        ]
    
    def get_chunk_preview(self, obj):
        """Get preview of source chunk for context"""
        return {
            'chunk_index': obj.chunk.chunk_index,
            'text_preview': obj.chunk.chunk_text[:200] + '...' if len(obj.chunk.chunk_text) > 200 else obj.chunk.chunk_text,
            'token_count': obj.chunk.token_count,
            'span': obj.chunk.span,
        }


class RateEvidenceSerializer(serializers.Serializer):
    """Serializer for rating evidence credibility"""
    
    rating = serializers.IntegerField(min_value=1, max_value=5)
    
    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5 stars")
        return value
