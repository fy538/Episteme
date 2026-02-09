# V1 Implementation Spec — Orientation Mode

The buildable spec for Episteme v1. Everything in this document derives from the Decision State Architecture and Product Vision. Nothing outside this document is in scope.

**Target aha moment:** "I uploaded my docs and the system showed me where they fight."

**What v1 delivers:** A user uploads documents into a project. The system extracts claims, surfaces implicit assumptions, detects contradictions, and renders an orientation map — a structured view of what the documents agree on, where they fight, what they assume without evidence, and what they never address. The user can then converse with an agent that understands the graph and can edit it structurally.

**What v1 does NOT deliver:** Cases, modes beyond orientation, readiness gating, plans, briefs, skills, multi-agent orchestration, commitment flows, options, scenarios, implementation intentions.

---

## Layer 1: Graph Primitives

The foundation. Every feature in v1 and beyond is a function of this data model.

### Design Principles

1. **One table for nodes, one table for edges.** No separate models for claims vs. assumptions vs. evidence. The type field distinguishes them. Adding a new cognitive concept never requires a migration.
2. **Provenance on everything.** Every node and edge traces back to its origin — which document, which chunk, which message, which agent action. Trust requires traceability.
3. **Properties over columns.** Type-specific metadata lives in a JSON field. If you query or sort on it, promote it to a column. Otherwise, keep the table clean.
4. **Scope-ready but scope-simple.** The schema supports project vs. case scoping, but v1 only uses project scope. No case logic is implemented yet.

### Node Model

```python
class NodeType(models.TextChoices):
    # V1 — orientation
    CLAIM = "claim"                 # Assertion from a document or conversation
    EVIDENCE = "evidence"           # Fact, data point, observation grounding a claim
    ASSUMPTION = "assumption"       # Unverified belief bridging evidence to conclusions
    TENSION = "tension"             # Contradiction or conflict between nodes

    # Future — decision mode (DO NOT IMPLEMENT)
    # FOCUS = "focus"
    # OPTION = "option"
    # SCENARIO = "scenario"
    # UNCERTAINTY = "uncertainty"


class NodeStatus(models.TextChoices):
    # Claim statuses
    SUPPORTED = "supported"             # Multiple evidence sources agree
    CONTESTED = "contested"             # Evidence conflicts
    UNSUBSTANTIATED = "unsubstantiated" # No evidence either way

    # Evidence statuses
    CONFIRMED = "confirmed"             # Verified, high credibility
    UNCERTAIN = "uncertain"             # Unverified or low confidence
    DISPUTED = "disputed"               # Conflicting sources

    # Assumption statuses
    UNTESTED = "untested"               # No evidence for or against
    ASSUMPTION_CONFIRMED = "assumption_confirmed"
    CHALLENGED = "challenged"           # Evidence exists both ways
    REFUTED = "refuted"                 # Strong evidence against

    # Tension statuses
    SURFACED = "surfaced"               # Detected, not yet addressed
    ACKNOWLEDGED = "acknowledged"       # User has seen and considered
    RESOLVED = "resolved"               # No longer a live contradiction


class NodeSourceType(models.TextChoices):
    DOCUMENT_EXTRACTION = "document_extraction"   # Extracted by LLM from uploaded document
    CHAT = "chat"                                 # Created from user conversation
    AGENT = "agent"                               # Created by agent analysis
    USER_EDIT = "user_edit"                        # Directly created/modified by user
    INTEGRATION = "integration"                    # Created during cross-document integration


class Node(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    type = models.CharField(max_length=32, choices=NodeType.choices)
    status = models.CharField(max_length=32, choices=NodeStatus.choices)
    content = models.TextField()                    # Human-readable content
    properties = models.JSONField(default=dict)     # Type-specific metadata (see below)

    # Ownership
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="nodes")
    case = models.ForeignKey("cases.Case", on_delete=models.CASCADE, null=True, blank=True,
                             related_name="case_nodes")  # Null = project-scoped
    scope = models.CharField(max_length=16, default="project",
                             choices=[("project", "project"), ("case", "case")])

    # Provenance — where did this node come from?
    source_type = models.CharField(max_length=32, choices=NodeSourceType.choices)
    source_document = models.ForeignKey("projects.Document", on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name="extracted_nodes")
    source_chunks = models.ManyToManyField("projects.DocumentChunk", blank=True,
                                           related_name="source_for_nodes")
    source_message = models.ForeignKey("chat.Message", on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name="created_nodes")

    # Semantic — requires pgvector extension: CREATE EXTENSION vector;
    from pgvector.django import VectorField
    embedding = VectorField(dimensions=384, null=True, blank=True)  # sentence-transformers all-MiniLM-L6-v2

    # Metadata
    created_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "type"]),
            models.Index(fields=["project", "scope"]),
            models.Index(fields=["source_document"]),
        ]
```

#### Properties by Node Type

The `properties` JSON field carries type-specific metadata. These are display/prompt fields, not query fields.

```python
# Claim properties
{
    "source_context": "paragraph or section where claim appears",
    "specificity": "high" | "medium" | "low",  # How concrete vs. vague
}

# Evidence properties
{
    "credibility": 0.0-1.0,            # Source reliability
    "evidence_type": "fact" | "metric" | "quote" | "benchmark" | "observation",
    "source_url": "...",               # External source if applicable
    "source_title": "...",
    "published_date": "ISO date",
}

# Assumption properties
{
    "load_bearing": true | false,      # Does a key conclusion depend on this?
    "implicit": true | false,          # Was this stated or inferred?
    "scope": "description of what this assumption covers",
}

# Tension properties
{
    "tension_type": "contradiction" | "tradeoff" | "gap" | "inconsistency",
    "severity": "high" | "medium" | "low",
    "between_nodes": ["node-uuid-1", "node-uuid-2"],  # The nodes in conflict
    "description": "Why these conflict",               # Explanation of the tension
}
```

### Edge Model

```python
class EdgeType(models.TextChoices):
    # V1
    SUPPORTS = "supports"           # Evidence or reasoning favoring target
    CONTRADICTS = "contradicts"     # Evidence or reasoning opposing target
    DEPENDS_ON = "depends_on"       # Source requires target to hold

    # Future (DO NOT IMPLEMENT)
    # LEADS_TO = "leads_to"
    # RISKS = "risks"
    # IMPLIES = "implies"
    # SCOPES = "scopes"


class Edge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    type = models.CharField(max_length=32, choices=EdgeType.choices)
    source_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="outgoing_edges")
    target_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="incoming_edges")

    strength = models.FloatField(null=True, blank=True)  # 0.0-1.0, optional
    provenance = models.TextField(blank=True)             # Why this edge exists

    # Provenance
    source_type = models.CharField(max_length=32, choices=NodeSourceType.choices)
    source_document = models.ForeignKey("projects.Document", on_delete=models.SET_NULL,
                                        null=True, blank=True)

    created_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["source_node"]),
            models.Index(fields=["target_node"]),
            models.Index(fields=["type"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["source_node", "target_node", "type"],
                                    name="unique_edge_per_type")
        ]
```

### Project Model Updates

The existing Project model stays mostly intact. Key additions:

```python
class Project(models.Model):
    # Existing fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="projects")
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # REMOVE these denormalized counters — derive from graph instead
    # total_signals, total_cases, total_documents, top_themes
```

Graph health is computed, never stored:

```python
def get_graph_health(project_id):
    """Compute orientation health from graph structure."""
    nodes = Node.objects.filter(project_id=project_id, scope="project")
    return {
        "total_nodes": nodes.count(),
        "claims": nodes.filter(type="claim").count(),
        "evidence": nodes.filter(type="evidence").count(),
        "assumptions": nodes.filter(type="assumption").count(),
        "tensions": nodes.filter(type="tension").count(),
        "untested_assumptions": nodes.filter(type="assumption", status="untested").count(),
        "unsubstantiated_claims": nodes.filter(type="claim", status="unsubstantiated").count(),
        "active_tensions": nodes.filter(type="tension").exclude(status="resolved").count(),
    }
```

### Document Model Updates

```python
class Document(models.Model):
    # Existing fields stay
    # ...

    # NEW: Extraction lifecycle
    extraction_status = models.CharField(
        max_length=32,
        choices=[
            ("pending", "Pending"),
            ("extracting", "Extracting"),       # Phase A: extracting nodes from document
            ("integrating", "Integrating"),     # Phase B: integrating with existing graph
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending"
    )
    extraction_error = models.TextField(blank=True)

    # NEW: Document-level summary for graph integration context
    summary = models.TextField(blank=True)  # LLM-generated summary of key content
    extracted_node_count = models.IntegerField(default=0)  # How many nodes came from this doc
```

### Delta Model

Every graph mutation produces a delta. This is the mechanism that makes the system feel alive.

```python
class GraphDelta(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="deltas")

    trigger = models.CharField(max_length=32, choices=[
        ("document_upload", "Document Upload"),
        ("chat_edit", "Chat Edit"),
        ("agent_analysis", "Agent Analysis"),
        ("user_edit", "User Edit"),
    ])

    # What changed
    patch = models.JSONField()  # Structured list of changes (see below)
    narrative = models.TextField()  # Human-readable: "This document challenged 2 assumptions..."

    # Impact summary
    nodes_created = models.IntegerField(default=0)
    nodes_updated = models.IntegerField(default=0)
    edges_created = models.IntegerField(default=0)
    tensions_surfaced = models.IntegerField(default=0)
    assumptions_challenged = models.IntegerField(default=0)

    # Provenance
    source_document = models.ForeignKey("projects.Document", null=True, blank=True,
                                         on_delete=models.SET_NULL)
    source_message = models.ForeignKey("chat.Message", null=True, blank=True,
                                        on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
```

Patch structure:

```json
{
    "changes": [
        {
            "action": "create_node",
            "node_id": "uuid",
            "node_type": "claim",
            "content": "Market will grow 28% annually",
            "source_document": "uuid"
        },
        {
            "action": "create_edge",
            "edge_id": "uuid",
            "edge_type": "contradicts",
            "source_node": "uuid-1",
            "target_node": "uuid-2",
            "provenance": "Pitch deck claims 28% growth; market report says 12%"
        },
        {
            "action": "update_node",
            "node_id": "uuid",
            "field": "status",
            "from": "untested",
            "to": "challenged",
            "reason": "New evidence contradicts this assumption"
        },
        {
            "action": "create_tension",
            "node_id": "uuid",
            "between": ["uuid-1", "uuid-2"],
            "description": "Growth rate claims are incompatible"
        }
    ]
}
```

---

## Layer 2: Extraction & Integration Pipeline

This is the engine that produces the aha moment. Document upload triggers a two-phase pipeline that extracts knowledge from the document and integrates it with the existing project graph.

### Pipeline Overview

```
User uploads document
    │
    ▼
┌─────────────────────────┐
│  Preprocessing          │  Existing pipeline: store file, extract text,
│  (keep existing)        │  chunk into 256-512 token segments, generate
│                         │  chunk embeddings
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Phase A: Extraction    │  NEW: LLM extracts claims, evidence, and
│  "What does this doc    │  assumptions at document level. Produces
│   say?"                 │  Node objects with chunk provenance.
│                         │  Target: 5-12 nodes per document.
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Phase B: Integration   │  NEW: LLM compares new nodes against existing
│  "How does this relate  │  project graph. Creates edges, detects tensions,
│   to what we know?"     │  updates statuses. Produces the cross-document
│                         │  insight that makes the aha moment.
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Delta Generation       │  NEW: Compute what changed and generate
│  "What just happened?"  │  human-readable narrative.
└─────────────────────────┘
```

### Preprocessing (Existing — Adapt)

The current Document → DocumentChunk pipeline stays. Modifications:

1. **Keep:** File upload, text extraction (PDF/DOCX/etc.), chunking (256-512 tokens, 10-20% overlap), chunk embedding generation (sentence-transformers, 384-dim).
2. **Add:** After chunking, generate a **document-level summary** (1-2 paragraphs). This summary is stored on `Document.summary` and used as compact context during Phase B when the graph is large.
3. **Add:** Set `Document.extraction_status = "extracting"` when Phase A begins.
4. **Remove:** The old signal extraction from documents. Nodes replace signals.

### Phase A: Document Extraction

**Input:** Full document text (or chunked sections if document exceeds context window).
**Output:** A list of extracted nodes with chunk provenance.

#### Extraction Prompt Strategy

The LLM receives the full document text and produces structured JSON:

```
System: You are analyzing a document to extract its key knowledge components
for a reasoning graph. Extract ONLY the most important items — aim for
quality over quantity.

For each item, classify it as one of:
- CLAIM: A specific assertion or conclusion the document makes
- EVIDENCE: A concrete fact, data point, metric, or observation
- ASSUMPTION: A belief the document takes for granted without proving

Rules:
- Extract 3-7 claims (the document's key assertions)
- Extract 2-5 evidence items (concrete facts/data supporting claims)
- Surface 1-3 implicit assumptions (things assumed but never stated or proven)
- For each item, quote the specific passage it comes from
- For assumptions, explain WHY this is an assumption (what would need to
  be true, and what evidence is missing)
- Be precise and specific. "The market is growing" is too vague.
  "The document claims the TAM will reach $4.2B by 2027" is specific.

Output format:
{
    "nodes": [
        {
            "type": "claim" | "evidence" | "assumption",
            "content": "specific, concrete statement",
            "status": "supported" | "unsubstantiated" | "confirmed" | "uncertain" | "untested",
            "source_passage": "exact quote from document",
            "source_location": "section/page/paragraph identifier",
            "properties": { ... type-specific properties ... },
            "reasoning": "why this was extracted and classified this way"
        }
    ],
    "document_summary": "2-3 sentence summary of the document's core argument"
}
```

#### Chunk Provenance Mapping

After extraction, map each node to its source chunk(s):

```python
async def map_nodes_to_chunks(extracted_nodes, document_chunks):
    """
    For each extracted node, find the chunk(s) containing its source passage.
    Uses exact text matching first, then embedding similarity as fallback.
    """
    for node_data in extracted_nodes:
        passage = node_data["source_passage"]

        # 1. Try exact substring match against chunk texts
        matching_chunks = [
            chunk for chunk in document_chunks
            if passage[:80].lower() in chunk.chunk_text.lower()
        ]

        # 2. Fallback: embedding similarity
        if not matching_chunks:
            passage_embedding = await generate_embedding(passage)
            matching_chunks = find_similar_chunks(
                passage_embedding, document_chunks, threshold=0.85, top_k=2
            )

        node_data["chunk_ids"] = [c.id for c in matching_chunks]
```

#### Node Creation

```python
async def create_nodes_from_extraction(project, document, extracted_data):
    """Phase A: Create Node objects from LLM extraction."""
    created_nodes = []

    for node_data in extracted_data["nodes"]:
        node = Node.objects.create(
            type=node_data["type"],
            status=node_data["status"],
            content=node_data["content"],
            properties={
                **node_data.get("properties", {}),
                "extraction_reasoning": node_data["reasoning"],
            },
            project=project,
            scope="project",
            source_type="document_extraction",
            source_document=document,
        )
        # Link to source chunks
        if node_data.get("chunk_ids"):
            node.source_chunks.set(node_data["chunk_ids"])

        # Generate embedding for future similarity matching
        node.embedding = await generate_embedding(node.content)
        node.save()

        created_nodes.append(node)

    # Update document
    document.summary = extracted_data.get("document_summary", "")
    document.extracted_node_count = len(created_nodes)
    document.extraction_status = "integrating"
    document.save()

    return created_nodes
```

### Phase B: Graph Integration

**Input:** New nodes from Phase A + existing project graph.
**Output:** New edges, new tension nodes, updated statuses on existing nodes.

This is the phase that produces cross-document insight — the aha moment.

#### Context Assembly

```python
async def assemble_integration_context(project, new_nodes, max_context_nodes=30):
    """
    Build the context for the integration LLM call.
    For small graphs, include everything.
    For large graphs, include only semantically relevant existing nodes.
    """
    existing_nodes = Node.objects.filter(
        project=project, scope="project"
    ).exclude(
        id__in=[n.id for n in new_nodes]
    )

    total_existing = existing_nodes.count()

    if total_existing <= max_context_nodes:
        # Small graph: send everything
        context_nodes = list(existing_nodes)
    else:
        # Large graph: find relevant existing nodes via embedding similarity
        context_nodes = []
        for new_node in new_nodes:
            if new_node.embedding:
                similar = find_similar_nodes(
                    new_node.embedding, existing_nodes,
                    threshold=0.6, top_k=5
                )
                context_nodes.extend(similar)
        # Deduplicate and cap
        context_nodes = list({n.id: n for n in context_nodes}.values())[:max_context_nodes]

    # Also include all existing edges between context nodes
    context_node_ids = [n.id for n in context_nodes]
    context_edges = Edge.objects.filter(
        source_node_id__in=context_node_ids,
        target_node_id__in=context_node_ids
    )

    return context_nodes, list(context_edges), total_existing
```

#### Integration Prompt Strategy

```
System: You are integrating new knowledge into an existing reasoning graph.

EXISTING GRAPH ({total_existing} nodes total, {shown} shown):
{serialized existing nodes and edges}

NEW NODES (just extracted from "{document_title}"):
{serialized new nodes with IDs}

Your job:
1. EDGES: For each new node, determine if it supports, contradicts, or
   depends on any existing node. Create edges ONLY when the relationship
   is clear and meaningful. Don't force connections.

2. TENSIONS: When you find a genuine contradiction (new evidence vs. existing
   claim, or two claims that can't both be true), create a Tension node.
   Be conservative — only flag real contradictions, not minor differences.

3. STATUS UPDATES: If new evidence strongly supports or contradicts an
   existing assumption, recommend a status change.

4. GAPS: Note any important topics the new document addresses that the
   existing graph has NO coverage of (these become unsubstantiated claims
   or untested assumptions).

Rules:
- Be conservative with contradictions. "Different emphasis" is not a
  contradiction. "X says growth is 28%, Y says growth is 12%" IS.
- Don't create edges just because two nodes mention the same topic.
  The relationship must be substantive.
- When creating a tension, explain specifically what the conflict is
  and why it matters.

Output format:
{
    "edges": [
        {
            "type": "supports" | "contradicts" | "depends_on",
            "source_node_id": "uuid (new or existing)",
            "target_node_id": "uuid (new or existing)",
            "strength": 0.0-1.0,
            "provenance": "why this relationship exists"
        }
    ],
    "tensions": [
        {
            "content": "description of the contradiction",
            "severity": "high" | "medium" | "low",
            "between_nodes": ["uuid-1", "uuid-2"],
            "description": "why these conflict and why it matters"
        }
    ],
    "status_updates": [
        {
            "node_id": "uuid of existing node",
            "new_status": "challenged" | "supported" | etc.,
            "reason": "why the status should change"
        }
    ],
    "gaps": [
        {
            "content": "topic or question not covered in existing graph",
            "type": "claim" | "assumption",
            "reasoning": "why this gap matters"
        }
    ],
    "delta_narrative": "2-3 sentence summary of what this document changes
                        about the project's knowledge landscape. Focus on
                        what's NEW, what's CHALLENGED, and what's still MISSING."
}
```

#### Integration Execution

```python
async def integrate_with_graph(project, document, new_nodes, integration_result):
    """Phase B: Create edges, tensions, and status updates from integration."""
    created_edges = []
    created_tensions = []
    status_changes = []

    # 1. Create edges
    for edge_data in integration_result["edges"]:
        edge = Edge.objects.create(
            type=edge_data["type"],
            source_node_id=edge_data["source_node_id"],
            target_node_id=edge_data["target_node_id"],
            strength=edge_data.get("strength"),
            provenance=edge_data["provenance"],
            source_type="integration",
            source_document=document,
        )
        created_edges.append(edge)

    # 2. Create tension nodes
    for tension_data in integration_result["tensions"]:
        tension = Node.objects.create(
            type="tension",
            status="surfaced",
            content=tension_data["content"],
            properties={
                "tension_type": "contradiction",
                "severity": tension_data["severity"],
                "between_nodes": tension_data["between_nodes"],
                "description": tension_data["description"],
            },
            project=project,
            scope="project",
            source_type="integration",
            source_document=document,
        )
        # Create edges from tension to the conflicting nodes
        for node_id in tension_data["between_nodes"]:
            Edge.objects.create(
                type="contradicts",
                source_node=tension,
                target_node_id=node_id,
                source_type="integration",
                source_document=document,
                provenance=tension_data["description"],
            )
        created_tensions.append(tension)

    # 3. Apply status updates
    for update in integration_result.get("status_updates", []):
        node = Node.objects.get(id=update["node_id"])
        old_status = node.status
        node.status = update["new_status"]
        node.save()
        status_changes.append({
            "node_id": str(node.id),
            "from": old_status,
            "to": update["new_status"],
            "reason": update["reason"],
        })

    # 4. Create gap nodes
    for gap in integration_result.get("gaps", []):
        Node.objects.create(
            type=gap.get("type", "claim"),
            status="unsubstantiated",
            content=gap["content"],
            properties={"gap_reasoning": gap["reasoning"]},
            project=project,
            scope="project",
            source_type="integration",
            source_document=document,
        )

    # 5. Mark document complete
    document.extraction_status = "completed"
    document.save()

    # 6. Generate and store delta
    delta = GraphDelta.objects.create(
        project=project,
        trigger="document_upload",
        source_document=document,
        narrative=integration_result.get("delta_narrative", ""),
        nodes_created=len(new_nodes) + len(created_tensions),
        edges_created=len(created_edges),
        tensions_surfaced=len(created_tensions),
        assumptions_challenged=len([s for s in status_changes if s["to"] == "challenged"]),
        patch={"changes": [...]},  # Build from above operations
    )

    return delta
```

### Full Pipeline Orchestration

```python
# Celery task
@shared_task
def process_document_to_graph(document_id, project_id):
    """
    Full pipeline: preprocess → extract → integrate → delta.
    Called after document upload and chunking completes.
    """
    document = Document.objects.get(id=document_id)
    project = Project.objects.get(id=project_id)

    try:
        # Phase A: Extract nodes from document
        document.extraction_status = "extracting"
        document.save()

        extraction_result = await run_extraction_llm(
            document_text=document.content_text,
            document_title=document.title,
        )
        new_nodes = await create_nodes_from_extraction(
            project, document, extraction_result
        )

        # Phase B: Integrate with existing graph
        document.extraction_status = "integrating"
        document.save()

        context_nodes, context_edges, total = await assemble_integration_context(
            project, new_nodes
        )
        integration_result = await run_integration_llm(
            new_nodes=new_nodes,
            existing_nodes=context_nodes,
            existing_edges=context_edges,
            document_title=document.title,
            total_existing=total,
        )
        delta = await integrate_with_graph(
            project, document, new_nodes, integration_result
        )

        # Emit event for real-time UI update
        emit_event(
            type="DOCUMENT_GRAPH_INTEGRATED",
            project_id=project_id,
            payload={"document_id": str(document_id), "delta_id": str(delta.id)},
        )

    except Exception as e:
        document.extraction_status = "failed"
        document.extraction_error = str(e)
        document.save()
        raise
```

### Context Window Management

| Project Size | Phase A Context | Phase B Context | Strategy |
|-------------|-----------------|-----------------|----------|
| First document | Full doc text | No existing graph | Extraction only, skip integration |
| 2-5 documents | Full doc text | Full graph (all nodes + edges) | Send everything |
| 6-15 documents | Full doc text | Full graph summary + all nodes | May truncate edge details |
| 15+ documents | Full doc or summary | Graph summary + top-K similar nodes per new node | Embedding similarity matching |

**Context budget rule:** Phase A gets ~80% of context for the document. Phase B splits context 40/60 between new nodes and existing graph. If the existing graph is too large, the document summary + embedding similarity provides adequate context.

### LLM Configuration

| Phase | Model | Why |
|-------|-------|-----|
| Phase A (Extraction) | Claude Sonnet | Good balance of quality and speed for structured extraction |
| Phase B (Integration) | Claude Sonnet | Cross-document reasoning needs strong analytical capability |
| Document Summary | Claude Haiku | Simple summarization task, speed matters |
| Chunk Embeddings | sentence-transformers (local) | Keep existing pipeline, no API cost |
| Node Embeddings | sentence-transformers (local) | Same model as chunks for consistency |

---

## Layer 3: Graph API & Orientation View

### API Endpoints

#### Graph Retrieval

```
GET /api/v2/projects/{project_id}/graph/

Returns the full project graph for rendering.

Response:
{
    "nodes": [
        {
            "id": "uuid",
            "type": "claim",
            "status": "supported",
            "content": "TAM will reach $4.2B by 2027",
            "properties": { ... },
            "source_document": { "id": "uuid", "title": "Market Report" },
            "created_at": "ISO datetime"
        },
        ...
    ],
    "edges": [
        {
            "id": "uuid",
            "type": "supports",
            "source_node_id": "uuid",
            "target_node_id": "uuid",
            "strength": 0.85,
            "provenance": "Market report provides data backing this claim"
        },
        ...
    ],
    "health": {
        "total_nodes": 24,
        "claims": 10,
        "evidence": 8,
        "assumptions": 4,
        "tensions": 2,
        "untested_assumptions": 3,
        "unsubstantiated_claims": 2,
        "active_tensions": 2
    },
    "documents": [
        { "id": "uuid", "title": "Pitch Deck", "extraction_status": "completed", "node_count": 6 },
        { "id": "uuid", "title": "Market Report", "extraction_status": "completed", "node_count": 8 }
    ]
}
```

#### Orientation View (Structured)

```
GET /api/v2/projects/{project_id}/graph/orientation/

Returns the graph organized by orientation categories — the "evidence map."
This is a DERIVED VIEW of the same graph data, organized for the aha moment.

Response:
{
    "agreements": [
        {
            "theme": "Market size is large and growing",
            "nodes": [ ...claims supported by multiple documents... ],
            "supporting_evidence": [ ...evidence nodes... ],
            "document_count": 3
        }
    ],
    "contradictions": [
        {
            "tension": { ...tension node... },
            "side_a": { "node": { ...claim... }, "evidence": [...], "documents": [...] },
            "side_b": { "node": { ...claim... }, "evidence": [...], "documents": [...] },
            "severity": "high"
        }
    ],
    "hidden_assumptions": [
        {
            "node": { ...assumption node... },
            "depends_on_by": [ ...nodes that rely on this assumption... ],
            "evidence_count": 0,
            "load_bearing": true
        }
    ],
    "gaps": [
        {
            "description": "No documents address unit economics",
            "related_nodes": [ ...nodes that reference this topic tangentially... ]
        }
    ],
    "delta_since_last_visit": {
        "narrative": "Since your last visit, 1 new document was processed...",
        "new_tensions": 1,
        "assumptions_challenged": 2
    }
}
```

#### Document Upload

```
POST /api/v2/projects/{project_id}/documents/

Accepts file upload. Triggers preprocessing → extraction → integration pipeline.
Returns immediately with document ID; processing happens async.

Response:
{
    "id": "uuid",
    "title": "Market Report Q4 2025",
    "extraction_status": "pending",
    "message": "Document uploaded. Processing will begin shortly."
}
```

#### Document Delta

```
GET /api/v2/projects/{project_id}/documents/{document_id}/delta/

Returns what this specific document changed in the project graph.

Response:
{
    "document": { "id": "uuid", "title": "..." },
    "delta": {
        "narrative": "This document challenged your growth assumptions...",
        "nodes_created": 7,
        "edges_created": 4,
        "tensions_surfaced": 1,
        "assumptions_challenged": 2,
        "details": {
            "confirmed": [ { "node": {...}, "reason": "..." } ],
            "challenged": [ { "node": {...}, "reason": "..." } ],
            "new_tensions": [ { "tension": {...}, "between": [...] } ],
            "new_information": [ { "node": {...} } ]
        }
    }
}
```

#### Node Detail

```
GET /api/v2/projects/{project_id}/nodes/{node_id}/

Returns full node detail including provenance and connections.

Response:
{
    "node": { ...full node data... },
    "connections": {
        "supports": [ { "edge": {...}, "connected_node": {...} } ],
        "contradicts": [ { "edge": {...}, "connected_node": {...} } ],
        "depends_on": [ { "edge": {...}, "connected_node": {...} } ],
        "supported_by": [ { "edge": {...}, "connected_node": {...} } ],
        "contradicted_by": [ { "edge": {...}, "connected_node": {...} } ],
    },
    "provenance": {
        "source_type": "document_extraction",
        "document": { "id": "uuid", "title": "..." },
        "source_passage": "exact text from document",
        "chunks": [ { "id": "uuid", "text": "..." } ]
    }
}
```

### Frontend: Orientation View (v1)

For v1, the orientation view is a **structured card-based layout**, not a full graph visualization. This is faster to build and delivers the aha moment more directly than a node-edge diagram.

The graph data powers this view, but the rendering is organized by cognitive category:

```
┌─────────────────────────────────────────────────────────────────┐
│  PROJECT: "Our Startup's Technical Direction"                   │
│  5 documents · 24 nodes · 4 assumptions · 2 tensions            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ⚡ CONTRADICTIONS (2)                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Growth rate: Pitch deck says 28% ←→ Market report      │    │
│  │ says 12%. HIGH severity.                                │    │
│  │ [Pitch Deck §3] vs [Market Report §2.1]                │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Competitive landscape: Pitch deck claims "no direct     │    │
│  │ competitors" ←→ Research doc lists 3 competitors.       │    │
│  │ [Pitch Deck §1] vs [Competitor Analysis §1]            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  🔍 HIDDEN ASSUMPTIONS (4)                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ⚠ "Distribution partner will renew" — load-bearing,    │    │
│  │   zero evidence. Options A and B depend on this.        │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ⚠ "Regulatory approval takes <12 months" — untested,   │    │
│  │   no documents address timeline.                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ...                                                            │
│                                                                 │
│  ✅ AGREEMENTS (3 themes)                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Market size is substantial — supported by 3 documents.  │    │
│  │ [Market Report] [Industry Analysis] [Pitch Deck]       │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ...                                                            │
│                                                                 │
│  ❓ GAPS                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ No documents address unit economics.                    │    │
│  │ No documents address customer acquisition cost.         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ─── Chat ──────────────────────────────────────────────────    │
│  │ User: "Tell me more about the growth rate contradiction" │    │
│  │ Agent: "Your pitch deck in §3 claims annual growth of   │    │
│  │ 28%, citing internal projections. However, the Q4 market│    │
│  │ report from Gartner shows the segment growing at 12%.   │    │
│  │ This is a high-severity tension because your financial  │    │
│  │ projections depend on the 28% figure..."                │    │
│  └──────────────────────────────────────────────────────────    │
└─────────────────────────────────────────────────────────────────┘
```

#### Frontend Architecture

- **Framework:** Next.js 14 (existing), React 18, TypeScript, Tailwind
- **State management:** React Query for graph data (auto-refetch on document processing completion)
- **Real-time updates:** Poll `/api/v2/projects/{id}/graph/` while documents are processing (SSE in future)
- **Layout:** Two-panel — orientation map (left/main) + chat (right/collapsible)

#### Key Components

```
ProjectPage
├── OrientationMap                    # Main structured view
│   ├── GraphHealthBar                # "5 docs · 24 nodes · 4 assumptions · 2 tensions"
│   ├── ContradictionsSection         # Highest visual priority — the aha moment
│   │   └── TensionCard              # Shows both sides with source provenance
│   ├── HiddenAssumptionsSection      # Amber/warning treatment
│   │   └── AssumptionCard           # Shows load-bearing status, evidence count
│   ├── AgreementsSection             # Green/confirmed treatment
│   │   └── ThemeCard                # Groups related supported claims
│   └── GapsSection                   # Gray/unknown treatment
│       └── GapCard                  # What's missing
├── DocumentList                      # Uploaded documents with extraction status
│   └── DocumentCard                 # Title, status badge, node count
├── ChatPanel                         # Conversational editing (Layer 4)
│   └── GraphAwareChat               # Same chat, but agent has graph context
└── NodeDetailDrawer                  # Slide-out when clicking a node reference
    ├── NodeContent                   # Full content with provenance
    ├── ConnectionsList               # What this node connects to
    └── SourcePassage                 # Highlighted text from source document
```

#### Visual Treatment by Category

| Category | Color | Icon | Priority |
|----------|-------|------|----------|
| Contradictions | Red/Rose | ⚡ Lightning | Highest — shown first |
| Hidden Assumptions | Amber/Yellow | ⚠ Warning | High — untested bets |
| Agreements | Green/Emerald | ✓ Check | Medium — confirmed knowledge |
| Gaps | Gray/Slate | ? Question | Lower — absence of information |

#### Graph Visualization (v1.1 — NOT v1)

The card-based orientation map is v1. A visual graph (React Flow) is v1.1 — added once the card view proves the value. When added, it's just another rendering of the same graph API data:

```
GET /api/v2/projects/{project_id}/graph/  →  Card-based orientation map (v1)
                                          →  React Flow DAG visualization (v1.1)
                                          →  Brief/summary projection (future)
```

Same state, different lenses. The API doesn't change.

---

## Layer 4: Conversational Editing

The user sees the orientation map and can converse with an agent that understands the graph. The agent can make structural edits — creating, updating, or removing nodes and edges.

### Agent Context

Every message to the agent includes the current graph state:

```python
def build_agent_context(project_id, user_message):
    """Build context for the conversational editing agent."""
    graph = get_project_graph(project_id)  # Nodes + edges
    health = get_graph_health(project_id)

    return {
        "system_prompt": GRAPH_AGENT_SYSTEM_PROMPT,
        "graph_context": serialize_graph_for_llm(graph, health),
        "user_message": user_message,
    }
```

### Agent System Prompt

```
You are the Episteme agent. You understand a project's reasoning graph —
its claims, evidence, assumptions, and tensions — and you help users
make sense of their documents and thinking.

CURRENT GRAPH STATE:
{serialized graph — nodes with types/statuses, edges with types}

GRAPH HEALTH:
{health summary — counts, untested assumptions, active tensions}

YOUR CAPABILITIES:
1. Answer questions about the graph (what's known, what's contested, etc.)
2. Make structural edits when the user's message implies a change:
   - Create new nodes (claims, evidence, assumptions)
   - Create new edges (supports, contradicts, depends_on)
   - Update node statuses
   - Create tension nodes when contradictions are identified
   - Remove nodes the user says are wrong or irrelevant

WHEN TO EDIT:
- User states a new fact or belief → create node
- User says something supports or contradicts existing knowledge → create edge
- User challenges an existing node → update status or create tension
- User says "that's not right" about a node → update or remove
- User asks "what am I missing?" → analyze graph for gaps, create gap nodes

WHEN NOT TO EDIT:
- User asks a question → answer from graph context, don't create nodes
- User is just discussing → respond conversationally

OUTPUT FORMAT:
Always respond with a conversational message. If you also made structural
edits, include them in a structured block:

<graph_edits>
{
    "edits": [
        { "action": "create_node", "type": "assumption", "content": "...",
          "status": "untested", "properties": { "load_bearing": true, "implicit": false } },
        { "action": "create_edge", "type": "depends_on",
          "source": "new-0", "target": "existing-uuid",
          "provenance": "..." },
        { "action": "update_node", "id": "uuid", "status": "challenged",
          "reason": "..." },
        { "action": "remove_node", "id": "uuid", "reason": "..." }
    ],
    "delta_narrative": "What changed and why"
}
</graph_edits>

IMPORTANT:
- Reference "new-0", "new-1" etc. for nodes you're creating in the same
  edit batch (so edges can reference them before they have real IDs).
- Always explain edits in the conversational response. Don't silently
  modify the graph.
- The delta_narrative should be 1-2 sentences focused on IMPACT, not just
  what was added.
```

### Edit Processing

```python
async def process_chat_with_graph_edits(project_id, thread_id, user_message, user):
    """
    Process a user message that may include graph edits.
    1. Build context with current graph
    2. Get LLM response (conversational + optional edits)
    3. Apply any structural edits
    4. Generate delta
    5. Return response + delta
    """
    # 1. Build context
    context = build_agent_context(project_id, user_message)

    # 2. Get LLM response
    response = await call_llm(context)
    conversational_reply, edits_block = parse_response(response)

    # 3. Save message
    message = save_assistant_message(thread_id, conversational_reply)

    # 4. Apply edits if present
    if edits_block:
        new_node_map = {}  # "new-0" → actual UUID

        for edit in edits_block["edits"]:
            if edit["action"] == "create_node":
                node = Node.objects.create(
                    type=edit["type"],
                    status=edit["status"],
                    content=edit["content"],
                    properties=edit.get("properties", {}),
                    project_id=project_id,
                    scope="project",
                    source_type="chat",
                    source_message=message,
                    created_by=user,
                )
                node.embedding = await generate_embedding(node.content)
                node.save()
                ref = f"new-{len(new_node_map)}"
                new_node_map[ref] = node.id

            elif edit["action"] == "create_edge":
                source_id = new_node_map.get(edit["source"], edit["source"])
                target_id = new_node_map.get(edit["target"], edit["target"])
                Edge.objects.create(
                    type=edit["type"],
                    source_node_id=source_id,
                    target_node_id=target_id,
                    provenance=edit.get("provenance", ""),
                    source_type="chat",
                    created_by=user,
                )

            elif edit["action"] == "update_node":
                Node.objects.filter(id=edit["id"]).update(
                    status=edit["status"],
                    updated_at=timezone.now(),
                )

            elif edit["action"] == "remove_node":
                # Soft delete or actual delete — for v1, actual delete is fine
                # Edges cascade
                Node.objects.filter(id=edit["id"]).delete()

        # 5. Generate delta
        GraphDelta.objects.create(
            project_id=project_id,
            trigger="chat_edit",
            source_message=message,
            narrative=edits_block.get("delta_narrative", ""),
            nodes_created=len([e for e in edits_block["edits"] if e["action"] == "create_node"]),
            edges_created=len([e for e in edits_block["edits"] if e["action"] == "create_edge"]),
            patch=edits_block,
        )

    return conversational_reply, edits_block
```

### Interaction Patterns

| User Says | Agent Does |
|-----------|-----------|
| "I uploaded 3 documents about our market" | Documents process through pipeline. Agent responds with orientation summary once extraction completes. |
| "Tell me more about the growth rate contradiction" | Reads tension node + connected evidence. Responds with detailed explanation citing source documents. No edits. |
| "Actually, the pitch deck number was updated — growth is now 15%" | Updates the claim node content/status. Checks if tension is still valid (12% vs 15% — still a gap). Updates delta. |
| "I think we're also assuming that enterprise deals close in < 90 days" | Creates assumption node (untested, load_bearing: true). Creates depends_on edges to relevant claims. |
| "That assumption about regulatory timeline isn't relevant to us" | Removes the node. Cleans up edges. Explains what changed. |
| "What am I missing?" | Runs gap analysis on graph. Surfaces: nodes with no evidence, topics not covered, assumptions with no testing path. May create gap nodes. |
| "Show me everything that depends on the partner renewal assumption" | Traverses graph from that assumption via depends_on edges. Lists all connected claims and evidence. No edits. |

---

## Implementation Sequence

### Sprint 1: Foundation (Backend)
1. Create `graph` Django app with Node, Edge, GraphDelta models
2. Write migrations
3. Implement basic graph CRUD service (create_node, create_edge, get_project_graph)
4. Implement graph health computation
5. Create API endpoints: graph retrieval, node detail

### Sprint 2: Extraction Pipeline (Backend)
1. Implement Phase A: document extraction prompt + node creation
2. Implement chunk-to-node provenance mapping
3. Implement Phase B: graph integration prompt + edge/tension creation
4. Implement delta generation
5. Wire into existing document upload flow (after chunking → trigger extraction)
6. Create document upload API endpoint with extraction status

### Sprint 3: Orientation View (Frontend)
1. Build ProjectPage with OrientationMap layout
2. Build category sections: Contradictions, Hidden Assumptions, Agreements, Gaps
3. Build NodeDetailDrawer with provenance display
4. Build DocumentList with extraction status indicators
5. Build GraphHealthBar
6. Wire polling for real-time updates during document processing

### Sprint 4: Conversational Editing (Full Stack)
1. Build graph-aware agent prompt with serialized graph context
2. Implement edit parsing from LLM response
3. Implement edit application (create/update/remove nodes and edges)
4. Wire chat panel into ProjectPage
5. Build delta display (toast/notification showing what changed after edits)

### Sprint 5: Polish & Testing
1. Test multi-document extraction with real documents
2. Tune extraction prompts (precision vs. recall)
3. Tune integration prompts (false contradiction rate)
4. Handle edge cases: empty projects, single document, very large documents
5. Performance: graph query optimization, embedding generation batching
6. Error handling: failed extractions, partial integration, LLM timeouts

---

## What's Explicitly Deferred

Everything below is architecturally supported by the graph model but NOT built in v1:

| Feature | Why Deferred | When |
|---------|-------------|------|
| Cases | Need to prove orientation value first | v2 |
| Decision mode | Requires Options, Focus nodes | v2 |
| Readiness gating | Requires case-level governance | v2 |
| Plan generation | Requires blocker detection from case graph | v2 |
| Brief generation | Requires case-level synthesis | v2 |
| React Flow graph viz | Card view delivers aha moment faster | v1.1 |
| Skills system | Not needed for core loop | v3+ |
| Multi-agent orchestration | Single agent sufficient for v1 | v3+ |
| Post-decision review | Requires commitment flow | v3+ |
| Team collaboration | Single user first | v3+ |

---

## Success Criteria

V1 is successful when:

1. **A user uploads 3-5 documents and immediately sees tensions they didn't know existed.** The contradiction detection is the primary value test.
2. **Hidden assumptions surface that the user recognizes as real but hadn't articulated.** The implicit assumption extraction is the trust-building moment.
3. **The user can converse with the agent about the graph and the agent's responses demonstrate structural understanding** — not just keyword matching but genuine awareness of how claims relate.
4. **Document deltas feel meaningful.** "This document challenged 2 assumptions" tells the user something they couldn't have known without the system.
5. **The orientation map is useful enough that the user returns to add more documents** — the graph gets smarter with each upload and the user can see that.

If these five things work, cases and decision mode follow naturally. If they don't, no amount of additional features will save the product.

---

## Appendix A: Status-Type Validation

The LLM extraction can produce invalid status/type combinations. Enforce at the model level:

```python
VALID_STATUSES_BY_TYPE = {
    "claim": {"supported", "contested", "unsubstantiated"},
    "evidence": {"confirmed", "uncertain", "disputed"},
    "assumption": {"untested", "assumption_confirmed", "challenged", "refuted"},
    "tension": {"surfaced", "acknowledged", "resolved"},
}

class Node(models.Model):
    # ... fields as defined above ...

    def clean(self):
        valid = VALID_STATUSES_BY_TYPE.get(self.type, set())
        if self.status not in valid:
            raise ValidationError(
                f"Status '{self.status}' is not valid for node type '{self.type}'. "
                f"Valid statuses: {valid}"
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
```

Apply the same validation before creating nodes from LLM output — reject or remap invalid combinations rather than storing them.

---

## Appendix B: Async/Sync Pattern

The pipeline uses **synchronous Celery tasks** for orchestration, with `sync_to_async`/`async_to_sync` bridges only for LLM API calls. This matches the existing codebase pattern.

```python
from asgiref.sync import async_to_sync
from celery import shared_task

@shared_task
def process_document_to_graph(document_id, project_id):
    """Synchronous Celery task. LLM calls use async_to_sync bridge."""
    document = Document.objects.get(id=document_id)
    project = Project.objects.get(id=project_id)

    try:
        document.extraction_status = "extracting"
        document.save()

        # Phase A — sync wrapper around async LLM call
        extraction_result = async_to_sync(run_extraction_llm)(
            document_text=document.content_text,
            document_title=document.title,
        )
        new_nodes = create_nodes_from_extraction(project, document, extraction_result)

        # Phase B
        document.extraction_status = "integrating"
        document.save()

        context_nodes, context_edges, total = assemble_integration_context(project, new_nodes)
        integration_result = async_to_sync(run_integration_llm)(
            new_nodes=new_nodes,
            existing_nodes=context_nodes,
            existing_edges=context_edges,
            document_title=document.title,
            total_existing=total,
        )
        delta = integrate_with_graph(project, document, new_nodes, integration_result)

        emit_event("DOCUMENT_GRAPH_INTEGRATED", project_id=project_id,
                    payload={"document_id": str(document_id), "delta_id": str(delta.id)})

    except Exception as e:
        document.extraction_status = "failed"
        document.extraction_error = str(e)
        document.save()
        # Don't re-raise — log and allow manual retry
        logger.exception(f"Document graph processing failed: {document_id}")
```

**Rule:** All service functions (create_nodes_from_extraction, integrate_with_graph, assemble_integration_context) are **synchronous**. Only the raw LLM API calls (`run_extraction_llm`, `run_integration_llm`) are async (because the LLM client libraries use async HTTP). Bridge them with `async_to_sync` at the call site.

---

## Appendix C: Error Handling & Partial Failure

### Extraction Status State Machine

```
pending → extracting → integrating → completed
    │          │              │
    └──────────┴──────────────┴───→ failed (with extraction_error detail)
```

**Failure granularity:** The `extraction_error` field stores which phase failed:

```python
document.extraction_error = json.dumps({
    "phase": "extraction" | "integration",
    "error": str(e),
    "partial_nodes_created": len(new_nodes) if phase == "integration" else 0,
    "timestamp": timezone.now().isoformat(),
})
```

### Phase A Failure

If extraction fails, no nodes have been created yet (extraction creates them atomically). Mark document as failed. User can retry — the task is idempotent.

### Phase B Failure

If integration fails AFTER nodes were created in Phase A, those nodes exist but have no cross-document edges. This is acceptable — the nodes from the document are valid, they just aren't integrated yet.

```python
# Phase B wraps edge/tension creation in a transaction
from django.db import transaction

def integrate_with_graph(project, document, new_nodes, integration_result):
    with transaction.atomic():
        # All edge creation, tension creation, and status updates
        # happen atomically. If any fails, all roll back.
        ...

    # Delta generation happens OUTSIDE the transaction
    # (it's a record of what happened, not part of the mutation)
    delta = GraphDelta.objects.create(...)
    return delta
```

**Retry strategy:** A failed Phase B can be retried without re-running Phase A. The task checks extraction_status:
- If `extracting` + has nodes → Phase A completed but status wasn't updated. Skip to Phase B.
- If `integrating` → Phase B failed. Delete any partial edges from this document, re-run Phase B.
- If `failed` → Check `extraction_error.phase` to determine which phase to retry.

### LLM Output Validation

```python
def validate_extraction_output(result: dict) -> dict:
    """Validate and sanitize LLM extraction output."""
    validated_nodes = []
    for node_data in result.get("nodes", []):
        # Require type and content
        if not node_data.get("type") or not node_data.get("content"):
            continue

        # Validate type
        if node_data["type"] not in VALID_STATUSES_BY_TYPE:
            continue

        # Validate or fix status
        valid_statuses = VALID_STATUSES_BY_TYPE[node_data["type"]]
        if node_data.get("status") not in valid_statuses:
            # Default status by type
            node_data["status"] = {
                "claim": "unsubstantiated",
                "evidence": "uncertain",
                "assumption": "untested",
                "tension": "surfaced",
            }[node_data["type"]]

        validated_nodes.append(node_data)

    result["nodes"] = validated_nodes
    return result
```

### Edit Validation (Conversational Editing)

```python
def validate_and_apply_edits(edits_block: dict, project_id: uuid) -> tuple[list, list]:
    """
    Validate agent edits before applying. Returns (applied, rejected).
    """
    applied, rejected = [], []

    for edit in edits_block.get("edits", []):
        try:
            if edit["action"] == "create_node":
                # Validate type-status combination
                valid = VALID_STATUSES_BY_TYPE.get(edit.get("type"), set())
                if edit.get("status") not in valid:
                    edit["status"] = list(valid)[0]  # Default to first valid status
                applied.append(edit)

            elif edit["action"] == "create_edge":
                # Verify referenced nodes exist (or are in new_node_map)
                # Skip edges to non-existent nodes
                applied.append(edit)

            elif edit["action"] in ("update_node", "remove_node"):
                # Verify node exists and belongs to this project
                if not Node.objects.filter(id=edit["id"], project_id=project_id).exists():
                    rejected.append({"edit": edit, "reason": "Node not found in project"})
                    continue
                applied.append(edit)

        except (KeyError, ValueError) as e:
            rejected.append({"edit": edit, "reason": str(e)})

    return applied, rejected
```

---

## Appendix D: Core Helper Functions

### Graph Serialization for LLM Context

```python
def serialize_graph_for_llm(project_id: uuid, max_nodes: int = 50) -> str:
    """
    Serialize project graph into a compact text format for LLM context.
    Returns a string representation that fits in ~4000 tokens.
    """
    nodes = (
        Node.objects
        .filter(project_id=project_id, scope="project")
        .select_related("source_document")
        .order_by("-updated_at")[:max_nodes]
    )

    edges = (
        Edge.objects
        .filter(source_node__project_id=project_id)
        .select_related("source_node", "target_node")
    )

    lines = ["GRAPH STATE:"]
    lines.append(f"Total: {nodes.count()} nodes\n")

    # Group by type
    for node_type in ["claim", "evidence", "assumption", "tension"]:
        typed = [n for n in nodes if n.type == node_type]
        if typed:
            lines.append(f"## {node_type.upper()}S ({len(typed)})")
            for n in typed:
                src = f" [from: {n.source_document.title}]" if n.source_document else ""
                lines.append(f"  [{n.id}] ({n.status}) {n.content[:150]}{src}")
            lines.append("")

    if edges:
        lines.append(f"## RELATIONSHIPS ({edges.count()})")
        for e in edges:
            lines.append(f"  {e.source_node.content[:60]} --{e.type}--> {e.target_node.content[:60]}")

    return "\n".join(lines)
```

### Embedding Generation

```python
from sentence_transformers import SentenceTransformer

# Load once at module level
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def generate_embedding(text: str) -> list[float]:
    """Generate a 384-dim embedding vector. Synchronous."""
    model = get_embedding_model()
    return model.encode(text).tolist()


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch embedding generation. More efficient for multiple texts."""
    model = get_embedding_model()
    return model.encode(texts).tolist()
```

### Similarity Search (pgvector)

```python
from pgvector.django import CosineDistance

def find_similar_nodes(
    query_embedding: list[float],
    queryset=None,
    project_id: uuid = None,
    threshold: float = 0.6,
    top_k: int = 10,
) -> list[Node]:
    """Find nodes similar to query embedding using pgvector cosine distance."""
    if queryset is None:
        queryset = Node.objects.filter(project_id=project_id, scope="project")

    return (
        queryset
        .exclude(embedding__isnull=True)
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .filter(distance__lt=(1 - threshold))  # cosine distance = 1 - similarity
        .order_by("distance")[:top_k]
    )
```

### LLM Call Wrappers

```python
import anthropic

client = anthropic.AsyncAnthropic()  # Uses ANTHROPIC_API_KEY env var


async def run_extraction_llm(document_text: str, document_title: str) -> dict:
    """
    Phase A: Extract claims, evidence, and assumptions from a document.
    Returns validated JSON with nodes list and document summary.
    """
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Document: {document_title}\n\n{document_text[:80000]}"
        }],
    )

    result = parse_json_from_response(response.content[0].text)
    return validate_extraction_output(result)


async def run_integration_llm(
    new_nodes: list[Node],
    existing_nodes: list[Node],
    existing_edges: list[Edge],
    document_title: str,
    total_existing: int,
) -> dict:
    """
    Phase B: Integrate new nodes with existing graph.
    Returns edges, tensions, status updates, gaps, and delta narrative.
    """
    context = format_integration_context(
        new_nodes, existing_nodes, existing_edges, total_existing
    )

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=INTEGRATION_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"New document: {document_title}\n\n{context}"
        }],
    )

    return parse_json_from_response(response.content[0].text)


def parse_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    import json, re
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}...")
```

---

## Appendix E: pgvector Setup

Required for embedding similarity search. Set up once during initial deployment.

```sql
-- PostgreSQL extension (requires superuser or rds_superuser)
CREATE EXTENSION IF NOT EXISTS vector;
```

```python
# Django migration
from django.db import migrations
from pgvector.django import VectorExtension

class Migration(migrations.Migration):
    operations = [
        VectorExtension(),  # Creates the extension
        # ... then create Node table with VectorField
    ]
```

```
# requirements.txt additions
pgvector>=0.3.0
django-pgvector>=0.1.0
sentence-transformers>=2.2.0
```

**Index for similarity search** (add after table has data):

```sql
-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX idx_node_embedding ON graph_node
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```
