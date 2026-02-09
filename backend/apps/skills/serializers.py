"""
Serializers for Skill models
"""
from rest_framework import serializers
from .models import Skill


class SkillSerializer(serializers.ModelSerializer):
    """Serializer for Skill with full details"""
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    source_case_title = serializers.CharField(source='source_case.title', read_only=True, allow_null=True)

    class Meta:
        model = Skill
        fields = [
            'id',
            'organization',
            'organization_name',
            'owner',
            'owner_username',
            'name',
            'description',
            'domain',
            'skill_md_content',
            'applies_to_agents',
            'episteme_config',
            'status',
            'source_case',
            'source_case_title',
            'created_at',
            'updated_at',
            'created_by',
            'created_by_name',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SkillListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing skills"""
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    source_case_title = serializers.CharField(source='source_case.title', read_only=True, allow_null=True)

    class Meta:
        model = Skill
        fields = [
            'id',
            'organization_name',
            'owner_username',
            'name',
            'description',
            'domain',
            'applies_to_agents',
            'status',
            'source_case_title',
            'created_at',
            'updated_at',
            'created_by_name',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateSkillSerializer(serializers.ModelSerializer):
    """Serializer for creating a new skill with initial content"""

    class Meta:
        model = Skill
        fields = [
            'id',
            'organization',
            'owner',
            'name',
            'description',
            'domain',
            'skill_md_content',
            'applies_to_agents',
            'episteme_config',
            'status',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        # Set created_by and owner from context
        user = self.context['request'].user
        validated_data['created_by'] = user
        if 'owner' not in validated_data:
            validated_data['owner'] = user

        # Create skill
        skill = Skill.objects.create(**validated_data)
        return skill
