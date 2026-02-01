"""
Serializers for case documents and citations.
"""
from rest_framework import serializers
from apps.cases.models import CaseDocument, DocumentCitation


class CaseDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for CaseDocument model.
    
    Includes citation counts, edit permission checks, and assumption highlighting.
    """
    citation_count = serializers.SerializerMethodField()
    cites_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    inquiry_title = serializers.CharField(source='inquiry.title', read_only=True, allow_null=True)
    highlighted_assumptions = serializers.SerializerMethodField()
    
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
            'highlighted_assumptions',
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
    
    def get_highlighted_assumptions(self, obj):
        """
        Extract and enrich assumptions from ai_structure for highlighting.
        
        Returns assumptions with context about related inquiries and signals.
        """
        from apps.inquiries.models import Inquiry
        from apps.signals.models import Signal
        
        if not obj.ai_structure or 'assumptions' not in obj.ai_structure:
            return []
        
        assumptions = obj.ai_structure.get('assumptions', [])
        enriched = []
        
        for assumption_text in assumptions:
            # Check if there's a related inquiry
            related_inquiry = Inquiry.objects.filter(
                case=obj.case,
                title__icontains=assumption_text[:40]  # Match on first 40 chars
            ).first()
            
            # Count related signals
            related_signals_count = Signal.objects.filter(
                case=obj.case,
                text__icontains=assumption_text[:30]  # Match on first 30 chars
            ).count()
            
            enriched.append({
                'text': assumption_text,
                'has_inquiry': related_inquiry is not None,
                'inquiry_id': str(related_inquiry.id) if related_inquiry else None,
                'inquiry_title': related_inquiry.title if related_inquiry else None,
                'inquiry_status': related_inquiry.status if related_inquiry else None,
                'related_signals_count': related_signals_count,
                'validated': related_inquiry.status == 'RESOLVED' if related_inquiry else False
            })
        
        return enriched


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
