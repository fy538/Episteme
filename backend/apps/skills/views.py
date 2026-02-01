"""
Views for Skill management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import models

from .models import Skill, SkillVersion
from .serializers import (
    SkillSerializer,
    SkillListSerializer,
    SkillVersionSerializer,
    CreateSkillSerializer
)
from .parser import parse_skill_md, validate_skill_md
from .permissions import SkillPermission


class SkillViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for skills with multi-level access control
    
    Endpoints:
    - GET /api/skills/ - List all accessible skills
    - POST /api/skills/ - Create new skill
    - GET /api/skills/{id}/ - Get skill details with current version
    - PUT /api/skills/{id}/ - Update skill metadata
    - DELETE /api/skills/{id}/ - Delete skill
    - POST /api/skills/{id}/create_version/ - Create new version
    - POST /api/skills/suggest_for_case/ - Suggest skills for a case
    - POST /api/skills/{id}/spawn_case/ - Create case from skill
    - POST /api/skills/{id}/fork/ - Fork skill
    - POST /api/skills/{id}/promote/ - Promote skill to higher scope
    """
    permission_classes = [IsAuthenticated, SkillPermission]
    
    def get_queryset(self):
        """Filter skills based on scope and permissions"""
        user = self.request.user
        
        return Skill.objects.filter(
            models.Q(scope='public') |  # Public skills
            models.Q(owner=user) |  # Skills owned by user
            models.Q(can_view=user) |  # Skills user has view permission for
            models.Q(scope='organization', organization__isnull=False)  # Org skills (TODO: filter by user's org)
        ).distinct()
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return SkillListSerializer
        elif self.action == 'create':
            return CreateSkillSerializer
        return SkillSerializer
    
    def perform_create(self, serializer):
        """Set created_by when creating a skill"""
        # TODO: Set organization from user when org relationship exists
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """
        Create a new version of a skill
        
        Request body:
        {
            "skill_md_content": "...",
            "resources": {...},
            "changelog": "Description of changes"
        }
        """
        skill = self.get_object()
        skill_md = request.data.get('skill_md_content')
        
        if not skill_md:
            return Response(
                {'error': 'skill_md_content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate SKILL.md format
        is_valid, errors = validate_skill_md(skill_md)
        if not is_valid:
            return Response(
                {'error': 'Invalid SKILL.md format', 'details': errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse to update skill metadata
        parsed = parse_skill_md(skill_md)
        metadata = parsed['metadata']
        
        # Update skill metadata if provided in YAML
        if 'name' in metadata:
            skill.name = metadata['name']
        if 'description' in metadata:
            skill.description = metadata['description']
        if 'domain' in metadata:
            skill.domain = metadata.get('domain', '')
        if 'episteme' in metadata:
            episteme = metadata['episteme']
            if 'applies_to_agents' in episteme:
                skill.applies_to_agents = episteme['applies_to_agents']
            # Store full episteme config
            skill.episteme_config = episteme
        
        # Create new version
        new_version = SkillVersion.objects.create(
            skill=skill,
            version=skill.current_version + 1,
            skill_md_content=skill_md,
            resources=request.data.get('resources', {}),
            created_by=request.user,
            changelog=request.data.get('changelog', '')
        )
        
        # Update skill
        skill.current_version = new_version.version
        skill.save()
        
        return Response(
            SkillVersionSerializer(new_version).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        List all versions of a skill
        """
        skill = self.get_object()
        versions = skill.versions.all()
        serializer = SkillVersionSerializer(versions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def version_detail(self, request, pk=None):
        """
        Get a specific version of a skill
        
        Query params:
        - version: Version number (defaults to current_version)
        """
        skill = self.get_object()
        version_num = request.query_params.get('version', skill.current_version)
        
        try:
            version_num = int(version_num)
        except ValueError:
            return Response(
                {'error': 'version must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        version = get_object_or_404(
            SkillVersion,
            skill=skill,
            version=version_num
        )
        
        serializer = SkillVersionSerializer(version)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def suggest_for_case(self, request):
        """
        Suggest relevant skills based on case details
        
        Request body:
        {
            "title": "Case title",
            "position": "Case position/thesis"
        }
        
        Returns: List of suggested skills
        """
        case_title = request.data.get('title', '')
        case_position = request.data.get('position', '')
        
        # Simple keyword matching (can be enhanced with embeddings later)
        # TODO: Filter by organization when org relationship exists
        skills = Skill.objects.filter(status='active')
        
        suggested = []
        text = f"{case_title} {case_position}".lower()
        
        for skill in skills:
            # Match domain keywords
            if skill.domain:
                keywords = skill.domain.lower().split()
                if any(kw in text for kw in keywords):
                    suggested.append(skill)
                    continue
            
            # Match skill name
            if skill.name.lower() in text:
                suggested.append(skill)
        
        serializer = SkillListSerializer(suggested, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def spawn_case(self, request, pk=None):
        """
        Create a new case from this skill
        
        POST /api/skills/{id}/spawn_case/
        
        Request body:
        {
            "title": "New Decision",
            "position": "Initial position",
            "stakes": "medium",
            "project_id": "uuid"
        }
        
        Returns: Created case
        """
        from apps.skills.conversion import CaseSkillConverter
        from apps.cases.serializers import CaseSerializer
        
        skill = self.get_object()
        title = request.data.get('title')
        
        if not title:
            return Response(
                {'error': 'Case title is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Spawn case from skill
        case = CaseSkillConverter.skill_to_case(
            skill=skill,
            case_title=title,
            user=request.user,
            position=request.data.get('position', ''),
            stakes=request.data.get('stakes'),
            project_id=request.data.get('project_id')
        )
        
        return Response(
            CaseSerializer(case).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def fork(self, request, pk=None):
        """
        Fork this skill to create a personal copy
        
        POST /api/skills/{id}/fork/
        
        Request body:
        {
            "name": "My Customized Version",
            "scope": "personal"  # or "team"
        }
        
        Returns: Forked skill
        """
        from apps.skills.conversion import CaseSkillConverter
        
        original_skill = self.get_object()
        new_name = request.data.get('name', f"{original_skill.name} (Copy)")
        scope = request.data.get('scope', 'personal')
        
        try:
            forked_skill = CaseSkillConverter.fork_skill(
                original_skill=original_skill,
                new_name=new_name,
                user=request.user,
                scope=scope
            )
            
            return Response(
                SkillSerializer(forked_skill).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def promote(self, request, pk=None):
        """
        Promote skill to higher scope level
        
        POST /api/skills/{id}/promote/
        
        Request body:
        {
            "scope": "team"  # or "organization", "public"
        }
        
        Returns: Updated skill
        """
        from apps.skills.conversion import CaseSkillConverter
        
        skill = self.get_object()
        new_scope = request.data.get('scope')
        
        if not new_scope:
            return Response(
                {'error': 'Target scope is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            updated_skill = CaseSkillConverter.promote_skill(
                skill=skill,
                new_scope=new_scope,
                user=request.user
            )
            
            return Response(SkillSerializer(updated_skill).data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
