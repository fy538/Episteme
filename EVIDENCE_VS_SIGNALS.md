# Evidence vs Signals: The Conceptual Model

## The Key Distinction

### Signals (User's Epistemic State)
**What:** User's thoughts, beliefs, uncertainties  
**Source:** User chat messages ONLY  
**Types:** Assumption, Question, Constraint, Goal, DecisionIntent  
**Purpose:** Capture what the user thinks and why  
**Mutability:** User can change their mind (signals evolve)

**Examples:**
- "I assume writes are append-only"
- "What's our current p99 latency?"
- "Must ship by end of Q2"
- "We need to reduce latency to 100ms"

---

### Evidence (External Facts)
**What:** Facts, data points, claims from documents  
**Source:** User-uploaded documents (PDFs, benchmarks, papers)  
**Types:** Metric, Benchmark, Fact, Claim, Quote  
**Purpose:** Ground user's reasoning with external sources  
**Mutability:** Tied to document version (if doc changes, evidence changes)

**Examples:**
- "System handles 50,000 requests per second" (metric)
- "PostgreSQL 2x faster than MongoDB for writes" (benchmark)
- "PostgreSQL supports JSONB indexing" (fact)
- "According to CTO: 'We prioritize availability'" (quote)

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

### Workflow 1: Design Review Prep

```
1. User chats: "Should we use Postgres or MongoDB?"
   → Signal(DecisionIntent) extracted

2. User uploads benchmark PDF
   → Evidence extracted: metrics, comparisons

3. User asks: "What evidence do we have for Postgres?"
   → Query returns Evidence items with exact citations

4. User rates evidence credibility (5 stars for official benchmarks)

5. AI generates design review brief
   → Cites signals (user's decision) + evidence (benchmark data)
   → No circular extraction
```

### Workflow 2: Metrics Dispute

```
1. User: "I believe our latency is under 100ms"
   → Signal(Claim) extracted

2. User uploads monitoring dashboard export
   → Evidence: "P99 latency: 250ms" (metric)

3. System detects: Evidence CONTRADICTS Signal
   → Badge: "⚠️ Your claim contradicts evidence"

4. User investigates, updates assumption
   → Signal marked as rejected
   → New Signal: "Latency is 250ms, need to improve"
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

## What's Next: Phase 2.3 (Knowledge Graph)

Add relationships to link Evidence → Signals:

```python
# In Evidence model:
supports_signals = ManyToManyField(Signal, related_name='supported_by_evidence')
contradicts_signals = ManyToManyField(Signal, related_name='contradicted_by_evidence')

# In Signal model:
supported_by = ManyToManyField(Evidence)
contradicted_by = ManyToManyField(Evidence)
```

Then build graph traversal:
```python
# Get all evidence supporting an assumption
signal = Signal.objects.get(id=...)
evidence = signal.supported_by.all()

# Find contradictions
contradictions = signal.contradicted_by.all()
```

---

## Summary

**Signals** = User's thoughts (from chat)  
**Evidence** = External facts (from docs)  
**Artifacts** = AI outputs (cite both) - coming in Phase 2.4

This clean separation enables:
- No circular extraction
- Clear provenance
- "Receipt" system for assumptions
- Foundation for knowledge graph reasoning

**Phase 2.2 complete. Ready for Phase 2.3 (graph edges)!**
