# Evidence Ingestion & Companion Service

Two tightly integrated systems: the **Evidence Ingestion Service** (universal pipeline for all evidence entering the system) and the **Companion Service** (meta-cognitive layer that monitors the knowledge graph and generates Socratic reflections).

## Part 1: Evidence Ingestion Service

**File:** `backend/apps/projects/ingestion_service.py`

Single convergence point for all evidence — research findings, URL fetches, pasted text, and document extractions all flow through the same pipeline.

### Pipeline (4 stages)

```
Stage 1: Document/Chunk Scaffolding
    Create or reuse Document + DocumentChunk (synthetic if needed)
    ↓
Stage 2: Bulk Evidence Creation (atomic transaction)
    Evidence.objects.bulk_create() with full provenance metadata
    ↓
Stage 3: Batch Embedding Generation
    Batch API call (fallback to individual on failure)
    ↓
Stage 4: Auto-Reasoning + Cascade
    Find similar signals → LLM classify → M2M links → trigger cascade
```

### Stage Details

**Stage 1 — Synthetic Documents:** If no existing document referenced, creates a lightweight one: title `"{source_label} ({YYYY-MM-DD HH:MM})"`, type `ingested`, status `indexed`. One per batch.

**Stage 2 — Provenance Metadata:**

| Field | Purpose |
|-------|---------|
| `source_url` | Where evidence was found (2000 char max) |
| `source_title` | Article/page title (500 char) |
| `source_domain` | Auto-parsed from URL if missing |
| `source_published_date` | Publication date (ISO) |
| `retrieval_method` | `document_upload`, `research_loop`, `external_paste`, `url_fetch`, `user_observation`, `chat_bridged` |
| `extraction_confidence` | LLM confidence 0.0–1.0 |

**Stage 3 — Embeddings:** Batch API preferred; individual fallback on failure. Non-fatal — evidence created even without embedding. All saved in single `bulk_update()`.

**Stage 4 — Auto-Reasoning:** Delegates to `AutoReasoningPipeline.process_new_evidence()`. Creates M2M links, triggers assumption cascade. Uses `async_to_sync()` for Celery compatibility.

### Input/Output

```python
# Input
@dataclass
class EvidenceInput:
    text: str
    evidence_type: str = 'fact'          # fact, metric, claim, quote, benchmark
    extraction_confidence: float = 0.8
    source_url: str = ''
    source_title: str = ''
    retrieval_method: str = 'document_upload'
    # ... (document_id, chunk_id, embedding optional)

# Output
@dataclass
class IngestionResult:
    evidence_ids: List[str]
    document_id: Optional[str]
    links_created: int = 0
    contradictions_detected: int = 0
    cascade_triggered: bool = False
    errors: List[str] = []
```

### Callers

| Caller | When |
|--------|------|
| `ingest_evidence_async` (Celery) | API evidence submission |
| `fetch_url_and_ingest` (Celery) | URL evidence submission |
| `extract_evidence_from_findings()` | Research loop completion (findings with relevance ≥ 0.6) |
| `brief_signals.py` | Inquiry evidence bridged to project evidence |

### URL Fetcher (`url_fetcher.py`)

Extracts web content before ingestion:

1. HTTP fetch (30s timeout, `Episteme/1.0` user-agent)
2. BeautifulSoup cleanup (removes scripts, nav, footer, aside)
3. Meta tag extraction (published date from 5 candidates, author from 3)
4. Content truncated to 100KB

---

## Part 2: Companion Service & Graph Analyzer

### Graph Analyzer

**File:** `backend/apps/companion/graph_analyzer.py` (~680 lines)

Detects structural patterns in the knowledge graph. Used by both the unified analysis engine (for reflection generation) and the brief grounding engine (for section annotations).

### Pattern Types

**`find_patterns(thread_id)`** returns:

| Pattern | How Detected | Threshold |
|---------|-------------|-----------|
| **Ungrounded assumptions** | Assumption signals with zero supporting evidence | Any |
| **Contradictions** | Signals with `contradicts`/`contradicted_by` M2M links | Any pair |
| **Strong claims** | Claims with ≥2 supporting evidence, avg confidence > 0.75 | 2+ evidence |
| **Recurring themes** | Signals grouped by embedding cosine similarity ≥ 0.80 | 2+ signals |
| **Missing considerations** | Questions not elevated to inquiries | Top 3 |

### Inquiry-Scoped Analysis

**`find_patterns_for_inquiry(inquiry_id)`** — Same patterns but filtered to single inquiry, plus `evidence_quality` breakdown (total, high/low confidence, supporting/contradicting/neutral).

**`compute_inquiry_health(inquiry_id)`** — Composite health score (0–100):

| Factor | Score Impact |
|--------|-------------|
| High-confidence contradiction | -15 (blocking) |
| Regular contradiction | -5 (warning) |
| Ungrounded assumption | -5 |
| Strong claim | +10 |
| No evidence at all | -20 |
| Less than 2 evidence | -10 |
| Baseline | 50 |

### Advanced Methods

- **`detect_circular_reasoning()`** — Cycles in signal dependency chains
- **`find_orphaned_assumptions()`** — Assumptions with no path to evidence
- **`find_evidence_deserts()`** — Inquiries with < 2 evidence items
- **`find_confidence_conflicts()`** — High-confidence items (≥ 0.75) that contradict each other

### Integration with Intelligence Engine

```python
# intelligence/engine.py
patterns = await GraphAnalyzer().find_patterns(thread_id)
# Patterns injected into unified analysis context
# → Single LLM call generates response + reflection informed by graph state
```

---

### Session Receipt Service

**File:** `backend/apps/companion/receipts.py`

Tracks session accomplishments in 4-hour windows.

**Session windows:** 00:00, 04:00, 08:00, 12:00, 16:00, 20:00

**Receipt types:**
`case_created` · `signals_extracted` · `inquiry_resolved` · `evidence_added` · `research_completed`

**Recording:**
```python
SessionReceiptService.record_case_created(thread_id, case)
SessionReceiptService.record_inquiry_resolved(thread_id, inquiry, conclusion)
SessionReceiptService.record_evidence_added(thread_id, inquiry, evidence_count, direction)
SessionReceiptService.record_research_completed(thread_id, title, source_count, case)
```

**Retrieval:**
- `GET /api/chat/threads/{id}/session_receipts/` — Current session receipts
- `get_all_thread_receipts()` — Full history across sessions
- `cleanup_old_receipts(days=30)` — Maintenance

---

### Companion Models

**Reflection** — Meta-cognitive commentary (now generated via unified analysis engine, not standalone):

| Field | Purpose |
|-------|---------|
| `reflection_text` | 2-3 paragraphs of Socratic guidance |
| `trigger_type` | `user_message`, `document_upload`, `contradiction_detected`, `periodic`, `confidence_change` |
| `patterns` | Graph patterns that informed this reflection |
| `analyzed_messages` / `analyzed_signals` | Context tracking |

**InquiryHistory** — Confidence evolution tracking:

| Field | Purpose |
|-------|---------|
| `inquiry` | FK to Inquiry |
| `confidence` | Float 0.0–1.0 at this point |
| `trigger_event` | What caused the change |
| `reason` | Human-readable explanation |

Django `post_save` signal on Inquiry auto-creates history entries when confidence changes.

---

### Companion Service Methods

| Method | Purpose |
|--------|---------|
| `prepare_reflection_context()` | Gathers last 10 messages + signals + graph patterns for reflection generation |
| `track_background_work(since)` | Queries recent activity: signals extracted, evidence linked, connections built, confidence changes |
| `get_case_state()` | Summary: open/resolved inquiries, validated/unvalidated assumptions, evidence gaps |

---

### Socratic Prompts (`prompts.py`)

Templates for reflection generation in unified analysis:

| Prompt | Purpose |
|--------|---------|
| `get_socratic_reflection_prompt()` | Main reflection: probing questions, assumption challenges, reframes |
| `get_contradiction_prompt()` | Analyze whether two statements contradict |
| `get_assumption_challenge_prompt()` | 2-3 Socratic questions to challenge an assumption |
| `get_missing_consideration_prompt()` | Surface blind spots (stakeholders, costs, edge cases) |
| `get_action_card_reflection_prompt()` | Meta-commentary on action cards shown to user |

Memory-enhanced version includes past reflections for continuity.

---

## Data Flow Integration

```
Evidence Ingestion
  → Auto-Reasoning (similar signals → M2M links)
      → Assumption Cascade (status → plan → grounding)
          → GraphAnalyzer detects patterns
              → Unified Engine generates reflection

Research Loop completes
  → Extract findings → Evidence records
      → Ingestion pipeline
          → [same cascade path above]

Chat message
  → GraphAnalyzer.find_patterns()
      → Unified Engine builds context
          → Single LLM call: response + reflection + signals
              → Save Reflection with patterns
              → Record SessionReceipt for accomplishments
```

---

## Key Files

```
backend/apps/
├── projects/
│   ├── ingestion_service.py     # EvidenceIngestionService (universal pipeline)
│   ├── url_fetcher.py           # URL content extraction
│   ├── models.py                # Evidence model with provenance fields
│   └── evidence_views.py        # /evidence/ingest/, /evidence/fetch-url/
├── companion/
│   ├── graph_analyzer.py        # GraphAnalyzer (5 pattern types + health scoring)
│   ├── services.py              # CompanionService (reflection context, background work)
│   ├── receipts.py              # SessionReceiptService (4-hour windowed tracking)
│   ├── prompts.py               # Socratic reflection templates
│   ├── models.py                # SessionReceipt, Reflection, InquiryHistory
│   └── signals.py               # post_save handler for confidence tracking
└── tasks/
    └── ingestion_tasks.py       # ingest_evidence_async, fetch_url_and_ingest
```
