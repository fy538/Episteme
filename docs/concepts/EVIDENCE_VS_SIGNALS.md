# Evidence vs Signals: The Conceptual Model

**[V1 IMPLEMENTATION NOTE]** This conceptual model describes how Episteme distinguishes user thinking (signals) from external facts (evidence). V1 implements this via a unified Node model where every atomic unit is tracked with its source and type. As the system evolves, these distinctions enable rich graph relationships and reasoning.

---

## The Key Distinction

### Signals (User's Epistemic State)
**What:** User's thoughts, beliefs, uncertainties, assumptions
**Source:** User chat messages or conversation
**Types:** Assumption, Question, Constraint, Goal, DecisionIntent
**Purpose:** Capture what the user thinks and why
**Mutability:** User can refine (signals evolve)
**In V1:** Extracted from conversation, displayed as nodes in graph with "ungrounded" visual marker

**Examples:**
- "I assume writes are append-only"
- "What's our current p99 latency?"
- "Must ship by end of Q2"
- "We need to reduce latency to 100ms"

---

### Evidence (External Facts / Document-Sourced Claims)
**What:** Facts, data points, claims extracted from documents
**Source:** User-uploaded documents (PDFs, URLs, notes)
**Types:** Metric, Benchmark, Fact, Claim, Quote
**Purpose:** Ground user's reasoning with external sources
**Mutability:** Versioned with source document
**In V1:** Extracted from docs, displayed as nodes in graph with source citation

**Examples:**
- "System handles 50,000 requests per second" (metric, from performance_report.pdf)
- "PostgreSQL 2x faster than MongoDB for writes" (benchmark, from benchmark_study.pdf)
- "PostgreSQL supports JSONB indexing" (fact, from postgres_docs.pdf)
- "According to CTO: 'We prioritize availability'" (quote, from meeting_notes.txt)

---

## Why This Separation Matters

### Problem It Solves: Circular Extraction

**OLD (Broken):**
```
User chat: "I assume X"  
  → Signal: "Assume X"  
  
AI generates research: "The system assumes X"  
  → Signal: "Assume X" (duplicate!)  
  
Result: Noise, confusion about source
```

**NEW (Clean):**
```
User chat: "I assume X"  
  → Signal: "Assume X" (user's thought)  
  
User uploads doc: "Study shows X is true"  
  → Evidence: "Study shows X" (external fact)  
  
Link: Evidence SUPPORTS Signal  
  
Result: Clear provenance
```

---

## Data Flow

### User Chat → Signals
```
User: "We should use Postgres. I assume writes are append-only."
  ↓
Extract:
  - Signal(type=DecisionIntent): "Use Postgres"
  - Signal(type=Assumption): "Writes are append-only"
  ↓
Store with embeddings, sequence_index
```

### User Upload → Evidence
```
User uploads: "performance_benchmark.pdf"
  ↓
Chunk: 512-token chunks, recursive
  ↓
Extract from chunks:
  - Evidence(type=metric): "50k writes/sec"
  - Evidence(type=benchmark): "Postgres 2x faster"
  ↓
Link to chunks (for citation)
  ↓
Store with embeddings
```

### AI Generate → Artifact (Future: Phase 2.4)
```
User: "Generate research report"
  ↓
AI workflow:
  1. Query relevant signals (user's constraints)
  2. Query relevant evidence (facts from docs)
  3. Generate blocks with CITATIONS
  ↓
Artifact created:
  - Block 1: "Overview" (cites: user goal signal)
  - Block 2: "Performance" (cites: benchmark evidence)
  - Block 3: "Recommendation" (cites: user constraints)
  ↓
NO extraction (it's an output, not input)
```

---

## Knowledge Graph (Phase 2.3)

Once we add relationship edges:

```
Signal: "Postgres is faster"
  ↑
  [SUPPORTED_BY]
  ↑
Evidence: "Benchmark shows Postgres 2x faster"
  ↑
  [EXTRACTED_FROM]
  ↑
Chunk: "Section 3.2: Performance testing showed..."
  ↑
  [PART_OF]
  ↑
Document: "performance_benchmark.pdf"
```

**Query:** "Is this assumption grounded?"  
**Answer:** "Yes, supported by 2 evidence items from benchmarks"

---

## User Workflows

### V1 Workflow: Make Assumptions Visible

```
1. User chats: "Should we use Postgres or MongoDB?"
   → Signal(DecisionIntent) extracted as node
   → Marked as: ungrounded (no evidence yet)

2. User uploads benchmark PDF
   → Evidence(Benchmark) extracted as nodes
   → Linked: "PostgreSQL 2x faster for writes" (source: benchmark.pdf)

3. System detects relationship
   → Edge created: Evidence SUPPORTS Signal
   → Signal recomputed: partially grounded (1 source)

4. User uploads CTO memo
   → Evidence(Quote) extracted: "We prioritize availability"
   → System detects: SUPPORTS preference for Postgres

5. User sees graph:
   → Signal node: "Postgres better" (now shows 2 supporting sources)
   → Still missing: operational complexity, cost comparison
```

### V1 Contradiction Scenario

```
1. User: "The market is growing at 20% annually"
   → Signal(Assumption) extracted

2. User uploads market report
   → Evidence: "Market grew 12% last year" (from report_2024.pdf)
   → Evidence: "Growth expected to accelerate to 18%" (from forecast.pdf)

3. System detects CONTRADICTION
   → Edge marked: Evidence CONTRADICTS Signal
   → Visual indicator: red line between nodes
   → User sees: "Your assumption (20%) differs from documented trends (12%-18%)"

4. User refines thinking
   → Updates Signal: "Market growing 15-18%"
   → System recomputes: Signal now better-grounded
```

---

## API Usage Examples

### List Evidence from Document

```http
GET /api/evidence/?document_id={uuid}
```

Returns all facts extracted from that document.

### Get High-Quality Evidence

```http
GET /api/evidence/high_confidence/
```

Returns evidence with:
- Extraction confidence > 0.8, OR
- User credibility rating >= 4 stars

### Rate Evidence Credibility

```http
PATCH /api/evidence/{id}/rate/
{
  "rating": 5
}
```

User marks this as highly credible (5 stars).

### Filter by Type

```http
GET /api/evidence/?type=metric&case_id={uuid}
```

Get all metrics from documents in this case.

---

## V1 Implementation: Unified Node Model

V1 doesn't have separate Signal/Evidence storage — it has a unified **Node** with a type field:

```python
class Node:
    type: str  # "assumption", "claim", "evidence", etc.
    content: str
    source: str  # "conversation" or "document_id"
    embedding: vector  # for similarity matching
    created_at: datetime
```

And **Edges** for relationships:

```python
class Edge:
    source_node: Node  # signal or evidence
    target_node: Node  # signal or evidence
    relationship: str  # "supports", "contradicts", "relates_to"
```

**Why unified:** Cleaner code, easier to query, same interface for all relationships.

**How it preserves the distinction:** Node.type and Node.source tell you whether it's user thinking or external fact.

---

## Summary

**The core distinction survives v1:**
- User thoughts are tracked as nodes with provenance
- External facts are tracked as nodes with document references
- Edges show relationships (supports, contradicts)
- The graph makes both visible and shows how they connect

This foundation enables:
- Clear provenance for every claim
- Contradiction detection (evidence contradicts assumption)
- Assumption surfacing (here's what you're betting on)
- Future: gap analysis (here's what should exist but doesn't)
