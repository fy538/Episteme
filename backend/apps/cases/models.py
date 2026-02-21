"""
Case models - Durable work objects
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

from pgvector.django import VectorField

from apps.common.models import TimestampedModel, UUIDModel


class CaseStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    DECIDED = 'decided', 'Decided'
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
    SOURCE = 'source', 'Source Document'
    NOTES = 'notes', 'Notes'


class EditFriction(models.TextChoices):
    """Edit permission levels for documents"""
    LOW = 'low', 'Easy to edit'
    HIGH = 'high', 'Annotate only'
    READONLY = 'readonly', 'Read-only'


class CaseStage(models.TextChoices):
    """Investigation stage for a case's plan"""
    EXPLORING = 'exploring', 'Exploring'
    INVESTIGATING = 'investigating', 'Investigating'
    SYNTHESIZING = 'synthesizing', 'Synthesizing'
    READY = 'ready', 'Ready'


class ResolutionType(models.TextChoices):
    """How a case was resolved."""
    RESOLVED = 'resolved', 'Resolved'   # "I have an answer"
    CLOSED = 'closed', 'Closed'         # "Closing without resolving"


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

    # Premortem — "Imagine this decision failed. What's the most likely reason?"
    premortem_text = models.TextField(
        blank=True,
        help_text="User's premortem: imagined reason for future failure"
    )
    premortem_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the premortem was written"
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
        'WorkingDocument',
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
    
    # Active skills for this case (ordered via through model)
    active_skills = models.ManyToManyField(
        'skills.Skill',
        through='CaseActiveSkill',
        blank=True,
        related_name='active_in_cases',
        help_text="Skills activated for this case (ordered)"
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

    # Per-case intelligence configuration (Items 2)
    intelligence_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-case AI behavior config: {auto_validate, background_research, gap_detection}"
    )

    # Per-case investigation preferences (Item 3)
    investigation_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-case investigation prefs: {rigor, evidence_threshold, disable_locks}"
    )

    # Pre-computed embedding for semantic search (384-dim from sentence-transformers)
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        help_text="384-dim embedding from sentence-transformers"
    )

    # Flexible metadata store for extraction pipeline state, analysis results, etc.
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Flexible metadata: extraction status, analysis results, companion origin, etc."
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


class WorkingDocument(UUIDModel, TimestampedModel):
    """
    Documents within a case - flexible multi-document system.

    Supports multiple document types:
    - Briefs (user writes synthesis - low edit friction)
    - Research (AI generates - high edit friction, annotate only)
    - Sources (uploaded PDFs - read-only)
    - Notes (user freeform - low friction)

    Documents can cite each other via markdown links: [[doc-name#section]]
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='working_documents'
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
        help_text="Extracted structure - e.g. research has findings"
    )
    
    # If AI-generated
    generated_by_ai = models.BooleanField(
        default=False,
        help_text="Whether this document was AI-generated"
    )
    
    agent_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of agent that generated this (e.g. research)"
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
        related_name='created_working_documents'
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


class WorkingDocumentVersion(UUIDModel):
    """
    Version snapshot for WorkingDocument content.

    Created automatically before AI overwrites (suggestions, agentic tasks)
    and optionally on manual saves. Enables rollback and AI attribution.
    """
    document = models.ForeignKey(
        WorkingDocument,
        on_delete=models.CASCADE,
        related_name='versions'
    )

    version = models.IntegerField(
        help_text="Sequential version number"
    )

    content_markdown = models.TextField(
        help_text="Full document content at this version"
    )

    diff_summary = models.TextField(
        blank=True,
        help_text="Human-readable summary of what changed"
    )

    created_by = models.CharField(
        max_length=30,
        choices=[
            ('user', 'User'),
            ('ai_suggestion', 'AI Suggestion'),
            ('ai_task', 'AI Agentic Task'),
            ('auto_save', 'Auto-save'),
            ('restore', 'Restored from version'),
        ],
        help_text="Who/what created this version"
    )

    task_description = models.TextField(
        blank=True,
        help_text="If AI-generated, the task/prompt that triggered the edit"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']
        indexes = [
            models.Index(fields=['document', '-version']),
            models.Index(fields=['document', '-created_at']),
        ]
        unique_together = [['document', 'version']]

    def __str__(self):
        return f"v{self.version} of {self.document.title} ({self.created_by})"

    @classmethod
    def create_snapshot(cls, document, created_by, diff_summary='', task_description=''):
        """Create a version snapshot of the current document content."""
        from django.db import transaction

        with transaction.atomic():
            latest = (
                cls.objects.select_for_update()
                .filter(document=document)
                .order_by('-version')
                .first()
            )
            next_version = (latest.version + 1) if latest else 1

            return cls.objects.create(
                document=document,
                version=next_version,
                content_markdown=document.content_markdown,
                diff_summary=diff_summary,
                created_by=created_by,
                task_description=task_description,
            )


class InvestigationPlan(UUIDModel, TimestampedModel):
    """
    Living investigation roadmap for a case. One-to-one with Case.

    The plan holds the investigation stage and current version pointer.
    Actual plan content (phases, assumptions, criteria) lives in PlanVersion
    snapshots — every change creates a new immutable version.
    """
    case = models.OneToOneField(
        'Case',
        on_delete=models.CASCADE,
        related_name='plan'
    )

    stage = models.CharField(
        max_length=20,
        choices=CaseStage.choices,
        default=CaseStage.EXPLORING,
        help_text="Current investigation stage"
    )

    current_version = models.IntegerField(
        default=1,
        help_text="Latest accepted version number"
    )

    position_statement = models.TextField(
        blank=True,
        help_text="Current working thesis — evolves with evidence"
    )

    # Provenance
    created_from_event_id = models.UUIDField(
        null=True, blank=True,
        help_text="Event that triggered plan creation"
    )

    class Meta:
        indexes = [
            models.Index(fields=['case']),
        ]

    def __str__(self):
        return f"Plan for: {self.case.title} (v{self.current_version}, {self.stage})"


class PlanVersion(UUIDModel):
    """
    Immutable snapshot of a plan at a point in time.

    Content is a structured JSONField holding the full plan state:
    phases, assumptions, decision criteria. Each AI-proposed or
    user-confirmed change creates a new version.

    Follows the WorkingDocumentVersion pattern (create_snapshot classmethod).
    """
    plan = models.ForeignKey(
        InvestigationPlan,
        on_delete=models.CASCADE,
        related_name='versions'
    )

    version_number = models.IntegerField(
        help_text="Sequential version number"
    )

    # Full plan content as structured JSON
    content = models.JSONField(
        help_text="Full plan snapshot — phases, assumptions, decision_criteria"
    )
    # content schema:
    # {
    #   "phases": [{
    #     "id": "uuid-str", "title": str, "description": str,
    #     "order": int, "inquiry_ids": [str]
    #   }],
    #   "assumptions": [{
    #     "id": "uuid-str",           # Can be Signal ID (linked) or standalone UUID
    #     "signal_id": "uuid|null",   # Reference to Signal record (single source of truth)
    #     "text": str,
    #     "status": "untested|confirmed|challenged|refuted",
    #     "test_strategy": str, "evidence_summary": str,
    #     "risk_level": "low|medium|high"
    #   }],
    #   "decision_criteria": [{
    #     "id": "uuid-str", "text": str,
    #     "is_met": bool, "linked_inquiry_id": "uuid|null"
    #   }],
    #   "stage_rationale": str
    # }

    diff_summary = models.TextField(
        blank=True,
        help_text="Human-readable summary of what changed"
    )

    diff_data = models.JSONField(
        null=True, blank=True,
        help_text="Structured diff for UI rendering (added/removed/changed items)"
    )

    created_by = models.CharField(
        max_length=30,
        choices=[
            ('system', 'System (initial generation)'),
            ('ai_proposal', 'AI Proposal (accepted by user)'),
            ('user_request', 'User Request (via chat)'),
            ('critique', 'Critique Agent'),
            ('restore', 'Restored from previous version'),
        ],
        help_text="Who/what created this version"
    )

    created_from_event_id = models.UUIDField(
        null=True, blank=True,
        help_text="Event that triggered this version"
    )

    TRIGGER_TYPE_CHOICES = [
        ('initial', 'Initial generation'),
        ('user_edit', 'User manual edit'),
        ('chat_edit', 'Chat-based edit'),
        ('ai_proposal_accepted', 'AI proposal accepted'),
        ('extraction_complete', 'Extraction pipeline'),
        ('research_complete', 'Research complete'),
        ('document_added', 'Document added'),
        ('regeneration', 'Plan regeneration'),
        ('stage_change', 'Stage change'),
        ('restore', 'Version restore'),
    ]

    trigger_type = models.CharField(
        max_length=30,
        choices=TRIGGER_TYPE_CHOICES,
        default='initial',
        blank=True,
        help_text="What triggered this version creation"
    )

    generation_context = models.JSONField(
        default=dict, blank=True,
        help_text="Context that influenced this version: thread_id, message excerpt, research results, etc."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = [['plan', 'version_number']]
        indexes = [
            models.Index(fields=['plan', '-version_number']),
            models.Index(fields=['plan', '-created_at']),
        ]

    def __str__(self):
        return f"v{self.version_number} of plan for {self.plan.case.title} ({self.created_by})"

    @classmethod
    def create_snapshot(cls, plan, content, created_by, diff_summary='', diff_data=None,
                        trigger_type='initial', generation_context=None):
        """Create a new version snapshot. Mirrors WorkingDocumentVersion.create_snapshot."""
        from django.db import transaction

        with transaction.atomic():
            latest = (
                cls.objects.select_for_update()
                .filter(plan=plan)
                .order_by('-version_number')
                .first()
            )
            next_version = (latest.version_number + 1) if latest else 1

            version = cls.objects.create(
                plan=plan,
                version_number=next_version,
                content=content,
                created_by=created_by,
                diff_summary=diff_summary,
                diff_data=diff_data,
                trigger_type=trigger_type,
                generation_context=generation_context or {},
            )

        # Update the plan's current version pointer
        plan.current_version = next_version
        plan.save(update_fields=['current_version', 'updated_at'])

        return version


class DocumentCitation(UUIDModel, TimestampedModel):
    """
    Citation from one document to another.
    
    Created automatically by parsing markdown links: [[target-doc#section]]
    Enables bidirectional navigation and tracks document connections.
    """
    from_document = models.ForeignKey(
        WorkingDocument,
        on_delete=models.CASCADE,
        related_name='outgoing_citations'
    )

    to_document = models.ForeignKey(
        WorkingDocument,
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


class CaseActiveSkill(models.Model):
    """
    Through model for Case.active_skills with ordering and provenance.

    Enables:
    - Explicit skill ordering (lower order = higher priority)
    - Tracking which pack activated a skill
    - Activation timestamps
    """
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    skill = models.ForeignKey('skills.Skill', on_delete=models.CASCADE)
    order = models.IntegerField(
        default=0,
        help_text="Priority order (lower = higher priority)"
    )
    activated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'case_active_skills'
        unique_together = [['case', 'skill']]
        ordering = ['order']

    def __str__(self):
        return f"{self.case.title[:30]} <- {self.skill.name} (order={self.order})"


class DecisionRecord(UUIDModel, TimestampedModel):
    """
    Records the user's final decision for a case.

    Created when user transitions from investigating to decided.
    Tracks the decision rationale, confidence, and long-term outcomes.
    """
    case = models.OneToOneField(
        Case,
        on_delete=models.CASCADE,
        related_name='decision'
    )
    decision_text = models.TextField(
        help_text="What was decided — the actual decision statement"
    )
    key_reasons = models.JSONField(
        default=list,
        help_text="List of reason strings: why this decision was made"
    )
    confidence_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Decision confidence 0-100"
    )
    caveats = models.TextField(
        blank=True,
        help_text="Known risks, conditions, or things to watch for"
    )
    resolution_type = models.CharField(
        max_length=20,
        choices=ResolutionType.choices,
        default=ResolutionType.RESOLVED,
        help_text="How this case was resolved"
    )
    resolution_profile = models.TextField(
        blank=True,
        default='',
        help_text="LLM-generated narrative characterization of the resolution quality"
    )
    linked_assumption_ids = models.JSONField(
        default=list,
        help_text="UUIDs of assumptions the user marked as validated during decision"
    )
    decided_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the decision was formally recorded"
    )
    outcome_check_date = models.DateField(
        null=True,
        blank=True,
        help_text="When to check back on how the decision played out"
    )
    outcome_notes = models.JSONField(
        default=list,
        help_text="List of outcome observations: [{date, note, sentiment}]"
    )

    # Pre-computed embedding for semantic search (384-dim from sentence-transformers)
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        help_text="384-dim embedding from sentence-transformers"
    )

    # Flexible metadata: premortem comparison, analysis results, etc.
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Flexible metadata: premortem comparison, analysis results, etc."
    )

    class Meta:
        indexes = [
            models.Index(fields=['case']),
            models.Index(fields=['outcome_check_date']),
        ]

    def __str__(self):
        return f"Decision for: {self.case.title[:50]}"
