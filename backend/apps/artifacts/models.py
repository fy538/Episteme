"""
Artifact models - AI-generated and user-edited documents

Artifacts are structured, editable outputs (like Cursor for documents):
- Research reports
- Critiques/red-team analyses
- Decision briefs
- Presentation decks (future)

Key features:
- Block-based structure (editable)
- Version controlled (VersionRAG approach)
- Provenance tracked (cites signals + evidence)
- No signal extraction (artifacts are outputs, not inputs)
"""
from django.db import models
from django.contrib.auth.models import User

from apps.common.models import TimestampedModel, UUIDModel


class ArtifactType(models.TextChoices):
    """Types of artifacts"""
    RESEARCH = 'research', 'Research Report'
    CRITIQUE = 'critique', 'Critique/Red-team Analysis'
    BRIEF = 'brief', 'Decision Brief'
    DECK = 'deck', 'Presentation Deck'


class Artifact(UUIDModel, TimestampedModel):
    """
    AI-generated or user-edited document.
    
    Artifacts are block-based (like Notion/Cursor) and version-controlled.
    They CITE signals and evidence, they don't re-extract them.
    """
    # Basic info
    title = models.CharField(max_length=500)
    type = models.CharField(
        max_length=20,
        choices=ArtifactType.choices
    )
    
    # Relationships
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='artifacts'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='artifacts')
    
    # Versioning
    current_version = models.ForeignKey(
        'ArtifactVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    version_count = models.IntegerField(default=1)
    
    # Provenance (what led to this artifact)
    input_signals = models.ManyToManyField(
        'signals.Signal',
        blank=True,
        related_name='used_in_artifacts',
        help_text="Signals that informed this artifact"
    )
    
    input_evidence = models.ManyToManyField(
        'projects.Evidence',
        blank=True,
        related_name='used_in_artifacts',
        help_text="Evidence that informed this artifact"
    )
    
    # Skills used during generation
    skills_used = models.ManyToManyField(
        'skills.Skill',
        blank=True,
        related_name='used_in_artifacts',
        help_text="Skills that were active during artifact generation"
    )
    
    # Generation metadata
    generated_by = models.CharField(
        max_length=50,
        help_text="adk_research, adk_critique, adk_brief, or user"
    )
    
    generation_prompt = models.TextField(
        blank=True,
        help_text="Prompt used to generate this artifact"
    )
    
    # Status
    is_published = models.BooleanField(
        default=False,
        help_text="Whether artifact is finalized"
    )
    
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['case', '-updated_at']),
            models.Index(fields=['user', 'type']),
            models.Index(fields=['is_published', '-updated_at']),
        ]
    
    def __str__(self):
        return f"{self.get_type_display()}: {self.title}"


class ArtifactVersion(UUIDModel):
    """
    Version history for artifacts (VersionRAG approach).
    
    Each edit creates a new version with:
    - Complete block state
    - Diff from previous version
    - Timestamp and author
    """
    artifact = models.ForeignKey(
        Artifact,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    
    version = models.IntegerField(
        help_text="Version number (1, 2, 3...)"
    )
    
    # Block structure (editable JSON)
    blocks = models.JSONField(
        help_text="""
        Array of blocks:
        [
          {
            "id": "block_uuid",
            "type": "heading" | "paragraph" | "list" | "quote" | "citation",
            "content": "text content",
            "cites": ["signal_uuid", "evidence_uuid"],
            "metadata": {...}
          }
        ]
        """
    )
    
    # Version graph
    parent_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_versions'
    )
    
    # Diff from parent (VersionRAG)
    diff = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Diff from parent version:
        {
          "added_blocks": ["block_id", ...],
          "removed_blocks": ["block_id", ...],
          "modified_blocks": [
            {"block_id": "...", "old_content": "...", "new_content": "..."}
          ]
        }
        """
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Generation metadata (if AI-generated)
    generation_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Time to generate (ms)"
    )
    
    class Meta:
        ordering = ['-version']
        unique_together = [('artifact', 'version')]
        indexes = [
            models.Index(fields=['artifact', '-version']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.artifact.title} v{self.version}"
