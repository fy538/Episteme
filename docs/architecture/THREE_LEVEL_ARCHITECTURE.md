# Three-Level Architecture

How Project, Chat, and Case work together — the master technical overview.

---

## Overview

Episteme implements a three-level architecture that mirrors natural cognitive progression:

```
PROJECT (Orientation)     "What's the landscape?"
    │
    ▼
CHAT (Exploration)        "What should I be thinking about?"
    │
    ▼
CASE (Investigation)      "Let me get this specific decision right."
```

Each level has its own data structures, services, and AI capabilities. Data flows between levels — documents feed projects, conversations inform cases, and investigation results accumulate back into projects.

---

## The Technical Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5.x, ASGI, PostgreSQL with pgvector |
| **Async tasks** | Celery + Redis |
| **AI framework** | PydanticAI with structured tool-based extraction |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2, 384-dim) |
| **API** | Django REST Framework with JWT auth |
| **Frontend** | Next.js 14, React 18, TypeScript 5.4 |
| **Graph visualization** | @xyflow/react 12.10 (ReactFlow) + elkjs for layout |
| **Editor** | Tiptap 2.2 |
| **Data fetching** | @tanstack/react-query 5.28 |
| **Streaming** | Server-Sent Events (SSE) with sectioned XML parsing |
| **Monitoring** | Sentry, structured JSON logging with correlation IDs |

---

## Level 1: Project — Orientation

### What It Does

Projects are long-lived containers for a domain of concern. Users upload documents; the system builds a hierarchical theme map that reveals what the documents cover, where they agree, and what they never address.

### Data Model

```
Project
  ├── Documents → DocumentChunks (with embeddings, 384-dim pgvector)
  ├── ClusterHierarchy (multi-level cluster tree)
  ├── ProjectSummary (versioned AI summaries)
  └── ProjectInsight (agent-discovered observations)
```

### Hierarchical Clustering (Plan 1)

RAPTOR-style recursive agglomerative clustering:

```
Level 0 (Leaves):   Raw DocumentChunks with embeddings
    ↓ agglomerative clustering (cosine distance, threshold 0.65)
Level 1 (Topics):   10-30 topic clusters with LLM-generated labels + summaries
    ↓ agglomerative clustering (threshold 0.55)
Level 2 (Themes):   3-7 theme super-clusters with LLM summaries
    ↓ single root
Level 3 (Root):     Project-level summary
```

**Key service:** `HierarchicalClusteringService.build_hierarchy(project_id)`

- Uses sklearn AgglomerativeClustering with cosine distance
- Orphan chunks assigned to nearest cluster
- LLM summaries generated in parallel (max 5 concurrent)
- Embeddings computed for each cluster node for similarity search
- Output stored as `ClusterHierarchy` JSON tree with `ClusterTreeNode` structure

### Project Summary (Plan 6)

AI-generated project summaries with versioned sections:
- Overview, key findings, emerging picture, attention needed, what changed
- Rebuilt when hierarchy changes (Plan 6: change detection)

### Data Flow

```
Documents uploaded
  → Chunking + embedding pipeline
    → Chunks stored with pgvector embeddings
      → Hierarchical clustering (async Celery task)
        → ClusterHierarchy stored
          → ProjectSummary generated
            → Landscape view rendered in frontend
```

---

## Level 2: Chat — Exploration

### What It Does

The organic companion agent helps users think through their situation by detecting thinking modes and building appropriate structure from conversation — decision trees, checklists, comparison frameworks, clarifying questions.

### Data Model

```
Thread (conversation container)
  ├── Messages (user + assistant, with source_chunks for RAG)
  ├── ConversationStructure (versioned, typed structures)
  └── Case references (when companion suggests investigation)
```

### Organic Companion (Plan 2)

**Key service:** `CompanionService`

The companion operates as a background structure-detection layer:

```
User message arrives
  → Chat response generated (with project context, hierarchy-aware retrieval)
    → CompanionService.update_structure() triggered (async)
      → Loads recent messages (6 for updates, 20 for creation)
        → Injects project + case context
          → LLM extracts:
            - structure_type (decision_tree, checklist, comparison, etc.)
            - content (the structured object)
            - established (confirmed reasoning)
            - open_questions (unresolved)
            - eliminated (ruled out)
            - context_summary (feeds back into next chat prompt)
              → Stored as versioned ConversationStructure
```

**Configuration:**
- Minimum 3 turns before first structure detection
- 30-second minimum interval between updates
- Maximum 5 versions kept per thread
- Structure type detected from conversation content, not user request

### Case Signal Detection

The companion detects when conversation reaches a natural investigation point:

```
CompanionService.detect_case_signal(thread_id)
  → Analyzes conversation structure for decision readiness
    → Returns signal with suggested decision question
      → Frontend shows CasePreviewCard (editable, Plan 8)
        → User edits and confirms → Case created
```

### Research Needs Detection

```
CompanionService.detect_research_needs(thread_id)
  → Identifies researchable open questions from structure
    → Triggers research agent if appropriate
```

### Data Flow

```
User sends message
  → Hierarchy-aware retrieval (project chunks, filtered by relevance)
    → Chat prompt assembled (system prompt + context + source chunks)
      → LLM response streamed via SSE
        → CompanionService.update_structure() (async)
          → ConversationStructure versioned and stored
            → Context summary injected into next chat prompt
```

---

## Level 3: Case — Investigation

### What It Does

Cases are focused investigation workspaces. A decision question serves as a lens; the system applies CEAT extraction (Claims, Evidence, Assumptions, Tensions) to produce a structured reasoning graph with assumption lifecycle tracking, blind spot detection, and readiness gating.

### Data Model

```
Case
  ├── decision_question (the focusing lens)
  ├── Node[] (claims, evidence, assumptions, tensions — with embeddings)
  ├── Edge[] (supports, contradicts, depends_on — with strength 0.0-1.0)
  ├── GraphDelta[] (mutation records with narrative summaries)
  ├── CaseNodeReference[] (visibility into project-level nodes)
  ├── DecisionRecord (Plan 9: what was decided and why)
  └── Stage progression: exploring → investigating → synthesizing → ready → decided
```

### Knowledge Graph Model

**Node types and status lifecycle:**

| Type | Statuses |
|------|---------|
| CLAIM | SUPPORTED, CONTESTED, UNSUBSTANTIATED |
| EVIDENCE | CONFIRMED, UNCERTAIN, DISPUTED |
| ASSUMPTION | UNTESTED → CONFIRMED / CHALLENGED / REFUTED |
| TENSION | SURFACED → ACKNOWLEDGED → RESOLVED |

**Edge types:** SUPPORTS, CONTRADICTS, DEPENDS_ON (with strength 0.0-1.0 and provenance tracking)

**GraphDelta:** Every mutation recorded with trigger type, narrative summary, JSON patch, and impact counters (nodes_added, edges_added, tensions_surfaced).

### CEAT Extraction (Plan 3)

**Key service:** `CaseExtractionService`

```
CaseExtractionService.extract_case_graph(case, chunks)
  → Groups chunks by document
    → Builds prompt with decision question as focusing lens
      → LLM extraction via EXTRACTION_TOOL (structured output)
        → Creates Node objects with scope='case' and 384-dim embeddings
          → Creates Edge objects with existing node awareness
            → Records GraphDelta with impact counters
```

**Incremental extraction:** `CaseExtractionService.incremental_extract(case, new_chunks, existing_nodes)` — deduplication-aware, merges new findings with existing graph.

### Blind Spot Analysis

Detects areas not addressed by current investigation:
- Compares extracted CEAT structure against expected coverage for the decision type
- Surfaces what hasn't been considered
- Informs readiness gating

### Stage Progression

Cases progress through stages based on investigation completeness:

```
exploring      → Initial document review, CEAT extraction
investigating  → Active assumption testing, evidence gathering
synthesizing   → Drawing conclusions, resolving tensions
ready          → Sufficient evidence, assumptions tested, tensions acknowledged
decided        → Decision recorded (Plan 9)
```

### Data Flow

```
Case created (from companion suggestion or manual)
  → Document chunks retrieved (project-level, filtered by case relevance)
    → CEAT extraction (async Celery task)
      → Nodes + Edges created with embeddings
        → GraphDelta recorded
          → Blind spot analysis runs
            → Readiness evaluated
              → Stage updated based on investigation completeness
```

---

## Cross-Level Data Flow

### Documents → Project → Case

```
Documents uploaded to Project
  → Chunks + embeddings stored
    → Hierarchical clustering (project-level orientation)
      → Case created with decision question
        → Relevant chunks selected for case context
          → CEAT extraction applied through decision lens
```

### Chat → Case (Companion Bridge, Plan 8)

```
Companion detects case signal
  → CasePreviewCard shown (editable: title, position, key questions, assumptions)
    → User confirms (with optional edits)
      → Case created with companion_origin metadata
        → Conversation context transferred to case
          → CEAT extraction includes companion-established reasoning
```

### Case → Decision → Outcome (Plan 9)

```
Case reaches "ready" stage
  → DecisionRecord captured (decision, reasons, confidence, caveats)
    → Linked assumptions recorded
      → Outcome check date set
        → Case status → "decided"
          → Periodic task checks for due outcome reviews
            → Outcome notes recorded → calibration data accumulated
```

### Project Knowledge Accumulation

```
Case completed → assumptions confirmed/refuted
  → Results visible at project level via CaseNodeReference
    → Next case in same project benefits from prior investigation
      → Project gets smarter with every case
```

---

## Implementation Map

| Architecture Layer | Plans | Key Services | Key Models |
|-------------------|-------|-------------|------------|
| **Project orientation** | Plan 1, 6, 7 | HierarchicalClusteringService, InsightAgent | ClusterHierarchy, ProjectSummary, ProjectInsight |
| **Chat exploration** | Plan 2, 4 | CompanionService, ChatService | Thread, Message, ConversationStructure |
| **Case investigation** | Plan 3, 5, 8 | CaseExtractionService, AnalysisService | Node, Edge, GraphDelta, Case |
| **Decision lifecycle** | Plan 9 | DecisionService | DecisionRecord, OutcomeNote |
| **Cross-cutting** | All | EventService, EmbeddingService | Event (audit trail), DocumentChunk |

---

## Key Technical Decisions

**Why pgvector over a dedicated vector DB:** PostgreSQL with pgvector keeps the entire data model in one database. Nodes, edges, chunks, and embeddings all queryable with standard SQL + vector similarity. Simplicity over performance — appropriate for the current scale.

**Why 384-dim embeddings (all-MiniLM-L6-v2):** Fast, small, good enough for semantic similarity. Runs locally without GPU. Embedding dimension matches pgvector index configuration.

**Why PydanticAI for extraction:** Structured tool-based output with type validation. CEAT extraction produces typed Node/Edge objects directly, not free-form text that needs post-processing.

**Why event sourcing for the audit trail:** Every assumption status change, evidence addition, and decision record is an immutable event. "How did we get here?" is always answerable. Foundation for future confidence calibration and decision learning.

**Why SSE streaming (not WebSockets):** Simpler to implement, debug, and deploy. Chat responses stream via sectioned XML parsing with optimistic rendering. Good enough for the current interaction model.

**Why Celery for async tasks:** Hierarchical clustering, CEAT extraction, and companion structure detection are compute-intensive. Celery + Redis provides reliable async execution with retry logic and correlation ID tracking.
