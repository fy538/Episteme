"""
Event models - Append-only event store (source of truth)
"""
import uuid
from django.db import models
from django.contrib.auth.models import User


class ActorType(models.TextChoices):
    USER = 'user', 'User'
    ASSISTANT = 'assistant', 'Assistant'
    SYSTEM = 'system', 'System'


class EventType(models.TextChoices):
    # ── Actively emitted ─────────────────────────────────────────────────

    # Chat events
    USER_MESSAGE_CREATED = 'UserMessageCreated', 'User Message Created'
    ASSISTANT_MESSAGE_CREATED = 'AssistantMessageCreated', 'Assistant Message Created'

    # Case lifecycle events
    CASE_CREATED = 'CaseCreated', 'Case Created'
    CASE_PATCHED = 'CasePatched', 'Case Patched'
    CASE_LINKED_TO_THREAD = 'CaseLinkedToThread', 'Case Linked to Thread'
    CONVERSATION_ANALYZED_FOR_CASE = 'ConversationAnalyzedForCase', 'Conversation Analyzed for Case'
    CASE_CREATED_FROM_ANALYSIS = 'CaseCreatedFromAnalysis', 'Case Created from Analysis'
    CASE_SCAFFOLDED = 'CaseScaffolded', 'Case Scaffolded from Chat'

    # Inquiry events
    INQUIRY_CREATED = 'InquiryCreated', 'Inquiry Created'
    INQUIRY_RESOLVED = 'InquiryResolved', 'Inquiry Resolved'
    INQUIRIES_AUTO_CREATED = 'InquiriesAutoCreated', 'Inquiries Auto-Created'

    # Signal events
    SIGNAL_EXTRACTED = 'SignalExtracted', 'Signal Extracted'
    SIGNAL_STATUS_CHANGED = 'SignalStatusChanged', 'Signal Status Changed'
    SIGNAL_EDITED = 'SignalEdited', 'Signal Edited'

    # WorkingView events
    WORKING_VIEW_MATERIALIZED = 'WorkingViewMaterialized', 'Working View Materialized'

    # Workflow events
    WORKFLOW_STARTED = 'WorkflowStarted', 'Workflow Started'
    WORKFLOW_COMPLETED = 'WorkflowCompleted', 'Workflow Completed'

    # Agent execution events
    AGENT_WORKFLOW_STARTED = 'AgentWorkflowStarted', 'Agent Workflow Started'
    AGENT_PROGRESS = 'AgentProgress', 'Agent Progress Update'
    AGENT_COMPLETED = 'AgentCompleted', 'Agent Workflow Completed'
    AGENT_FAILED = 'AgentFailed', 'Agent Workflow Failed'
    AGENT_CHECKPOINT = 'AgentCheckpoint', 'Agent Loop Checkpoint'
    AGENT_TRAJECTORY = 'AgentTrajectory', 'Agent Decision Trajectory'

    # Structure discovery events
    STRUCTURE_ACCEPTED = 'StructureAccepted', 'Structure Accepted'
    STRUCTURE_DISMISSED = 'StructureDismissed', 'Structure Dismissed'

    # ── Reserved / not yet emitted ───────────────────────────────────────
    # These types are defined for planned features but not yet emitted.
    # Do NOT delete — they may be referenced in migrations or frontend code.

    INQUIRY_REOPENED = 'InquiryReopened', 'Inquiry Reopened'
    INQUIRY_PRIORITY_CHANGED = 'InquiryPriorityChanged', 'Inquiry Priority Changed'

    CASE_DOCUMENT_CREATED = 'CaseDocumentCreated', 'Case Document Created'
    CASE_DOCUMENT_UPDATED = 'CaseDocumentUpdated', 'Case Document Updated'
    CASE_DOCUMENT_DELETED = 'CaseDocumentDeleted', 'Case Document Deleted'

    EVIDENCE_CREATED = 'EvidenceCreated', 'Evidence Created'
    EVIDENCE_UPDATED = 'EvidenceUpdated', 'Evidence Updated'

    OBJECTION_CREATED = 'ObjectionCreated', 'Objection Created'
    OBJECTION_ADDRESSED = 'ObjectionAddressed', 'Objection Addressed'
    OBJECTION_DISMISSED = 'ObjectionDismissed', 'Objection Dismissed'

    CITATION_CREATED = 'CitationCreated', 'Citation Created'
    CITATION_DELETED = 'CitationDeleted', 'Citation Deleted'

    SIGNALS_LINKED_TO_CASE = 'SignalsLinkedToCase', 'Signals Linked to Case'

    CONVERSATION_ANALYZED_FOR_AGENT = 'ConversationAnalyzedForAgent', 'Conversation Analyzed for Agent'
    AGENT_SUGGESTED = 'AgentSuggested', 'Agent Suggested'
    AGENT_CONFIRMED = 'AgentConfirmed', 'Agent Confirmed by User'
    AGENT_DECLINED = 'AgentDeclined', 'Agent Declined by User'

    STRUCTURE_SUGGESTED = 'StructureSuggested', 'Structure Suggested'
    STRUCTURE_IGNORED = 'StructureIgnored', 'Structure Ignored'

    BRIEF_EVOLVED = 'BriefEvolved', 'Brief Grounding Evolved'
    BRIEF_SECTION_CREATED = 'BriefSectionCreated', 'Brief Section Created'
    BRIEF_SECTION_UPDATED = 'BriefSectionUpdated', 'Brief Section Updated'
    BRIEF_SECTION_DELETED = 'BriefSectionDeleted', 'Brief Section Deleted'


class Event(models.Model):
    """
    Append-only event store - the single source of truth
    
    CRITICAL: Events are immutable. Never UPDATE or DELETE.
    Any change to the system state must be a new event.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Actor (who caused this event)
    actor_type = models.CharField(max_length=20, choices=ActorType.choices)
    actor_id = models.UUIDField(null=True, blank=True)  # User ID or null for system
    
    # Event classification
    type = models.CharField(max_length=100, choices=EventType.choices, db_index=True)
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
