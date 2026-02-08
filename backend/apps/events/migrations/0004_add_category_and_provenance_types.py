"""
Add category field to Event model and new provenance event types.

The category field separates provenance events (user-facing case history)
from operational events (internal/debugging). Existing events default to
'provenance'; a data migration then marks known operational types.
"""

from django.db import migrations, models


# All event type choices including new provenance types
ALL_EVENT_TYPE_CHOICES = [
    # Provenance
    ("CaseCreated", "Case Created"),
    ("CaseCreatedFromAnalysis", "Case Created from Analysis"),
    ("CaseScaffolded", "Case Scaffolded from Chat"),
    ("CaseArchived", "Case Archived"),
    ("InquiryCreated", "Inquiry Created"),
    ("InquiryResolved", "Inquiry Resolved"),
    ("InquiryReopened", "Inquiry Reopened"),
    ("InquiriesAutoCreated", "Inquiries Auto-Created"),
    ("DocumentAdded", "Document Added"),
    ("EvidenceAdded", "Evidence Added"),
    ("SignalPromoted", "Signal Promoted to Inquiry"),
    ("SignalDismissed", "Signal Dismissed"),
    ("BriefEvolved", "Brief Grounding Evolved"),
    ("BriefSectionWritten", "Brief Section Written"),
    ("BriefSectionRevised", "Brief Section Revised"),
    ("StructureAccepted", "Structure Accepted"),
    ("StructureDismissed", "Structure Dismissed"),
    ("ResearchCompleted", "Research Completed"),
    ("ConfidenceChanged", "Confidence Changed"),
    ("PositionRevised", "Position Revised"),
    # Operational
    ("UserMessageCreated", "User Message Created"),
    ("AssistantMessageCreated", "Assistant Message Created"),
    ("CasePatched", "Case Patched"),
    ("CaseLinkedToThread", "Case Linked to Thread"),
    ("AgentWorkflowStarted", "Agent Workflow Started"),
    ("AgentProgress", "Agent Progress Update"),
    ("AgentCompleted", "Agent Workflow Completed"),
    ("AgentFailed", "Agent Workflow Failed"),
    ("AgentCheckpoint", "Agent Loop Checkpoint"),
    ("AgentTrajectory", "Agent Decision Trajectory"),
    ("WorkflowStarted", "Workflow Started"),
    ("WorkflowCompleted", "Workflow Completed"),
    ("SignalExtracted", "Signal Extracted"),
    ("SignalStatusChanged", "Signal Status Changed"),
    ("SignalEdited", "Signal Edited"),
    ("WorkingViewMaterialized", "Working View Materialized"),
    ("ConversationAnalyzedForCase", "Conversation Analyzed for Case"),
    ("ConversationAnalyzedForAgent", "Conversation Analyzed for Agent"),
    ("StructureSuggested", "Structure Suggested"),
    # Reserved
    ("InquiryPriorityChanged", "Inquiry Priority Changed"),
    ("CaseDocumentCreated", "Case Document Created"),
    ("CaseDocumentUpdated", "Case Document Updated"),
    ("CaseDocumentDeleted", "Case Document Deleted"),
    ("EvidenceCreated", "Evidence Created"),
    ("EvidenceUpdated", "Evidence Updated"),
    ("ObjectionCreated", "Objection Created"),
    ("ObjectionAddressed", "Objection Addressed"),
    ("ObjectionDismissed", "Objection Dismissed"),
    ("CitationCreated", "Citation Created"),
    ("CitationDeleted", "Citation Deleted"),
    ("SignalsLinkedToCase", "Signals Linked to Case"),
    ("AgentSuggested", "Agent Suggested"),
    ("AgentConfirmed", "Agent Confirmed by User"),
    ("AgentDeclined", "Agent Declined by User"),
    ("StructureIgnored", "Structure Ignored"),
    ("BriefSectionCreated", "Brief Section Created"),
    ("BriefSectionUpdated", "Brief Section Updated"),
    ("BriefSectionDeleted", "Brief Section Deleted"),
]

OPERATIONAL_TYPES = [
    "UserMessageCreated",
    "AssistantMessageCreated",
    "CasePatched",
    "CaseLinkedToThread",
    "AgentWorkflowStarted",
    "AgentProgress",
    "AgentCompleted",
    "AgentFailed",
    "AgentCheckpoint",
    "AgentTrajectory",
    "WorkflowStarted",
    "WorkflowCompleted",
    "SignalExtracted",
    "SignalStatusChanged",
    "SignalEdited",
    "WorkingViewMaterialized",
    "ConversationAnalyzedForCase",
    "ConversationAnalyzedForAgent",
    "StructureSuggested",
]


def categorize_existing_events(apps, schema_editor):
    """Mark existing operational events with the correct category."""
    Event = apps.get_model("events", "Event")
    Event.objects.filter(type__in=OPERATIONAL_TYPES).update(category="operational")


def reverse_categorize(apps, schema_editor):
    """Reverse: set all events back to provenance (the default)."""
    Event = apps.get_model("events", "Event")
    Event.objects.all().update(category="provenance")


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0003_alter_event_type"),
    ]

    operations = [
        # 1. Add category field with default='provenance'
        migrations.AddField(
            model_name="event",
            name="category",
            field=models.CharField(
                choices=[
                    ("provenance", "Provenance (case history)"),
                    ("operational", "Operational (internal)"),
                ],
                db_index=True,
                default="provenance",
                max_length=20,
            ),
        ),
        # 2. Update type field choices to include new provenance types
        migrations.AlterField(
            model_name="event",
            name="type",
            field=models.CharField(
                choices=ALL_EVENT_TYPE_CHOICES,
                db_index=True,
                max_length=100,
            ),
        ),
        # 3. Add composite index for category + case_id + timestamp
        migrations.AddIndex(
            model_name="event",
            index=models.Index(
                fields=["category", "case_id", "timestamp"],
                name="events_event_cat_case_ts_idx",
            ),
        ),
        # 4. Data migration: categorize existing events
        migrations.RunPython(
            categorize_existing_events,
            reverse_categorize,
        ),
    ]
