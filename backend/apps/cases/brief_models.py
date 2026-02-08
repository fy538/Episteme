"""
Brief section and annotation models.

Provides a structured metadata overlay on top of CaseDocument markdown.
Sections link to markdown via <!-- section:ID --> markers and optionally
to Inquiries for grounding computation. Annotations are system-generated
observations about section quality (tensions, blind spots, evidence gaps).
"""
import uuid
from django.db import models

from apps.common.models import UUIDModel, TimestampedModel


class SectionType(models.TextChoices):
    DECISION_FRAME = 'decision_frame', 'Decision Frame'
    INQUIRY_BRIEF = 'inquiry_brief', 'Inquiry Brief'
    SYNTHESIS = 'synthesis', 'Synthesis'
    TRADE_OFFS = 'trade_offs', 'Trade-offs'
    RECOMMENDATION = 'recommendation', 'Recommendation'
    CUSTOM = 'custom', 'Custom'


class GroundingStatus(models.TextChoices):
    EMPTY = 'empty', 'No evidence yet'
    WEAK = 'weak', 'Under-evidenced'
    MODERATE = 'moderate', 'Some evidence'
    STRONG = 'strong', 'Well-grounded'
    CONFLICTED = 'conflicted', 'Has unresolved tensions'


class SectionCreator(models.TextChoices):
    SYSTEM = 'system', 'System scaffolded'
    USER = 'user', 'User created'
    AGENT = 'agent', 'Agent suggested'


class AnnotationType(models.TextChoices):
    TENSION = 'tension', 'Sources disagree'
    BLIND_SPOT = 'blind_spot', 'Missing analysis'
    UNGROUNDED = 'ungrounded', 'Unvalidated assumption'
    EVIDENCE_DESERT = 'evidence_desert', 'Needs more evidence'
    WELL_GROUNDED = 'well_grounded', 'Strong evidence'
    STALE = 'stale', 'Evidence may be outdated'
    CIRCULAR = 'circular', 'Circular reasoning detected'
    LOW_CREDIBILITY = 'low_credibility', 'Relies on low-credibility evidence'


class AnnotationPriority(models.TextChoices):
    BLOCKING = 'blocking', 'Blocking'
    IMPORTANT = 'important', 'Important'
    INFO = 'info', 'Informational'


class BriefSection(UUIDModel, TimestampedModel):
    """
    Metadata overlay for a section of the case brief.

    Links markdown sections (via <!-- section:ID --> markers) to
    inquiries and the knowledge graph. Enables grounding computation,
    annotations, and dynamic section management.

    Sections can be:
    - System-scaffolded (from CaseScaffoldService)
    - User-created (added manually)
    - Agent-suggested (proposed by AI)

    Linked sections (with inquiry FK or tagged_signals) get full
    intelligence overlay. Unlinked sections are pure prose.
    """
    # Link to the brief document
    brief = models.ForeignKey(
        'cases.CaseDocument',
        on_delete=models.CASCADE,
        related_name='brief_sections'
    )

    # Anchor to markdown — matches <!-- section:ID --> comment
    section_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Matches <!-- section:ID --> marker in markdown'
    )

    # Display
    heading = models.CharField(max_length=500)
    order = models.IntegerField(default=0)

    # Type classification
    section_type = models.CharField(
        max_length=50,
        choices=SectionType.choices,
        default=SectionType.CUSTOM
    )

    # Link to inquiry (for inquiry_brief sections)
    inquiry = models.ForeignKey(
        'inquiries.Inquiry',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='brief_sections',
        help_text='Links this section to an inquiry for grounding computation'
    )

    # Hierarchy — supports nesting (subsections)
    parent_section = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='subsections'
    )
    depth = models.IntegerField(
        default=0,
        help_text='0 = top-level, 1 = subsection, 2 = sub-sub'
    )

    # Ownership
    created_by = models.CharField(
        max_length=20,
        choices=SectionCreator.choices,
        default=SectionCreator.SYSTEM
    )

    # Linking state
    is_linked = models.BooleanField(
        default=False,
        help_text='True if linked to inquiry or has tagged signals'
    )

    # For custom sections: user/system can tag specific signals
    # for partial grounding without a full inquiry link
    tagged_signals = models.ManyToManyField(
        'signals.Signal',
        blank=True,
        related_name='tagged_in_sections'
    )

    # Computed grounding (cached, refreshed by evolve_scaffold)
    grounding_status = models.CharField(
        max_length=20,
        choices=GroundingStatus.choices,
        default=GroundingStatus.EMPTY
    )
    grounding_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Cached grounding metrics: evidence_count, tensions_count, etc.'
    )

    # Section state
    is_locked = models.BooleanField(
        default=False,
        help_text='Locked sections show lock_reason instead of edit controls'
    )
    lock_reason = models.CharField(
        max_length=200,
        blank=True,
        help_text='e.g. "Resolve 2 tensions to unlock"'
    )
    is_collapsed = models.BooleanField(
        default=False,
        help_text='User preference for collapsed/expanded state'
    )

    # Decomposed user judgment (Phase 4)
    # User rates their confidence in each section during synthesizing stage
    # 1=Low, 2=Some doubts, 3=Moderate, 4=High confidence
    user_confidence = models.IntegerField(
        null=True,
        blank=True,
        help_text="User's confidence in this section's conclusion (1-4)"
    )
    user_confidence_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user last rated this section"
    )

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['brief', 'order']),
            models.Index(fields=['brief', 'section_type']),
            models.Index(fields=['inquiry']),
        ]

    def __str__(self):
        return f'[{self.section_type}] {self.heading}'

    def save(self, *args, **kwargs):
        """Auto-compute is_linked and depth."""
        self.is_linked = bool(self.inquiry_id) or False  # M2M checked separately
        if self.parent_section:
            self.depth = self.parent_section.depth + 1
        super().save(*args, **kwargs)

    @staticmethod
    def generate_section_id() -> str:
        """Generate a unique section ID for markdown markers."""
        return f'sf-{uuid.uuid4().hex[:8]}'


class BriefAnnotation(UUIDModel, TimestampedModel):
    """
    Individual annotation on a brief section.

    System-generated observations about section quality:
    - Tensions (conflicting signals/evidence)
    - Blind spots (missing analysis)
    - Ungrounded assumptions (no evidence path)
    - Evidence deserts (insufficient evidence)
    - Well-grounded (strong evidence support)

    Annotations have a lifecycle: created → (dismissed | resolved)
    """
    section = models.ForeignKey(
        BriefSection,
        on_delete=models.CASCADE,
        related_name='annotations'
    )

    annotation_type = models.CharField(
        max_length=30,
        choices=AnnotationType.choices
    )

    description = models.TextField(
        help_text='Human-readable description of the annotation'
    )

    priority = models.CharField(
        max_length=20,
        choices=AnnotationPriority.choices,
        default=AnnotationPriority.IMPORTANT
    )

    # What triggered this annotation
    source_signals = models.ManyToManyField(
        'signals.Signal',
        blank=True,
        related_name='brief_annotations'
    )
    source_inquiry = models.ForeignKey(
        'inquiries.Inquiry',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='brief_annotations'
    )

    # Lifecycle
    dismissed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the user dismissed this annotation'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this annotation was resolved'
    )
    resolved_by = models.CharField(
        max_length=50,
        blank=True,
        help_text='user, system, or agent'
    )

    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['section', 'annotation_type']),
            models.Index(fields=['section', 'dismissed_at']),
        ]

    def __str__(self):
        return f'[{self.annotation_type}] {self.description[:80]}'

    @property
    def is_active(self) -> bool:
        """Annotation is active if not dismissed or resolved."""
        return self.dismissed_at is None and self.resolved_at is None
