"""
Knowledge Graph models — Node, Edge, GraphDelta.

The graph is the product. Everything else is a view.

Node and Edge form a typed property graph over project-level knowledge.
GraphDelta records every mutation with human-readable narratives.
"""
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from pgvector.django import VectorField

from apps.common.models import TimestampedModel, UUIDModel


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════

class NodeType(models.TextChoices):
    """Cognitive node types in the knowledge graph."""
    # V1 — orientation mode
    CLAIM = 'claim', 'Claim'                     # Assertion from a document or conversation
    EVIDENCE = 'evidence', 'Evidence'             # Fact, data point, observation
    ASSUMPTION = 'assumption', 'Assumption'       # Unverified belief bridging evidence to conclusions
    TENSION = 'tension', 'Tension'                # Contradiction or conflict between nodes

    # Future — decision mode (DO NOT IMPLEMENT YET)
    # FOCUS = 'focus', 'Focus'
    # OPTION = 'option', 'Option'
    # SCENARIO = 'scenario', 'Scenario'
    # UNCERTAINTY = 'uncertainty', 'Uncertainty'


class NodeStatus(models.TextChoices):
    """Status values for nodes. Valid combinations enforced in Node.clean()."""
    # Claim statuses
    SUPPORTED = 'supported', 'Supported'                         # Multiple evidence sources agree
    CONTESTED = 'contested', 'Contested'                         # Evidence conflicts
    UNSUBSTANTIATED = 'unsubstantiated', 'Unsubstantiated'       # No evidence either way

    # Evidence statuses
    CONFIRMED = 'confirmed', 'Confirmed'                         # Verified, high credibility
    UNCERTAIN = 'uncertain', 'Uncertain'                         # Unverified or low confidence
    DISPUTED = 'disputed', 'Disputed'                            # Conflicting sources

    # Assumption statuses
    UNTESTED = 'untested', 'Untested'                            # No evidence for or against
    ASSUMPTION_CONFIRMED = 'assumption_confirmed', 'Assumption Confirmed'
    CHALLENGED = 'challenged', 'Challenged'                      # Evidence exists both ways
    REFUTED = 'refuted', 'Refuted'                               # Strong evidence against

    # Tension statuses
    SURFACED = 'surfaced', 'Surfaced'                            # Detected, not yet addressed
    ACKNOWLEDGED = 'acknowledged', 'Acknowledged'                # User has seen and considered
    RESOLVED = 'resolved', 'Resolved'                            # No longer a live contradiction


# Type-status validation map
VALID_STATUSES_BY_TYPE = {
    NodeType.CLAIM: {
        NodeStatus.SUPPORTED,
        NodeStatus.CONTESTED,
        NodeStatus.UNSUBSTANTIATED,
    },
    NodeType.EVIDENCE: {
        NodeStatus.CONFIRMED,
        NodeStatus.UNCERTAIN,
        NodeStatus.DISPUTED,
    },
    NodeType.ASSUMPTION: {
        NodeStatus.UNTESTED,
        NodeStatus.ASSUMPTION_CONFIRMED,
        NodeStatus.CHALLENGED,
        NodeStatus.REFUTED,
    },
    NodeType.TENSION: {
        NodeStatus.SURFACED,
        NodeStatus.ACKNOWLEDGED,
        NodeStatus.RESOLVED,
    },
}

# Default status when type is known but status is missing/invalid
DEFAULT_STATUS_BY_TYPE = {
    NodeType.CLAIM: NodeStatus.UNSUBSTANTIATED,
    NodeType.EVIDENCE: NodeStatus.UNCERTAIN,
    NodeType.ASSUMPTION: NodeStatus.UNTESTED,
    NodeType.TENSION: NodeStatus.SURFACED,
}


class EdgeType(models.TextChoices):
    """Typed relationships between nodes."""
    SUPPORTS = 'supports', 'Supports'               # Evidence or reasoning favoring target
    CONTRADICTS = 'contradicts', 'Contradicts'       # Evidence or reasoning opposing target
    DEPENDS_ON = 'depends_on', 'Depends On'          # Source requires target to hold

    # Future
    # LEADS_TO = 'leads_to', 'Leads To'
    # RISKS = 'risks', 'Risks'
    # IMPLIES = 'implies', 'Implies'
    # SCOPES = 'scopes', 'Scopes'


class NodeSourceType(models.TextChoices):
    """How a node was created."""
    DOCUMENT_EXTRACTION = 'document_extraction', 'Document Extraction'
    CHAT_EDIT = 'chat_edit', 'Chat Edit'
    AGENT_ANALYSIS = 'agent_analysis', 'Agent Analysis'
    USER_EDIT = 'user_edit', 'User Edit'
    INTEGRATION = 'integration', 'Integration'       # Cross-document integration


class DeltaTrigger(models.TextChoices):
    """What caused a graph mutation."""
    DOCUMENT_UPLOAD = 'document_upload', 'Document Upload'
    CHAT_EDIT = 'chat_edit', 'Chat Edit'
    AGENT_ANALYSIS = 'agent_analysis', 'Agent Analysis'
    USER_EDIT = 'user_edit', 'User Edit'


class InclusionType(models.TextChoices):
    """How a project node was pulled into a case view."""
    AUTO = 'auto', 'Auto-pulled by similarity'
    MANUAL = 'manual', 'Manually added by user'
    DOCUMENT = 'document', 'From document integration'


# ═══════════════════════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════════════════════

class Node(UUIDModel, TimestampedModel):
    """
    A node in the knowledge graph.

    Represents a claim, evidence, assumption, or tension extracted from
    documents or created through conversation. The node_type field determines
    the cognitive role; the status field tracks epistemic state.

    Properties JSON carries type-specific metadata:
    - Claim: {source_context, specificity}
    - Evidence: {credibility, evidence_type, source_url, source_title}
    - Assumption: {load_bearing, implicit, scope}
    - Tension: {tension_type, severity, between_nodes, description}
    """
    # Type and status
    node_type = models.CharField(
        max_length=32,
        choices=NodeType.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=32,
        choices=NodeStatus.choices,
    )

    # Content
    content = models.TextField(
        help_text="Human-readable content of this node"
    )
    properties = models.JSONField(
        default=dict,
        blank=True,
        help_text="Type-specific metadata (see docstring)"
    )

    # Ownership
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='graph_nodes',
    )
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graph_nodes',
        help_text="If case-scoped, which case owns this node"
    )
    scope = models.CharField(
        max_length=16,
        default='project',
        choices=[('project', 'Project'), ('case', 'Case')],
    )

    # Provenance — where did this node come from?
    source_type = models.CharField(
        max_length=32,
        choices=NodeSourceType.choices,
    )
    source_document = models.ForeignKey(
        'projects.Document',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='extracted_nodes',
    )
    source_chunks = models.ManyToManyField(
        'projects.DocumentChunk',
        blank=True,
        related_name='source_for_nodes',
    )
    source_message = models.ForeignKey(
        'chat.Message',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_nodes',
    )

    # Semantic embedding for similarity search (pgvector)
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        help_text="384-dim embedding from sentence-transformers all-MiniLM-L6-v2"
    )

    # Confidence (extraction or user-assigned)
    confidence = models.FloatField(
        default=0.8,
        help_text="Confidence in this node (0.0-1.0)"
    )

    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'node_type']),
            models.Index(fields=['project', 'scope']),
            models.Index(fields=['case', 'node_type']),
            models.Index(fields=['source_document']),
            models.Index(fields=['project', 'status']),
        ]

    def __str__(self):
        return f"[{self.node_type}] {self.content[:80]}"

    def clean(self):
        """Validate type-status combination."""
        valid_statuses = VALID_STATUSES_BY_TYPE.get(self.node_type, set())
        if valid_statuses and self.status not in valid_statuses:
            raise ValidationError(
                f"Status '{self.status}' is not valid for node type '{self.node_type}'. "
                f"Valid statuses: {[s.value for s in valid_statuses]}"
            )

    def save(self, *args, **kwargs):
        # Auto-fix invalid status before save
        valid_statuses = VALID_STATUSES_BY_TYPE.get(self.node_type, set())
        if valid_statuses and self.status not in valid_statuses:
            self.status = DEFAULT_STATUS_BY_TYPE.get(
                self.node_type, NodeStatus.UNSUBSTANTIATED
            )
        super().save(*args, **kwargs)


class Edge(UUIDModel, TimestampedModel):
    """
    A typed, directed relationship between two nodes.

    Edges carry provenance (why this relationship exists) and
    optional strength (0.0-1.0 confidence in the relationship).
    """
    edge_type = models.CharField(
        max_length=32,
        choices=EdgeType.choices,
    )
    source_node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='outgoing_edges',
    )
    target_node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='incoming_edges',
    )

    # Relationship metadata
    strength = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence in this relationship (0.0-1.0)"
    )
    provenance = models.TextField(
        blank=True,
        help_text="Why this relationship exists"
    )

    # Provenance
    source_type = models.CharField(
        max_length=32,
        choices=NodeSourceType.choices,
    )
    source_document = models.ForeignKey(
        'projects.Document',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source_node', 'edge_type']),
            models.Index(fields=['target_node', 'edge_type']),
            models.Index(fields=['edge_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['source_node', 'target_node', 'edge_type'],
                name='unique_edge_per_type',
            )
        ]

    def __str__(self):
        return f"{self.source_node.content[:30]} --{self.edge_type}--> {self.target_node.content[:30]}"


class GraphDelta(UUIDModel, TimestampedModel):
    """
    Record of a graph mutation — what changed, and why it matters.

    Every document upload, chat edit, or agent analysis produces a delta.
    The narrative is the user-facing summary: "This document challenged
    2 assumptions and revealed a tension between your growth claims."
    """
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='graph_deltas',
    )

    # What triggered this mutation
    trigger = models.CharField(
        max_length=32,
        choices=DeltaTrigger.choices,
    )

    # Structured diff
    patch = models.JSONField(
        default=dict,
        help_text="Structured diff: {nodes_added, nodes_modified, nodes_removed, edges_added, ...}"
    )

    # Human-readable narrative
    narrative = models.TextField(
        blank=True,
        help_text="2-3 sentence summary of what changed and why it matters"
    )

    # Impact counters (for quick display without parsing patch)
    nodes_created = models.IntegerField(default=0)
    nodes_updated = models.IntegerField(default=0)
    edges_created = models.IntegerField(default=0)
    tensions_surfaced = models.IntegerField(default=0)
    assumptions_challenged = models.IntegerField(default=0)

    # Case (optional — set when mutation is case-scoped)
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graph_deltas',
    )

    # Provenance
    source_document = models.ForeignKey(
        'projects.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graph_deltas',
    )
    source_message = models.ForeignKey(
        'chat.Message',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graph_deltas',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['trigger']),
        ]

    def __str__(self):
        return f"Delta [{self.trigger}] — {self.narrative[:80]}" if self.narrative else f"Delta [{self.trigger}]"


class CaseNodeReference(UUIDModel, TimestampedModel):
    """
    Through-table allowing a case to "see" a project-scoped node
    without copying it. Cases are views, not copies.

    - inclusion_type tracks how the reference was created
    - relevance stores the similarity score for auto-pulled nodes
    - excluded=True means user soft-hid this node; the row persists
      so auto-pull doesn't re-add it
    """
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='node_references',
    )
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='case_references',
    )
    inclusion_type = models.CharField(
        max_length=16,
        choices=InclusionType.choices,
        default=InclusionType.AUTO,
    )
    relevance = models.FloatField(
        default=0.0,
        help_text="Similarity score when auto-pulled (0.0-1.0)",
    )
    excluded = models.BooleanField(
        default=False,
        help_text="User soft-hid this node from case view",
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['case', 'node'],
                name='unique_case_node_ref',
            )
        ]
        indexes = [
            models.Index(fields=['case', 'excluded']),
            models.Index(fields=['node']),
        ]

    def __str__(self):
        return f"Case {self.case_id} -> Node {self.node.content[:40]}"


# ═══════════════════════════════════════════════════════════════════
# Project Summary
# ═══════════════════════════════════════════════════════════════════

class SummaryStatus(models.TextChoices):
    """Generation state of a project summary."""
    NONE = 'none', 'No summary yet'
    SEED = 'seed', 'Seed (template, no LLM)'
    GENERATING = 'generating', 'Generating'
    PARTIAL = 'partial', 'Partial'
    FULL = 'full', 'Full'
    FAILED = 'failed', 'Failed'


class ProjectSummary(UUIDModel, TimestampedModel):
    """
    AI-generated narrative summary of a project's knowledge graph.

    Each generation creates a new row (versioned). The most recent
    non-failed row is the "current" summary.

    Sections JSON shape:
    {
        "overview": "...",
        "key_findings": [
            {"theme_label": "...", "narrative": "...", "cited_nodes": ["uuid", ...]}
        ],
        "emerging_picture": "...",
        "attention_needed": "...",
        "what_changed": "..."
    }
    """
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='summaries',
    )
    status = models.CharField(
        max_length=20,
        choices=SummaryStatus.choices,
        default=SummaryStatus.NONE,
    )

    # Structured sections
    sections = models.JSONField(
        default=dict,
        help_text="Structured sections: overview, key_findings, emerging_picture, attention_needed, what_changed"
    )

    # Staleness tracking
    is_stale = models.BooleanField(default=False)
    stale_since = models.DateTimeField(null=True, blank=True)

    # Generation metadata (model, tokens, latency, node_count, cluster_count)
    generation_metadata = models.JSONField(default=dict, blank=True)
    version = models.IntegerField(default=1)

    # Cluster data cached for frontend citation cross-referencing
    clusters = models.JSONField(default=list, blank=True)

    # Which delta was latest when this was generated (for "what changed" diffing)
    latest_delta_at_generation = models.ForeignKey(
        'graph.GraphDelta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['project', 'is_stale']),
        ]

    def __str__(self):
        return f"Summary v{self.version} [{self.status}] for {self.project_id}"
