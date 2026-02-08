"""
Artifact serializers
"""
from rest_framework import serializers
from apps.artifacts.models import Artifact, ArtifactVersion


class ArtifactVersionSerializer(serializers.ModelSerializer):
    """Serializer for ArtifactVersion"""
    
    class Meta:
        model = ArtifactVersion
        fields = [
            'id',
            'artifact',
            'version',
            'blocks',
            'parent_version',
            'diff',
            'created_at',
            'created_by',
            'generation_time_ms',
        ]
        read_only_fields = fields


class ArtifactSerializer(serializers.ModelSerializer):
    """Serializer for Artifact"""
    
    current_version_blocks = serializers.SerializerMethodField()
    input_signal_count = serializers.SerializerMethodField()
    input_evidence_count = serializers.SerializerMethodField()

    class Meta:
        model = Artifact
        fields = [
            'id',
            'title',
            'type',
            'case',
            'user',
            'current_version',
            'current_version_blocks',
            'version_count',
            'input_signal_count',
            'input_evidence_count',
            'generated_by',
            'is_published',
            'published_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'current_version',
            'version_count',
            'generated_by',
            'created_at',
            'updated_at',
        ]

    def get_current_version_blocks(self, obj):
        """Get blocks from current version"""
        if obj.current_version:
            return obj.current_version.blocks
        return []

    def get_input_signal_count(self, obj):
        """Use prefetched data when available, else fallback to COUNT"""
        try:
            return len(obj.input_signals.all())
        except AttributeError:
            return 0

    def get_input_evidence_count(self, obj):
        """Use prefetched data when available, else fallback to COUNT"""
        try:
            return len(obj.input_evidence.all())
        except AttributeError:
            return 0


class CreateArtifactSerializer(serializers.Serializer):
    """Serializer for creating artifacts"""
    title = serializers.CharField(max_length=500)
    type = serializers.ChoiceField(choices=['research', 'critique', 'brief', 'deck'])
    case_id = serializers.UUIDField()


class EditBlockSerializer(serializers.Serializer):
    """Serializer for editing a specific block"""
    block_id = serializers.CharField()
    content = serializers.CharField()


class GenerateResearchSerializer(serializers.Serializer):
    """Serializer for research generation request"""
    case_id = serializers.UUIDField()
    topic = serializers.CharField()


class GenerateCritiqueSerializer(serializers.Serializer):
    """Serializer for critique generation request"""
    case_id = serializers.UUIDField()
    target_signal_id = serializers.UUIDField()


class GenerateBriefSerializer(serializers.Serializer):
    """Serializer for brief generation request"""
    case_id = serializers.UUIDField()
