# Celery Workflows & Task Orchestration

Distributed async task system built on Celery + Redis. Uses a sequential parent-child spawning pattern (not Celery chains/groups) with best-effort degradation for non-critical steps.

## Infrastructure

| Setting | Value |
|---------|-------|
| Broker | Redis (`redis://localhost:6379/0`) |
| Result backend | Redis (same instance) |
| Serialization | JSON only (no pickle) |
| Task time limit | 30 minutes |
| Task discovery | `app.autodiscover_tasks()` |

---

## Task Inventory (22 tasks)

### Critical Path Tasks

#### `assistant_response_workflow(thread_id, user_message_id)`
The main orchestrator — every user chat message flows through this.

**6-step pipeline:**
1. **Agent confirmation check** — Is user confirming a pending agent suggestion? If so, spawn agent
2. **Agent inflection detection** — Every 3 turns, analyze if conversation needs specialized agent (confidence > 0.75)
3. **Proactive interventions** — Pattern-based suggestions (best-effort, catches exceptions)
4. **Generate response** — Core chat response via `ChatService`
5. **Batched signal extraction** — Accumulates 2+ turns or 30+ chars, then extracts in single LLM call
6. **Structure readiness detection** — Progressive disclosure: suggests case structure when metrics pass

Spawns `generate_chat_title_workflow` at completion.

#### `process_document_workflow(document_id)`
Document processing pipeline: extract text → chunk → generate embeddings → index.

Sets `processing_status = 'failed'` on error. Emits `WORKFLOW_COMPLETED` event.

#### `generate_research_artifact_v2(case_id, topic, user_id, correlation_id, placeholder_message_id)`
Long-running research — the most complex task.

**Pipeline:** Load context → Load skills → ResearchLoop (Plan → Search → Extract → Evaluate → Synthesize) → Extract evidence from findings → Create artifact

**Advanced features:**
- **Checkpointing** — Resume from saved state if interrupted
- **Context continuation** — If context exhausted, builds handoff summary and runs new loop
- **Trajectory recording** — Opt-in execution trace saved to event store
- **Progress callbacks** — Real-time updates to placeholder message
- **Skills injection** — Domain-specific skills injected into research prompts
- **Evidence feedback** — Findings with relevance ≥ 0.6 converted to Evidence records, feeding back into cascade

**Retry:** Auto-retry on ConnectionError/TimeoutError, exponential backoff (max 60s), max 2 retries.

### Evidence & Ingestion Tasks

| Task | Purpose | Retry |
|------|---------|-------|
| `ingest_evidence_async` | Async wrapper for `EvidenceIngestionService.ingest()` | 2 retries, 10s delay |
| `fetch_url_and_ingest` | Fetch URL → create Document → delegate to document pipeline | 2 retries, 10s delay |
| `evolve_brief_async` | Brief grounding recomputation (cache-debounced, 10s window) | 2 retries, 5s delay |

### Signal Processing Tasks

| Task | Purpose | Schedule |
|------|---------|----------|
| `generate_signal_embeddings` | Vector encoding for new signals | Triggered by event handler |
| `consolidate_thread_signals` | Dedup (>90% similarity), decay (30-day half-life), archive (<0.3 confidence) | Spawned by scheduler |
| `schedule_signal_consolidation` | Finds threads updated in last 7 days with ≥10 signals, spawns consolidation | Daily 3 AM |
| `update_signal_temperatures` | Recalculate signal tiers (hot/warm/cold) | Daily 4 AM |

### Legacy/Deprecated Tasks

| Task | Status | Replacement |
|------|--------|-------------|
| `generate_research_artifact` (v1) | Deprecated | v2 |
| `generate_critique_artifact` | Deprecated | v2 (not yet implemented) |
| `generate_brief_artifact` | Deprecated | v2 (not yet implemented) |
| `extract_document_signals_workflow` | Removed | `process_document_workflow` |

### Phase 2B Research Tasks (Legacy)

`generate_research_workflow`, `generate_debate_workflow`, `generate_critique_workflow` — AI document generation for inquiries. Each emits 3 provenance events.

### Stubs (Not Implemented)

`cleanup_old_events`, `refresh_working_views`, `extract_signals_workflow`, `draft_case_workflow`

---

## Key Workflow Chains

### Chat → Response → Signals → Structure Detection
**Duration:** < 5s typical

```
User sends message
  → assistant_response_workflow.delay()
      ├── Agent check → inflection detection → interventions
      ├── Generate response (ChatService)
      ├── Batch signal extraction
      ├── Structure readiness detection
      └── spawn: generate_chat_title_workflow.delay()
```

### Evidence → Ingestion → Signal Linking → Brief
**Duration:** 10-30s

```
submit_evidence()
  → ingest_evidence_async.delay()
      ├── Run ingestion service (create records)
      ├── Link to signals (auto-reasoning)
      ├── Detect contradictions
      └── Emit EVIDENCE_ADDED event
  → (Django signal) evolve_brief_async.delay()
      └── Recompute brief grounding
```

### Research → Findings → Evidence → Cascade
**Duration:** 2-10 minutes

```
request_research()
  → generate_research_artifact_v2.delay()
      ├── Load context (signals, evidence, skills)
      ├── Run ResearchLoop (Plan → Search → Extract → Synthesize)
      ├── Handle context continuation if needed
      ├── Extract findings → Evidence records (relevance ≥ 0.6)
      ├── Create Artifact + ArtifactVersion
      └── Update placeholder message with progress
```

### URL → Document → Evidence → Cascade
```
submit_url()
  → fetch_url_and_ingest.delay()
      ├── Fetch URL content (BeautifulSoup)
      ├── Create Document record
      └── spawn: process_document_workflow.delay()
          ├── Chunk → Embed → Index
          └── (triggers evidence extraction → cascade)
```

---

## Orchestration Patterns

### Sequential Parent-Child (not Celery chains)
Parent task spawns child via `.delay()`. Child runs independently, no result aggregation. Simple, resilient, easy to debug.

### Best-Effort Degradation
Critical path (response generation) must succeed. Optional enhancements (titles, interventions, events) catch all exceptions and log warnings. User never sees errors from non-critical steps.

### Agent Registry Dynamic Dispatch
```python
descriptor = AGENT_REGISTRY[agent_type]    # 'research', 'critique', 'brief'
task = descriptor.entry_point.delay(**kwargs)
```
Registry maps agent types to Celery task functions.

### Debounced Execution
`evolve_brief_async` uses cache-based debouncing (10s window) to batch rapid changes. Clears cache on retry. Falls back to synchronous execution if Celery unavailable (test compatibility).

---

## Event Integration

| Task | Events Emitted |
|------|---------------|
| `assistant_response_workflow` | `CONVERSATION_ANALYZED_FOR_AGENT`, `STRUCTURE_SUGGESTED` |
| `process_document_workflow` | `WORKFLOW_COMPLETED` |
| `ingest_evidence_async` | `EVIDENCE_ADDED` (with retrieval metadata) |
| `evolve_brief_async` | `BRIEF_EVOLVED` (sections updated, annotations created/resolved) |
| `generate_research_artifact_v2` | `AGENT_FAILED` (on error) |
| Research workflows (legacy) | `WORKFLOW_COMPLETED`, `RESEARCH_COMPLETED`, `DOCUMENT_ADDED` |

---

## Retry & Error Handling

| Task | Auto-Retry | Delay | Backoff |
|------|-----------|-------|---------|
| `ingest_evidence_async` | ConnectionError, TimeoutError | 10s | No |
| `fetch_url_and_ingest` | Always retryable | 10s | No |
| `evolve_brief_async` | Always retryable | 5s | No |
| `generate_research_artifact_v2` | ConnectionError, TimeoutError | Dynamic | Exponential (60s max) |

**Patterns:**
- Structured logging with context (task IDs, case IDs, correlation IDs)
- Document processing sets `processing_status = 'failed'` on error
- Research v2 updates placeholder message with error step
- Non-critical step failures logged as warnings, never crash parent

---

## Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| `CHAT_SYNC_RESPONSES` | Boolean | If True, skip Celery for chat (debugging) |
| Beat: 3 AM daily | `schedule_signal_consolidation` | Dedup/decay signals |
| Beat: 4 AM daily | `update_signal_temperatures` | Tier recalculation |
| Global time limit | 30 minutes | Prevents hung tasks |

---

## Key Files

```
backend/
├── config/celery_app.py                  # Celery initialization
├── config/settings/base.py               # Beat schedule, broker config
├── tasks/
│   ├── workflows.py                      # Chat, document, research tasks
│   ├── ingestion_tasks.py                # Evidence ingestion + URL fetch
│   ├── brief_tasks.py                    # Brief evolution (debounced)
│   └── jobs.py                           # Maintenance stubs
├── apps/signals/tasks.py                 # Signal consolidation + temperatures
└── apps/artifacts/workflows.py           # Research/critique/brief generation
```
