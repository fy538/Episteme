"""
Skill models for organization-level agent customization

Simplified skill system - core Skill model without versioning or packs.
"""
from django.db import models
from django.contrib.auth.models import User

from apps.common.models import UUIDModel, TimestampedModel


class Skill(UUIDModel, TimestampedModel):
    """Skill for agent customization"""

    # Ownership
    organization = models.ForeignKey(
        'common.Organization',
        on_delete=models.CASCADE,
        related_name='skills',
        null=True,
        blank=True
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_skills',
        help_text="Primary owner of this skill"
    )

    # Metadata
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=200)
    domain = models.CharField(max_length=100, blank=True)

    # Skill content (inline - no separate version table)
    skill_md_content = models.TextField(
        blank=True,
        default='',
        help_text="Full SKILL.md content with YAML frontmatter"
    )

    # Episteme-specific config
    applies_to_agents = models.JSONField(default=list)  # ["research", "critique", "brief"]
    episteme_config = models.JSONField(default=dict)

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('archived', 'Archived')
        ],
        default='draft'
    )

    # Provenance
    source_case = models.ForeignKey(
        'cases.Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_skills',
        help_text="Case this skill was created from"
    )

    # Created by
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_skills'
    )

    class Meta:
        db_table = 'skills'
        unique_together = [['owner', 'name']]
        ordering = ['name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['owner']),
            models.Index(fields=['organization']),
        ]

    def __str__(self):
        if self.organization:
            return f"{self.name} ({self.organization.name})"
        return f"{self.name} ({self.owner.username})"
