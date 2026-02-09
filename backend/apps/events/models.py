"""
Event models - Append-only provenance and operational event store
"""
import uuid
from django.db import models
from django.contrib.auth.models import User


class ActorType(models.TextChoices):
    USER = 'user', 'User'
    ASSISTANT = 'assistant', 'Assistant'
    SYSTEM = 'system', 'System'


class EventCategory(models.TextChoices):
    PROVENANCE = 'provenance', 'Provenance (case history)'
    OPERATIONAL = 'operational', 'Operational (internal)'


class EventType(models.TextChoices):
    # ══ PROVENANCE ════════════════════════════════════════════════
    # Human-readable case history — shown in timeline UI.
    # Each event should be self-contained for display (no joins).

    # Case lifecycle
    CASE_CREATED = 'CaseCreated', 'Case Created'
    CASE_CREATED_FROM_ANALYSIS = 'CaseCreatedFromAnalysis', 'Case Created from Analysis'
    CASE_SCAFFOLDED = 'CaseScaffolded', 'Case Scaffolded from Chat'
    CASE_ARCHIVED = 'CaseArchived', 'Case Archived'

    # Inquiry lifecycle
    INQUIRY_CREATED = 'InquiryCreated', 'Inquiry Created'
    INQUIRY_RESOLVED = 'InquiryResolved', 'Inquiry Resolved'
    INQUIRY_REOPENED = 'InquiryReopened', 'Inquiry Reopened'
    INQUIRIES_AUTO_CREATED = 'InquiriesAutoCreated', 'Inquiries Auto-Created'

    # Knowledge building
    DOCUMENT_ADDED = 'DocumentAdded', 'Document Added'
    DOCUMENT_DELTA_ANALYZED = 'DocumentDeltaAnalyzed', 'Document Delta Analyzed'
    EVIDENCE_ADDED = 'EvidenceAdded', 'Evidence Added'

    # Graph mutations
    GRAPH_NODES_EXTRACTED = 'GraphNodesExtracted', 'Graph Nodes Extracted from Document'
    DOCUMENT_PROMOTED = 'DocumentPromoted', 'Document Promoted to Project Scope'
    DOCUMENT_DEMOTED = 'DocumentDemoted', 'Document Demoted to Case Scope'
    CASE_NODES_AUTO_PULLED = 'CaseNodesAutoPulled', 'Project Nodes Auto-Pulled into Case'
    CASE_NODE_PULLED = 'CaseNodePulled', 'Node Manually Pulled into Case'
    CASE_NODE_EXCLUDED = 'CaseNodeExcluded', 'Node Excluded from Case'

    # Synthesis
    BRIEF_EVOLVED = 'BriefEvolved', 'Brief Grounding Evolved'
    BRIEF_SECTION_WRITTEN = 'BriefSectionWritten', 'Brief Section Written'
    BRIEF_SECTION_REVISED = 'BriefSectionRevised', 'Brief Section Revised'
    STRUCTURE_ACCEPTED = 'StructureAccepted', 'Structure Accepted'
    STRUCTURE_DISMISSED = 'StructureDismissed', 'Structure Dismissed'

    # Research
    RESEARCH_COMPLETED = 'ResearchCompleted', 'Research Completed'

    # Evidence ingestion (universal pipeline)
    EVIDENCE_INGESTED = 'EvidenceIngested', 'Evidence Ingested (Universal Pipeline)'
    URL_FETCHED = 'UrlFetched', 'URL Content Fetched'

    # User decisions
    CONFIDENCE_CHANGED = 'ConfidenceChanged', 'Confidence Changed'
    POSITION_REVISED = 'PositionRevised', 'Position Revised'

    # Investigation plan lifecycle
    PLAN_CREATED = 'PlanCreated', 'Investigation Plan Created'
    PLAN_VERSION_CREATED = 'PlanVersionCreated', 'Plan Version Created'
    PLAN_STAGE_CHANGED = 'PlanStageChanged', 'Plan Stage Changed'

    # ══ OPERATIONAL ═══════════════════════════════════════════════
    # Internal system state — not shown in timeline UI.
    # Used for agent coordination, debugging, and resumability.

    # Chat message tracking (redundant with Message model, deprecated)
    USER_MESSAGE_CREATED = 'UserMessageCreated', 'User Message Created'
    ASSISTANT_MESSAGE_CREATED = 'AssistantMessageCreated', 'Assistant Message Created'

    # Case metadata changes (too granular for provenance)
    CASE_PATCHED = 'CasePatched', 'Case Patched'
    CASE_LINKED_TO_THREAD = 'CaseLinkedToThread', 'Case Linked to Thread'

    # Agent execution
    AGENT_WORKFLOW_STARTED = 'AgentWorkflowStarted', 'Agent Workflow Started'
    AGENT_PROGRESS = 'AgentProgress', 'Agent Progress Update'
    AGENT_COMPLETED = 'AgentCompleted', 'Agent Workflow Completed'
    AGENT_FAILED = 'AgentFailed', 'Agent Workflow Failed'
    AGENT_CHECKPOINT = 'AgentCheckpoint', 'Agent Loop Checkpoint'
    AGENT_TRAJECTORY = 'AgentTrajectory', 'Agent Decision Trajectory'

    # Workflow coordination
    WORKFLOW_STARTED = 'WorkflowStarted', 'Workflow Started'
    WORKFLOW_COMPLETED = 'WorkflowCompleted', 'Workflow Completed'

    # Internal view management
    WORKING_VIEW_MATERIALIZED = 'WorkingViewMaterialized', 'Working View Materialized'

    # Analysis triggers
    CONVERSATION_ANALYZED_FOR_CASE = 'ConversationAnalyzedForCase', 'Conversation Analyzed for Case'
    CONVERSATION_ANALYZED_FOR_AGENT = 'ConversationAnalyzedForAgent', 'Conversation Analyzed for Agent'
    STRUCTURE_SUGGESTED = 'StructureSuggested', 'Structure Suggested'

    # Plan operations
    PLAN_DIFF_PROPOSED = 'PlanDiffProposed', 'Plan Diff Proposed by AI'
    PLAN_DIFF_ACCEPTED = 'PlanDiffAccepted', 'Plan Diff Accepted'
    PLAN_DIFF_REJECTED = 'PlanDiffRejected', 'Plan Diff Rejected'
    PLAN_RESTORED = 'PlanRestored', 'Plan Restored to Previous Version'

    # ══ GRAPH ═════════════════════════════════════════════════════
    # Knowledge graph events — Node/Edge/GraphDelta lifecycle.

    GRAPH_NODE_CREATED = 'GraphNodeCreated', 'Graph Node Created'
    GRAPH_EDGE_CREATED = 'GraphEdgeCreated', 'Graph Edge Created'
    GRAPH_DELTA_COMPUTED = 'GraphDeltaComputed', 'Graph Delta Computed'
    GRAPH_EXTRACTION_STARTED = 'GraphExtractionStarted', 'Graph Extraction Started'
    GRAPH_EXTRACTION_COMPLETED = 'GraphExtractionCompleted', 'Graph Extraction Completed'

    # ══ RESERVED ══════════════════════════════════════════════════
    # Defined for planned features but not yet emitted.
    # Do NOT delete — referenced in migrations.

    INQUIRY_PRIORITY_CHANGED = 'InquiryPriorityChanged', 'Inquiry Priority Changed'
    CASE_DOCUMENT_CREATED = 'CaseDocumentCreated', 'Case Document Created'  # deprecated
    CASE_DOCUMENT_UPDATED = 'CaseDocumentUpdated', 'Case Document Updated'  # deprecated
    CASE_DOCUMENT_DELETED = 'CaseDocumentDeleted', 'Case Document Deleted'  # deprecated
    WORKING_DOCUMENT_CREATED = 'WorkingDocumentCreated', 'Working Document Created'
    WORKING_DOCUMENT_UPDATED = 'WorkingDocumentUpdated', 'Working Document Updated'
    WORKING_DOCUMENT_DELETED = 'WorkingDocumentDeleted', 'Working Document Deleted'
    EVIDENCE_CREATED = 'EvidenceCreated', 'Evidence Created'
    EVIDENCE_UPDATED = 'EvidenceUpdated', 'Evidence Updated'
    OBJECTION_CREATED = 'ObjectionCreated', 'Objection Created'
    OBJECTION_ADDRESSED = 'ObjectionAddressed', 'Objection Addressed'
    OBJECTION_DISMISSED = 'ObjectionDismissed', 'Objection Dismissed'
    CITATION_CREATED = 'CitationCreated', 'Citation Created'
    CITATION_DELETED = 'CitationDeleted', 'Citation Deleted'
    # Signal events (deprecated — signals removed, kept for migration history)
    SIGNAL_PROMOTED = 'SignalPromoted', 'Signal Promoted to Inquiry'
    SIGNAL_DISMISSED = 'SignalDismissed', 'Signal Dismissed'
    SIGNAL_EXTRACTED = 'SignalExtracted', 'Signal Extracted'
    SIGNAL_STATUS_CHANGED = 'SignalStatusChanged', 'Signal Status Changed'
    SIGNAL_EDITED = 'SignalEdited', 'Signal Edited'
    SIGNALS_LINKED_TO_CASE = 'SignalsLinkedToCase', 'Signals Linked to Case'

    AGENT_SUGGESTED = 'AgentSuggested', 'Agent Suggested'
    AGENT_CONFIRMED = 'AgentConfirmed', 'Agent Confirmed by User'
    AGENT_DECLINED = 'AgentDeclined', 'Agent Declined by User'
    STRUCTURE_IGNORED = 'StructureIgnored', 'Structure Ignored'
    BRIEF_SECTION_CREATED = 'BriefSectionCreated', 'Brief Section Created'
    BRIEF_SECTION_UPDATED = 'BriefSectionUpdated', 'Brief Section Updated'
    BRIEF_SECTION_DELETED = 'BriefSectionDeleted', 'Brief Section Deleted'


class Event(models.Model):
    """
    Append-only event store — provenance layer for case history.

    CRITICAL: Events are immutable. Never UPDATE or DELETE.
    The event stream records what happened; models hold current state.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Actor (who caused this event)
    actor_type = models.CharField(max_length=20, choices=ActorType.choices)
    actor_id = models.UUIDField(null=True, blank=True)  # User ID or null for system

    # Event classification
    type = models.CharField(max_length=100, choices=EventType.choices, db_index=True)
    category = models.CharField(
        max_length=20,
        choices=EventCategory.choices,
        default=EventCategory.PROVENANCE,
        db_index=True,
    )
    payload = models.JSONField()  # Event-specific data

    # Correlation & relationships
    correlation_id = models.UUIDField(null=True, blank=True, db_index=True)  # Groups related events
    case_id = models.UUIDField(null=True, blank=True, db_index=True)
    thread_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['case_id', 'timestamp']),
            models.Index(fields=['thread_id', 'timestamp']),
            models.Index(fields=['type', 'timestamp']),
            models.Index(fields=['correlation_id']),
            models.Index(fields=['actor_type', 'actor_id', 'timestamp']),
            models.Index(fields=['category', 'case_id', 'timestamp']),
        ]
        # Permissions to enforce append-only
        permissions = [
            ('can_append_event', 'Can append events'),
        ]

    def __str__(self):
        return f"{self.type} at {self.timestamp}"

    def save(self, *args, **kwargs):
        """Override save to prevent updates"""
        # Check if this is an update (object already exists in DB)
        if not self._state.adding:
            # This is an update attempt
            raise ValueError("Events are immutable. Cannot update existing events.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion"""
        raise ValueError("Events are immutable. Cannot delete events.")
