"""
Serializers for Skill models
"""
from rest_framework import serializers
from .models import Skill, SkillVersion


class SkillVersionSerializer(serializers.ModelSerializer):
    """Serializer for SkillVersion"""
    
    class Meta:
        model = SkillVersion
        fields = [
            'id',
            'version',
            'skill_md_content',
            'resources',
            'created_at',
            'created_by',
            'changelog'
        ]
        read_only_fields = ['id', 'created_at', 'created_by']


class SkillSerializer(serializers.ModelSerializer):
    """Serializer for Skill with current version content"""
    current_version_content = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    source_case_title = serializers.CharField(source='source_case.title', read_only=True, allow_null=True)
    forked_from_name = serializers.CharField(source='forked_from.name', read_only=True, allow_null=True)
    team_name = serializers.CharField(source='team.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Skill
        fields = [
            'id',
            'organization',
            'organization_name',
            'scope',
            'owner',
            'owner_username',
            'team',
            'team_name',
            'name',
            'description',
            'domain',
            'applies_to_agents',
            'episteme_config',
            'current_version',
            'status',
            'source_case',
            'source_case_title',
            'forked_from',
            'forked_from_name',
            'created_at',
            'updated_at',
            'created_by',
            'created_by_name',
            'current_version_content'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_version']
    
    def get_current_version_content(self, obj):
        """Get the content of the current version"""
        version = obj.versions.filter(version=obj.current_version).first()
        if version:
            return SkillVersionSerializer(version).data
        return None


class SkillListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing skills (without version content)"""
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    source_case_title = serializers.CharField(source='source_case.title', read_only=True, allow_null=True)
    
    class Meta:
        model = Skill
        fields = [
            'id',
            'organization_name',
            'scope',
            'owner_username',
            'name',
            'description',
            'domain',
            'applies_to_agents',
            'current_version',
            'status',
            'source_case_title',
            'created_at',
            'updated_at',
            'created_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateSkillSerializer(serializers.ModelSerializer):
    """Serializer for creating a new skill with initial content"""
    initial_skill_md = serializers.CharField(write_only=True, required=True)
    initial_resources = serializers.JSONField(write_only=True, required=False, default=dict)
    
    class Meta:
        model = Skill
        fields = [
            'id',
            'organization',
            'scope',
            'owner',
            'team',
            'name',
            'description',
            'domain',
            'applies_to_agents',
            'episteme_config',
            'status',
            'initial_skill_md',
            'initial_resources'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        initial_md = validated_data.pop('initial_skill_md')
        initial_resources = validated_data.pop('initial_resources', {})
        
        # Set created_by and owner from context
        user = self.context['request'].user
        validated_data['created_by'] = user
        if 'owner' not in validated_data:
            validated_data['owner'] = user
        
        # Create skill
        skill = Skill.objects.create(**validated_data)
        
        # Create initial version
        SkillVersion.objects.create(
            skill=skill,
            version=1,
            skill_md_content=initial_md,
            resources=initial_resources,
            created_by=user,
            changelog="Initial version"
        )
        
        return skill
