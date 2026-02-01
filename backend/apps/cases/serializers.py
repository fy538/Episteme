"""
Case serializers
"""
from rest_framework import serializers
from .models import Case, WorkingView, CaseStatus, StakesLevel


class CaseSerializer(serializers.ModelSerializer):
    """Serializer for Case model"""
    based_on_skill_name = serializers.CharField(
        source='based_on_skill.name',
        read_only=True,
        allow_null=True
    )
    became_skill_name = serializers.CharField(
        source='became_skill.name',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = Case
        fields = [
            'id',
            'title',
            'status',
            'stakes',
            'position',
            'confidence',
            'user',
            'linked_thread',
            'created_from_event_id',
            'created_at',
            'updated_at',
            # Skill template fields
            'is_skill_template',
            'template_scope',
            'based_on_skill',
            'based_on_skill_name',
            'became_skill',
            'became_skill_name',
        ]
        read_only_fields = ['id', 'created_from_event_id', 'created_at', 'updated_at']


class WorkingViewSerializer(serializers.ModelSerializer):
    """Serializer for WorkingView model"""
    
    class Meta:
        model = WorkingView
        fields = [
            'id',
            'case',
            'summary_json',
            'based_on_event_id',
            'created_at',
        ]
        read_only_fields = fields


class CreateCaseSerializer(serializers.Serializer):
    """Serializer for creating a new case"""
    
    title = serializers.CharField(max_length=500)
    position = serializers.CharField(required=False, allow_blank=True, default="")
    stakes = serializers.ChoiceField(
        choices=StakesLevel.choices,
        default=StakesLevel.MEDIUM
    )
    thread_id = serializers.UUIDField(required=False, allow_null=True)
    project_id = serializers.UUIDField(required=False, allow_null=True)  # Phase 2


class UpdateCaseSerializer(serializers.Serializer):
    """Serializer for updating a case"""
    
    title = serializers.CharField(max_length=500, required=False)
    position = serializers.CharField(required=False)
    stakes = serializers.ChoiceField(choices=StakesLevel.choices, required=False)
    confidence = serializers.FloatField(min_value=0.0, max_value=1.0, required=False, allow_null=True)
    status = serializers.ChoiceField(choices=CaseStatus.choices, required=False)
