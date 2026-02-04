"""
Inquiry models - Elevated signals worthy of investigation (Phase 2)
"""
from django.db import models
from django.contrib.auth.models import User

from apps.common.models import TimestampedModel, UUIDModel


class InquiryStatus(models.TextChoices):
    """Lifecycle status of an inquiry"""
    OPEN = 'open', 'Open'
    INVESTIGATING = 'investigating', 'Investigating'
    RESOLVED = 'resolved', 'Resolved'
    ARCHIVED = 'archived', 'Archived'


class ElevationReason(models.TextChoices):
    """Why a signal was elevated to an inquiry"""
    REPETITION = 'repetition', 'Repeated Signal'
    CONFLICT = 'conflict', 'Conflicting Signals'
    BLOCKING = 'blocking', 'Blocks Decision'
    USER_CREATED = 'user_created', 'User Promoted'
    HIGH_STRENGTH = 'high_strength', 'High Signal Strength'


class Inquiry(UUIDModel, TimestampedModel):
    """
    Elevated signal worthy of investigation.
    
    An inquiry is created when:
    - A signal is repeated/reinforced multiple times
    - User manually promotes a signal
    - System detects blocking conflict or question
    - Signal strength exceeds threshold
    
    Inquiries are units of focused investigation within a case.
    They accumulate evidence, generate objections, and eventually resolve.
    """
    # Core content
    title = models.TextField(
        help_text="Question or claim being investigated (e.g., 'Is PostgreSQL faster for our write workload?')"
    )
    description = models.TextField(
        blank=True,
        help_text="Additional context about this inquiry"
    )
    
    # Event tracking for provenance
    created_from_event_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Event that created this inquiry (for provenance)"
    )
    
    # Origin tracking (for inline-created inquiries)
    origin_text = models.TextField(
        null=True,
        blank=True,
        help_text="Selected text from document that sparked this inquiry"
    )
    origin_document = models.ForeignKey(
        'cases.CaseDocument',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='spawned_inquiries',
        help_text="Document where the inquiry originated from"
    )
    text_span = models.JSONField(
        null=True,
        blank=True,
        help_text="Character range in origin document: {from, to, section}"
    )
    
    # Relationships
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='inquiries'
    )
    
    # Origin - what led to this inquiry
    # Note: related_name 'spawned_inquiries' is defined on Signal.inquiry FK
    # Additional origin signals can be linked via origin_signals M2M if needed
    
    # Why was this elevated?
    elevation_reason = models.CharField(
        max_length=50,
        choices=ElevationReason.choices,
        help_text="What triggered the creation of this inquiry"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=InquiryStatus.choices,
        default=InquiryStatus.OPEN
    )
    
    # Resolution (when inquiry is resolved)
    conclusion = models.TextField(
        blank=True,
        help_text="Final conclusion or answer to the inquiry"
    )
    conclusion_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence in conclusion 0.0-1.0"
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the inquiry was resolved"
    )
    
    # Priority (user can adjust)
    priority = models.IntegerField(
        default=0,
        help_text="Higher = more important. 0 = normal priority"
    )
    
    # Ordering within case
    sequence_index = models.IntegerField(
        help_text="Order inquiry was created in case (0, 1, 2...)"
    )
    
    # Inquiry brief (Phase 2A)
    brief = models.ForeignKey(
        'cases.CaseDocument',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='is_brief_for_inquiry',
        help_text="Inquiry-level brief document"
    )

    # Dependencies - inquiries that must be resolved before this one
    blocked_by = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='blocks',
        blank=True,
        help_text="Inquiries that must be resolved before this one can be resolved"
    )

    class Meta:
        verbose_name_plural = 'inquiries'
        ordering = ['-priority', 'sequence_index']
        indexes = [
            models.Index(fields=['case', 'status']),
            models.Index(fields=['case', 'priority', 'status']),
            models.Index(fields=['case', 'sequence_index']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Inquiry: {self.title[:80]}"
    
    def is_resolved(self):
        """Check if inquiry has been resolved"""
        return self.status == InquiryStatus.RESOLVED
    
    def is_active(self):
        """Check if inquiry is currently active (open or investigating)"""
        return self.status in [InquiryStatus.OPEN, InquiryStatus.INVESTIGATING]


class Evidence(UUIDModel, TimestampedModel):
    """
    Evidence supporting or contradicting an inquiry.
    
    Evidence can come from:
    - Documents (whole or specific chunks)
    - Experiments/tests
    - External data
    - User observations
    
    Documents are cited, not extracted - preserving full context.
    """
    inquiry = models.ForeignKey(
        Inquiry,
        on_delete=models.CASCADE,
        related_name='evidence_items'
    )
    
    # Evidence source type
    evidence_type = models.CharField(
        max_length=50,
        choices=[
            ('document_full', 'Whole Document'),
            ('document_chunks', 'Document Section'),
            ('experiment', 'Experiment/Test'),
            ('external_data', 'External Data'),
            ('user_observation', 'User Observation'),
        ]
    )
    
    # If from document
    source_document = models.ForeignKey(
        'projects.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evidence_uses'
    )
    
    source_chunks = models.ManyToManyField(
        'projects.DocumentChunk',
        related_name='evidence_uses',
        blank=True
    )
    
    # Evidence content
    evidence_text = models.TextField(
        help_text="User's interpretation or direct quote"
    )
    
    # How it relates to inquiry
    direction = models.CharField(
        max_length=20,
        choices=[
            ('supports', 'Supports'),
            ('contradicts', 'Contradicts'),
            ('neutral', 'Neutral/Context'),
        ]
    )
    
    # Strength and credibility
    strength = models.FloatField(
        default=0.5,
        help_text="How strong is this evidence (0.0-1.0)"
    )
    
    credibility = models.FloatField(
        default=0.5,
        help_text="How credible is the source (0.0-1.0)"
    )
    
    # User verification
    verified = models.BooleanField(
        default=False,
        help_text="User has verified this evidence"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="User's notes about this evidence"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_evidence'
    )
    
    class Meta:
        verbose_name_plural = 'evidence'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['inquiry', 'direction']),
            models.Index(fields=['source_document']),
            models.Index(fields=['created_by', '-created_at']),
        ]
    
    def __str__(self):
        preview = self.evidence_text[:50] if self.evidence_text else ''
        return f"{self.direction} evidence for {self.inquiry.title[:30]}: {preview}..."


class Objection(UUIDModel, TimestampedModel):
    """
    Challenge or alternative perspective on an inquiry.
    
    Objections can be:
    - System-generated (from analyzing reasoning)
    - User-created (manual challenges)
    - Document-sourced (findings that challenge assumptions)
    
    Purpose: Strengthen reasoning by surfacing challenges.
    """
    inquiry = models.ForeignKey(
        Inquiry,
        on_delete=models.CASCADE,
        related_name='objections'
    )
    
    # Objection content
    objection_text = models.TextField(
        help_text="The challenge or alternative perspective"
    )
    
    objection_type = models.CharField(
        max_length=50,
        choices=[
            ('alternative_perspective', 'Alternative Perspective'),
            ('challenge_assumption', 'Challenge Assumption'),
            ('counter_evidence', 'Counter Evidence'),
            ('scope_limitation', 'Scope Limitation'),
            ('missing_consideration', 'Missing Consideration'),
        ]
    )
    
    # Source of objection
    source = models.CharField(
        max_length=50,
        choices=[
            ('system', 'System Generated'),
            ('user', 'User Created'),
            ('document', 'From Document'),
        ]
    )
    
    # If from document
    source_document = models.ForeignKey(
        'projects.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='objection_sources'
    )
    
    source_chunks = models.ManyToManyField(
        'projects.DocumentChunk',
        related_name='objection_sources',
        blank=True
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('addressed', 'Addressed'),
            ('dismissed', 'Dismissed'),
        ],
        default='active'
    )
    
    addressed_how = models.TextField(
        blank=True,
        help_text="How this objection was resolved or addressed"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_objections'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['inquiry', 'status']),
            models.Index(fields=['source_document']),
            models.Index(fields=['created_by', '-created_at']),
        ]
    
    def __str__(self):
        preview = self.objection_text[:50] if self.objection_text else ''
        return f"{self.objection_type} for {self.inquiry.title[:30]}: {preview}..."
