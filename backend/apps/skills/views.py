"""
Views for Skill management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models

from .models import Skill
from .serializers import (
    SkillSerializer,
    SkillListSerializer,
    CreateSkillSerializer,
)
from .permissions import SkillPermission


class SkillViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for skills

    Endpoints:
    - GET /api/skills/ - List all accessible skills
    - POST /api/skills/ - Create new skill
    - GET /api/skills/{id}/ - Get skill details
    - PUT /api/skills/{id}/ - Update skill
    - DELETE /api/skills/{id}/ - Delete skill
    - POST /api/skills/suggest_for_case/ - Suggest skills for a case
    """
    permission_classes = [IsAuthenticated, SkillPermission]

    def get_queryset(self):
        """Filter skills based on ownership"""
        user = self.request.user

        qs = Skill.objects.filter(
            models.Q(owner=user) |  # Skills owned by user
            models.Q(organization__members=user)  # Org skills for user's org
        ).select_related(
            'organization', 'owner', 'created_by', 'source_case',
        ).distinct()
        return qs

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return SkillListSerializer
        elif self.action == 'create':
            return CreateSkillSerializer
        return SkillSerializer

    def perform_create(self, serializer):
        """Set created_by and owner when creating a skill"""
        serializer.save(
            owner=self.request.user,
            created_by=self.request.user,
        )

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

        # Use the same scoped queryset so users only see skills they have access to
        skills = self.get_queryset().filter(status='active')

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
