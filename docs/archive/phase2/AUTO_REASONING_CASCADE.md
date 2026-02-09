# Auto-Reasoning & Assumption Cascade

The "live knowledge graph" behavior — three interconnected mechanisms that automatically link evidence to signals, recompute assumption status, and re-ground the case brief whenever new evidence enters the system.

## The Three-Way Feedback Loop

```
┌───────────────────────────────────────────────┐
│  MECHANISM B: Auto-Reasoning Pipeline          │
│  (auto_reasoning.py)                           │
│                                                │
│  New evidence arrives with embedding           │
│    → Find similar signals (cosine ≥ 0.82)     │
│    → LLM classifies relationship               │
│    → Create M2M links (supports/contradicts)   │
│                                                │
│  m2m_changed signal fires automatically ──────────┐
└───────────────────────────────────────────────┘   │
                                                     ↓
┌───────────────────────────────────────────────┐
│  MECHANISM A: Assumption Status Cascade         │
│  (assumption_cascade.py)                        │
│                                                │
│  Recompute status from evidence balance         │
│    → untested / confirmed / challenged / refuted│
│  If status changed:                             │
│    → Sync to investigation plan (new version)   │
│    → Trigger brief grounding                    │
└──────────────────────────┬────────────────────┘
                           ↓
┌───────────────────────────────────────────────┐
│  MECHANISM C: Brief Grounding Engine            │
│  (brief_grounding.py)                          │
│                                                │
│  For each brief section:                        │
│    → Count evidence (supporting/contradicting)  │
│    → Identify tensions + ungrounded assumptions │
│    → Determine status (empty→weak→moderate→     │
│      strong→conflicted)                         │
│    → Generate/reconcile annotations             │
│    → Update section locks + readiness checklist │
└───────────────────────────────────────────────┘
         ↓
    User sees updated brief with:
    - Grounding status indicators
    - Tension/gap annotations
    - Readiness checklist items
    - Section lock status
```

---

## Mechanism B: Auto-Reasoning Pipeline

**File:** `backend/apps/reasoning/auto_reasoning.py`

Automatically establishes semantic links between evidence and signals. Triggered after evidence ingestion.

### Pipeline

1. **Embedding similarity search** — Find signals semantically similar to new evidence
   - Threshold: **0.82** cosine similarity
   - Top-K: **5** most similar signals
   - Skips dismissed signals and `EVIDENCE_MENTION` type

2. **LLM relationship classification** — For each similar signal, classify the relationship
   - Model: Claude Haiku (fast provider)
   - Temperature: 0.3, Max tokens: 150
   - Confidence threshold: **0.70** minimum to create link

3. **Graph link creation** — Create M2M relationships based on classification

4. **Inquiry confidence update** — Adjust confidence on linked inquiries

### Relationship Types

| Type | Action | M2M |
|------|--------|-----|
| `SUPPORTS` | Link evidence as support | `evidence.supports_signals.add(signal)` |
| `CONTRADICTS` | Link + auto-create objection on inquiry | `evidence.contradicts_signals.add(signal)` |
| `REFINES` | Logged but not acted upon (future) | — |
| `NEUTRAL` | Skipped | — |

### Auto-Created Objections

When a contradiction is detected and the signal is linked to an inquiry:
- Objection created with type `counter_evidence`, source `system`
- Text: "New evidence contradicts assumption: {evidence_text}"
- Links back to source document and chunk

### Inquiry Confidence Adjustments

| Event | Adjustment | Bounds |
|-------|-----------|--------|
| Supporting evidence linked | +0.05 | Max 0.95 |
| Contradicting evidence linked | -0.10 | Min 0.10 |
| Change < 0.01 | Ignored (noise filter) | — |

---

## Mechanism A: Assumption Status Cascade

**File:** `backend/apps/signals/assumption_cascade.py`

Propagates evidence changes through assumption status, plan, and brief.

### Trigger

Django M2M signal handlers registered on:
- `Evidence.supports_signals` (post_add, post_remove, post_clear)
- `Evidence.contradicts_signals` (post_add, post_remove, post_clear)

### Step 1: Recompute Assumption Status

Only processes signals with `type == ASSUMPTION`. Single aggregate query:

```
total = supporting_count + contradicting_count

if total == 0              → untested
elif contradicting == 0    → confirmed
elif supporting == 0       → refuted
elif supporting > contra   → confirmed (majority supporting)
else                       → challenged (equal or more contradicting)
```

### Step 2: Cascade Orchestration

Wrapped in `@transaction.atomic` — entire cascade is all-or-nothing.

**Infinite loop prevention:** Thread-local depth counter with `MAX_CASCADE_DEPTH = 3`:
- Plan sync → Grounding recalc → Status change → Plan sync (potential loop)
- Depth >= 3 → early exit with warning log

**Execution flow (if status changed):**
1. Sync new status to investigation plan → creates new `PlanVersion` snapshot
2. Trigger `BriefGroundingEngine.evolve_brief(case_id)` → recomputes grounding
3. Return result summary

**Graceful degradation:** Plan sync failure doesn't block grounding; both are non-fatal.

### Output

```python
{
    'status_changed': bool,
    'new_status': str,          # untested/confirmed/challenged/refuted
    'plan_synced': bool,
    'grounding_updated': bool
}
```

---

## Mechanism C: Brief Grounding (recap)

See [BRIEF_GROUNDING_AND_EVIDENCE_LINKING.md](./BRIEF_GROUNDING_AND_EVIDENCE_LINKING.md) for full details.

**Key behaviors triggered by the cascade:**

- **Status determination:** `empty → weak → moderate → strong → conflicted`
- **Annotation reconciliation:** Signature-based dedup `(type, description[:80])`
- **Section locking:** Synthesis/recommendation locked until inquiries grounded
- **Readiness sync:** Auto-create checklist items for gaps, auto-complete when resolved

### Evidence Thresholds (configurable per case)

| Level | Strong min | Moderate min | Unvalidated OK? |
|-------|-----------|-------------|-----------------|
| `low` | 1 | 1 | Yes |
| `medium` (default) | 3 | 1 | No |
| `high` | 5 | 2 | No |

---

## Triggers — What Starts the Cascade

| Source | Path |
|--------|------|
| Evidence ingestion service | → Auto-reasoning → M2M add → Cascade |
| Document processing | → Evidence extraction → Auto-reasoning → Cascade |
| Research loop completion | → Evidence extraction from findings → Ingestion → Cascade |
| Manual evidence linking | → M2M add → Cascade |
| Django signal handlers | → `brief_signals.py` triggers `evolve_brief_async.delay()` |
| API endpoint | → `PATCH /cases/{id}/evolve_brief/` (manual trigger) |

---

## Critical Thresholds

| Parameter | Value | File |
|-----------|-------|------|
| Embedding similarity (auto-reasoning) | 0.82 | `auto_reasoning.py` |
| Top-K similar signals | 5 | `auto_reasoning.py` |
| LLM relationship confidence | 0.70 | `auto_reasoning.py` |
| LLM temperature | 0.3 | `auto_reasoning.py` |
| Cascade max depth | 3 | `assumption_cascade.py` |
| Inquiry confidence boost (support) | +0.05 | `auto_reasoning.py` |
| Inquiry confidence penalty (contradict) | -0.10 | `auto_reasoning.py` |
| Confidence floor/ceiling | 0.10 / 0.95 | `auto_reasoning.py` |
| Grounding debounce (Celery) | 10 seconds | `brief_tasks.py` |

---

## System Properties

| Property | Guarantee |
|----------|-----------|
| **Idempotent** | Multiple calls with same evidence state produce same result |
| **Atomic** | Cascade wrapped in `@transaction.atomic` |
| **Depth-limited** | Thread-local counter prevents infinite loops |
| **Resilient** | LLM parse errors default to NEUTRAL; plan sync failures don't block grounding |
| **Eventually consistent** | Celery debouncing batches rapid changes (10s window) |

---

## Key Files

```
backend/apps/
├── reasoning/
│   └── auto_reasoning.py         # Mechanism B — semantic linking pipeline
├── signals/
│   ├── assumption_cascade.py     # Mechanism A — status cascade orchestrator
│   └── apps.py                   # M2M signal handler registration
├── cases/
│   ├── brief_grounding.py        # Mechanism C — grounding engine
│   ├── brief_signals.py          # Django signal handlers (trigger cascade)
│   └── plan_service.py           # Plan version creation on status sync
└── tasks/
    └── brief_tasks.py            # evolve_brief_async (debounced Celery task)
```
