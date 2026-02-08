"""
Serializers for Inquiry models
"""
from rest_framework import serializers

from apps.inquiries.models import Inquiry, Evidence, Objection


class InquirySerializer(serializers.ModelSerializer):
    """Serializer for Inquiry model"""

    related_signals_count = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)
    is_resolved = serializers.BooleanField(read_only=True)
    blocked_by = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Inquiry.objects.all(),
        required=False
    )
    blocked_by_titles = serializers.SerializerMethodField()
    blocks = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Inquiry
        fields = [
            'id',
            'case',
            'title',
            'description',
            'elevation_reason',
            'status',
            'conclusion',
            'conclusion_confidence',
            'resolved_at',
            'priority',
            'sequence_index',
            'created_at',
            'updated_at',
            'related_signals_count',
            'is_active',
            'is_resolved',
            # Dependency fields
            'blocked_by',
            'blocked_by_titles',
            'blocks',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'sequence_index']

    def get_related_signals_count(self, obj):
        """Count of signals — uses prefetched cache when available"""
        try:
            return len(obj.related_signals.all())
        except AttributeError:
            return 0

    def get_blocked_by_titles(self, obj):
        """Get titles of blocking inquiries — uses prefetched cache"""
        return [
            {'id': str(i.id), 'title': i.title, 'status': i.status}
            for i in obj.blocked_by.all()
        ]


class InquiryListSerializer(serializers.ModelSerializer):
    """Lighter serializer for listing inquiries"""

    related_signals_count = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = [
            'id',
            'title',
            'status',
            'priority',
            'elevation_reason',
            'created_at',
            'resolved_at',
            'related_signals_count',
        ]

    def get_related_signals_count(self, obj):
        try:
            return len(obj.related_signals.all())
        except AttributeError:
            return 0


class InquiryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating inquiries"""
    
    class Meta:
        model = Inquiry
        fields = [
            'case',
            'title',
            'description',
            'elevation_reason',
            'priority',
        ]
    
    def create(self, validated_data):
        # Auto-assign sequence_index based on existing inquiries in case
        case = validated_data['case']
        last_inquiry = Inquiry.objects.filter(case=case).order_by('-sequence_index').first()
        validated_data['sequence_index'] = (last_inquiry.sequence_index + 1) if last_inquiry else 0
        
        return super().create(validated_data)


class EvidenceSerializer(serializers.ModelSerializer):
    """Serializer for Evidence model"""

    document_title = serializers.CharField(
        source='source_document.title', read_only=True, default=None,
    )
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Evidence
        fields = [
            'id',
            'inquiry',
            'evidence_type',
            'source_document',
            'document_title',
            'evidence_text',
            'direction',
            'strength',
            'credibility',
            'verified',
            'notes',
            'created_by',
            'created_at',
            'chunk_count',
        ]
        read_only_fields = ['id', 'created_at', 'created_by']

    def get_chunk_count(self, obj):
        """Count of chunks cited — uses prefetched cache when available"""
        try:
            return len(obj.source_chunks.all())
        except AttributeError:
            return 0


class EvidenceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating evidence"""
    
    chunk_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        help_text="List of chunk IDs to cite"
    )
    
    class Meta:
        model = Evidence
        fields = [
            'inquiry',
            'evidence_type',
            'source_document',
            'chunk_ids',
            'evidence_text',
            'direction',
            'strength',
            'credibility',
            'verified',
            'notes',
        ]
    
    def create(self, validated_data):
        chunk_ids = validated_data.pop('chunk_ids', [])

        # Add created_by from context
        validated_data['created_by'] = self.context['request'].user

        evidence = Evidence.objects.create(**validated_data)

        # Link chunks
        if chunk_ids:
            from apps.projects.models import DocumentChunk
            chunks = DocumentChunk.objects.filter(id__in=chunk_ids)
            evidence.source_chunks.set(chunks)

        # Emit provenance event
        from apps.events.services import EventService
        from apps.events.models import EventType, ActorType
        inquiry = evidence.inquiry
        EventService.append(
            event_type=EventType.EVIDENCE_ADDED,
            payload={
                'evidence_id': str(evidence.id),
                'inquiry_id': str(inquiry.id),
                'inquiry_title': inquiry.title,
                'direction': evidence.direction,
                'source_summary': (evidence.evidence_text or '')[:100],
            },
            actor_type=ActorType.USER,
            actor_id=self.context['request'].user.id,
            case_id=inquiry.case_id,
        )

        return evidence


class ObjectionSerializer(serializers.ModelSerializer):
    """Serializer for Objection model"""

    document_title = serializers.CharField(
        source='source_document.title', read_only=True, default=None,
    )
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Objection
        fields = [
            'id',
            'inquiry',
            'objection_text',
            'objection_type',
            'source',
            'source_document',
            'document_title',
            'status',
            'addressed_how',
            'created_by',
            'created_at',
            'chunk_count',
        ]
        read_only_fields = ['id', 'created_at', 'created_by']

    def get_chunk_count(self, obj):
        """Count of chunks cited — uses prefetched cache when available"""
        try:
            return len(obj.source_chunks.all())
        except AttributeError:
            return 0


class ObjectionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating objections"""
    
    chunk_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        help_text="List of chunk IDs supporting objection"
    )
    
    class Meta:
        model = Objection
        fields = [
            'inquiry',
            'objection_text',
            'objection_type',
            'source',
            'source_document',
            'chunk_ids',
            'status',
            'addressed_how',
        ]
    
    def create(self, validated_data):
        chunk_ids = validated_data.pop('chunk_ids', [])
        
        # Add created_by from context
        validated_data['created_by'] = self.context['request'].user
        
        objection = Objection.objects.create(**validated_data)
        
        # Link chunks
        if chunk_ids:
            from apps.projects.models import DocumentChunk
            chunks = DocumentChunk.objects.filter(id__in=chunk_ids)
            objection.source_chunks.set(chunks)
        
        return objection
