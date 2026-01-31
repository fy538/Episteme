"""
Serializers for case documents and citations.
"""
from rest_framework import serializers
from apps.cases.models import CaseDocument, DocumentCitation


class CaseDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for CaseDocument model.
    
    Includes citation counts and edit permission checks.
    """
    citation_count = serializers.SerializerMethodField()
    cites_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    inquiry_title = serializers.CharField(source='inquiry.title', read_only=True, allow_null=True)
    
    class Meta:
        model = CaseDocument
        fields = [
            'id',
            'case',
            'inquiry',
            'inquiry_title',
            'document_type',
            'title',
            'content_markdown',
            'edit_friction',
            'ai_structure',
            'generated_by_ai',
            'agent_type',
            'generation_prompt',
            'times_cited',
            'citation_count',
            'cites_count',
            'can_edit',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'times_cited',
            'citation_count',
            'cites_count',
            'can_edit',
            'created_at',
            'updated_at',
        ]
    
    def get_citation_count(self, obj):
        """Count of documents citing this document"""
        return obj.incoming_citations.count()
    
    def get_cites_count(self, obj):
        """Count of documents this document cites"""
        return obj.outgoing_citations.count()
    
    def get_can_edit(self, obj):
        """Check if current user can edit this document"""
        request = self.context.get('request')
        if not request or not request.user:
            return False
        
        # Low friction: anyone can edit
        if obj.edit_friction == 'low':
            return True
        
        # High friction or readonly: only creator (for high friction)
        if obj.edit_friction == 'high':
            return obj.created_by == request.user
        
        # Readonly: no one can edit
        return False


class CaseDocumentListSerializer(serializers.ModelSerializer):
    """Lighter serializer for listing documents"""
    
    inquiry_title = serializers.CharField(source='inquiry.title', read_only=True, allow_null=True)
    
    class Meta:
        model = CaseDocument
        fields = [
            'id',
            'title',
            'document_type',
            'inquiry',
            'inquiry_title',
            'times_cited',
            'generated_by_ai',
            'edit_friction',
            'created_at',
        ]


class CaseDocumentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating documents"""
    
    class Meta:
        model = CaseDocument
        fields = [
            'case',
            'inquiry',
            'document_type',
            'title',
            'content_markdown',
            'edit_friction',
        ]


class DocumentCitationSerializer(serializers.ModelSerializer):
    """Serializer for document citations"""
    
    from_title = serializers.CharField(source='from_document.title', read_only=True)
    to_title = serializers.CharField(source='to_document.title', read_only=True)
    from_type = serializers.CharField(source='from_document.document_type', read_only=True)
    to_type = serializers.CharField(source='to_document.document_type', read_only=True)
    
    class Meta:
        model = DocumentCitation
        fields = [
            'id',
            'from_document',
            'to_document',
            'from_title',
            'to_title',
            'from_type',
            'to_type',
            'citation_text',
            'cited_section',
            'line_number',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
