"""
Case models - Durable work objects
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.common.models import TimestampedModel, UUIDModel


class CaseStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    ARCHIVED = 'archived', 'Archived'


class StakesLevel(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'


class DocumentType(models.TextChoices):
    """Types of documents in a case"""
    CASE_BRIEF = 'case_brief', 'Case Brief'
    INQUIRY_BRIEF = 'inquiry_brief', 'Inquiry Brief'
    RESEARCH = 'research', 'Research Report'
    DEBATE = 'debate', 'AI Debate'
    CRITIQUE = 'critique', 'AI Critique'
    SOURCE = 'source', 'Source Document'
    NOTES = 'notes', 'Notes'


class EditFriction(models.TextChoices):
    """Edit permission levels for documents"""
    LOW = 'low', 'Easy to edit'
    HIGH = 'high', 'Annotate only'
    READONLY = 'readonly', 'Read-only'


class Case(UUIDModel, TimestampedModel):
    """
    A Case is the centered workspace for getting something right.

    It captures:
    - Decision frame (question, constraints, success criteria)
    - Current position
    - Assumptions, questions, constraints (via signals in Phase 1)
    - Stakes and confidence
    - Provenance (what events/threads created it)
    """
    title = models.CharField(max_length=500)
    status = models.CharField(
        max_length=20,
        choices=CaseStatus.choices,
        default=CaseStatus.DRAFT
    )
    stakes = models.CharField(
        max_length=20,
        choices=StakesLevel.choices,
        default=StakesLevel.MEDIUM
    )

    # Decision Frame fields
    decision_question = models.TextField(
        blank=True,
        help_text="Core question being decided (e.g., 'Should we acquire CompanyX?')"
    )
    constraints = models.JSONField(
        default=list,
        help_text="Constraints on the decision: [{type, description}]"
    )
    success_criteria = models.JSONField(
        default=list,
        help_text="Success criteria: [{criterion, measurable, target}]"
    )
    stakeholders = models.JSONField(
        default=list,
        help_text="Stakeholders: [{name, interest, influence}]"
    )

    # Core content
    position = models.TextField(help_text="Current position or thesis")

    # User-stated epistemic confidence
    user_confidence = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="User's self-assessed confidence (0-100)"
    )
    user_confidence_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user last updated their confidence"
    )
    what_would_change_mind = models.TextField(
        blank=True,
        help_text="User's answer to 'What would change your mind?'"
    )
    
    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cases')
    
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name='cases',
        help_text="Project this case belongs to (REQUIRED)"
    )
    
    # Main brief (Phase 2A)
    main_brief = models.ForeignKey(
        'CaseDocument',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='is_main_brief_for',
        help_text="Main case brief document"
    )
    
    # Provenance
    created_from_event_id = models.UUIDField(
        help_text="Event that triggered case creation"
    )
    
    # Active skills for this case
    active_skills = models.ManyToManyField(
        'skills.Skill',
        blank=True,
        related_name='active_in_cases',
        help_text="Skills activated for this case"
    )
    
    # Skill template functionality
    is_skill_template = models.BooleanField(
        default=False,
        help_text="Whether this case is being used as a skill template"
    )
    
    template_scope = models.CharField(
        max_length=20,
        choices=[
            ('personal', 'Personal'),
            ('team', 'Team'),
            ('organization', 'Organization')
        ],
        null=True,
        blank=True,
        help_text="Scope if this case is a skill template"
    )
    
    # Bidirectional skill relationships
    based_on_skill = models.ForeignKey(
        'skills.Skill',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='spawned_cases',
        help_text="Skill this case was created from"
    )
    
    became_skill = models.OneToOneField(
        'skills.Skill',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='originating_case',  # Changed to avoid clash
        help_text="Skill created from this case"
    )

    # Pre-computed embedding for semantic search (384-dim from sentence-transformers)
    embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="Pre-computed embedding vector for semantic search"
    )

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['project', '-updated_at']),
            models.Index(fields=['status', '-updated_at']),
        ]
    
    def __str__(self):
        return self.title


class WorkingView(UUIDModel):
    """
    Materialized snapshot of a case's current state (Phase 1)
    
    This is a denormalized view for fast rendering and "what changed" diffs.
    """
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='working_views')
    
    # Snapshot of the case state
    summary_json = models.JSONField(help_text="Materialized case state with signals")
    
    # Provenance
    based_on_event_id = models.UUIDField(
        help_text="Last event included in this snapshot"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['case', '-created_at']),
            models.Index(fields=['based_on_event_id']),
        ]
    
    def __str__(self):
        return f"WorkingView for {self.case.title} at {self.created_at}"


class CaseDocument(UUIDModel, TimestampedModel):
    """
    Documents within a case - flexible multi-document system.
    
    Supports multiple document types:
    - Briefs (user writes synthesis - low edit friction)
    - Research (AI generates - high edit friction, annotate only)
    - Debates (AI personas - high friction)
    - Critiques (AI challenges - high friction)
    - Sources (uploaded PDFs - read-only)
    - Notes (user freeform - low friction)
    
    Documents can cite each other via markdown links: [[doc-name#section]]
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='case_documents'
    )
    
    inquiry = models.ForeignKey(
        'inquiries.Inquiry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='inquiry_documents',
        help_text="If document is specific to an inquiry"
    )
    
    # Document identity
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices
    )
    
    title = models.CharField(max_length=500)
    
    # Content (markdown format)
    content_markdown = models.TextField(
        default='',
        help_text="Document content in markdown"
    )
    
    # Edit permissions (determined by document type)
    edit_friction = models.CharField(
        max_length=20,
        choices=EditFriction.choices,
        help_text="Edit permission level"
    )
    
    # Flexible AI structure (schema varies by document_type)
    ai_structure = models.JSONField(
        default=dict,
        help_text="Extracted structure - research has findings, debates have positions, etc."
    )
    
    # If AI-generated
    generated_by_ai = models.BooleanField(
        default=False,
        help_text="Whether this document was AI-generated"
    )
    
    agent_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of agent that generated this (research, debate, critique)"
    )
    
    generation_prompt = models.TextField(
        blank=True,
        help_text="Prompt used to generate this document"
    )
    
    # Contribution tracking
    times_cited = models.IntegerField(
        default=0,
        help_text="How many times this document is cited by others"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_case_documents'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['case', 'document_type']),
            models.Index(fields=['inquiry', 'document_type']),
            models.Index(fields=['case', '-created_at']),
            models.Index(fields=['created_by', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.document_type}: {self.title}"


class DocumentCitation(UUIDModel, TimestampedModel):
    """
    Citation from one document to another.
    
    Created automatically by parsing markdown links: [[target-doc#section]]
    Enables bidirectional navigation and tracks document connections.
    """
    from_document = models.ForeignKey(
        CaseDocument,
        on_delete=models.CASCADE,
        related_name='outgoing_citations'
    )
    
    to_document = models.ForeignKey(
        CaseDocument,
        on_delete=models.CASCADE,
        related_name='incoming_citations'
    )
    
    # Citation details
    citation_text = models.TextField(
        help_text="The [[link]] text as it appears in document"
    )
    
    line_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Line number in source document"
    )
    
    # What section was cited
    cited_section = models.CharField(
        max_length=200,
        blank=True,
        help_text="Section anchor (e.g., 'findings', 'conclusion')"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['from_document', '-created_at']),
            models.Index(fields=['to_document', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.from_document.title} → {self.to_document.title}"


class ReadinessChecklistItem(UUIDModel, TimestampedModel):
    """
    User-defined readiness criteria for a case.

    The user defines what "ready to decide" means for them.
    System provides defaults but user can customize.
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='readiness_checklist'
    )

    description = models.TextField(
        help_text="What needs to be true/done before deciding"
    )

    is_required = models.BooleanField(
        default=True,
        help_text="Whether this item must be complete to be 'ready'"
    )

    is_complete = models.BooleanField(
        default=False,
        help_text="User marks this complete when satisfied"
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this item was marked complete"
    )

    # Optional links to related items
    linked_inquiry = models.ForeignKey(
        'inquiries.Inquiry',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='readiness_items',
        help_text="Inquiry that validates this criterion"
    )

    linked_assumption_signal = models.ForeignKey(
        'signals.Signal',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='readiness_items',
        help_text="Assumption signal related to this criterion"
    )

    order = models.IntegerField(
        default=0,
        help_text="Display order"
    )

    # AI-generated context
    why_important = models.TextField(
        blank=True,
        help_text="AI explanation of why this item matters for the decision"
    )

    created_by_ai = models.BooleanField(
        default=False,
        help_text="Whether this item was AI-generated"
    )

    # Auto-completion tracking
    completion_note = models.TextField(
        blank=True,
        help_text="Note about how/why this was completed (especially for auto-completion)"
    )

    # Phase 2: Hierarchical structure
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        help_text="Parent item (for nested/dependent items)"
    )

    item_type = models.CharField(
        max_length=50,
        choices=[
            ('validation', 'Validate Assumption'),
            ('investigation', 'Complete Investigation'),
            ('analysis', 'Perform Analysis'),
            ('stakeholder', 'Stakeholder Input'),
            ('alternative', 'Evaluate Alternative'),
            ('criteria', 'Define Criteria'),
            ('custom', 'Custom'),
        ],
        default='custom',
        help_text="Type of readiness item"
    )

    # Phase 2: Blocking dependencies
    # Note: blocks relationship means "this item blocks other items from being completed"
    # Use item.blocks.all() to get items this blocks
    # Use item.blocked_by.all() to get items blocking this one
    blocks = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='blocked_by',
        blank=True,
        help_text="Items that cannot be completed until this one is done"
    )

    # Must be defined after all fields
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store original completion state for signal detection
        self._original_is_complete = self.is_complete if self.pk else False

    class Meta:
        ordering = ['parent__order', 'order', 'id']  # Parents first, then children
        indexes = [
            models.Index(fields=['case', 'order']),
            models.Index(fields=['case', 'parent']),
            models.Index(fields=['item_type']),
        ]

    def __str__(self):
        status = '✓' if self.is_complete else '○'
        return f"{status} {self.description[:50]}"


# Default checklist items for new cases
DEFAULT_READINESS_CHECKLIST = [
    {"description": "Decision question is clearly defined", "is_required": True},
    {"description": "I've considered at least one alternative", "is_required": True},
    {"description": "Key assumptions are identified", "is_required": True},
    {"description": "Critical assumptions are validated or risk accepted", "is_required": False},
    {"description": "I understand what would change my mind", "is_required": False},
]
