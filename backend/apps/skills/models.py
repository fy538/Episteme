"""
Skill models for organization-level agent customization

Following Anthropic's Agent Skills specification with Episteme-specific extensions.
"""
from django.db import models
from django.contrib.auth.models import User

from apps.common.models import UUIDModel, TimestampedModel


class Skill(UUIDModel, TimestampedModel):
    """Multi-level skill for agent customization (personal/team/org)"""
    
    # Multi-level ownership
    organization = models.ForeignKey(
        'common.Organization',
        on_delete=models.CASCADE,
        related_name='skills',
        null=True,  # Nullable for personal skills
        blank=True
    )
    
    scope = models.CharField(
        max_length=20,
        choices=[
            ('personal', 'Personal'),
            ('team', 'Team'),
            ('organization', 'Organization'),
            ('public', 'Public')
        ],
        default='personal',
        help_text="Visibility and permission scope"
    )
    
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_skills',
        help_text="Primary owner of this skill"
    )
    
    team = models.ForeignKey(
        'projects.Project',  # Use Project as team proxy for now
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_skills',
        help_text="Team this skill belongs to (for team-scoped skills)"
    )
    
    # Metadata (from Anthropic spec)
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=200)  # Used for selection
    domain = models.CharField(max_length=100, blank=True)  # e.g., "legal", "medical"
    
    # Episteme-specific config
    applies_to_agents = models.JSONField(default=list)  # ["research", "critique", "brief"]
    episteme_config = models.JSONField(default=dict)  # Custom extensions
    
    # Versioning
    current_version = models.IntegerField(default=1)
    
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
    
    forked_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='forks',
        help_text="Skill this was forked from"
    )
    
    # Collaborative features
    can_view = models.ManyToManyField(
        User,
        blank=True,
        related_name='viewable_skills',
        help_text="Users who can view this skill"
    )
    
    can_edit = models.ManyToManyField(
        User,
        blank=True,
        related_name='editable_skills',
        help_text="Users who can edit this skill"
    )
    
    # Created by (keeping for backward compatibility)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_skills'
    )
    
    class Meta:
        db_table = 'skills'
        unique_together = [['owner', 'name', 'scope']]  # Unique per owner+scope
        ordering = ['name']
        indexes = [
            models.Index(fields=['scope', 'status']),
            models.Index(fields=['owner', 'scope']),
            models.Index(fields=['organization', 'scope']),
        ]
    
    def __str__(self):
        if self.organization:
            return f"{self.name} ({self.organization.name})"
        return f"{self.name} ({self.owner.username})"


class SkillVersion(UUIDModel):
    """Version-controlled skill content"""
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='versions')
    version = models.IntegerField()
    
    # Content (Anthropic SKILL.md format)
    skill_md_content = models.TextField()  # Full SKILL.md with YAML frontmatter
    
    # Resources (additional files)
    resources = models.JSONField(default=dict)  # {filename: content}
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='skill_versions'
    )
    changelog = models.TextField(blank=True)
    
    class Meta:
        db_table = 'skill_versions'
        unique_together = [['skill', 'version']]
        ordering = ['-version']
    
    def __str__(self):
        return f"{self.skill.name} v{self.version}"
