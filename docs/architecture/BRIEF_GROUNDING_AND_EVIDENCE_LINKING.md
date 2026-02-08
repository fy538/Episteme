# Brief Grounding & Evidence Linking

Three interconnected subsystems that form the analytical backbone of Episteme: the **Brief Grounding Engine** (evidence quality tracking), **Evidence Linker** (claim-to-signal matching), and **Scaffold Service** (conversation-to-case transformation).

## System Interaction Overview

```
Conversation                    Knowledge Graph
    │                          (Signals, Evidence, Inquiries)
    ↓                                    │
┌─────────────────┐                      │
│ Scaffold Service │──── creates ─────→  Case + Brief + Inquiries + Signals
└─────────────────┘                      │
                                         ↓
┌─────────────────┐              ┌───────────────┐
│ Evidence Linker  │←── reads ───│ Brief Sections │
│ (claim↔signal)   │             │ + Inquiries    │
└────────┬────────┘              └───────┬───────┘
         │ links                         │
         ↓                               ↓
┌─────────────────┐              ┌───────────────────┐
│ Evidence Records │──── feeds ──→│ Grounding Engine   │
└─────────────────┘              │ (status + annotations)│
                                 └───────┬───────────┘
                                         │ syncs
                                         ↓
                                 ┌───────────────────┐
                                 │ Readiness Checklist│
                                 └───────────────────┘
```

---

## Brief Grounding Engine

**File:** `backend/apps/cases/brief_grounding.py` (~35KB)

Computes evidence-based quality status for each section of a case brief. This is the engine that tells users "this section is well-supported" vs "this section has unresolved tensions."

### Entry Point

```python
BriefGroundingEngine.evolve_brief(case_id) → EvolveDelta
```

### Pipeline

1. **Load sections** — all `BriefSection` records for the case's main brief
2. **Compute grounding** per section:
   - Count evidence items by direction (supports / contradicts / neutral)
   - Find unvalidated assumptions (signals without supporting evidence)
   - Detect tensions (signals with contradictions via M2M `contradicts`)
   - Calculate average evidence strength
3. **Determine status** — `EMPTY` → `WEAK` → `MODERATE` → `STRONG` → `CONFLICTED`
4. **Compute annotations** via `GraphAnalyzer` (or inline fallback):
   - `TENSION` — conflicting signals/evidence
   - `UNGROUNDED` — assumptions without evidence path
   - `EVIDENCE_DESERT` — insufficient evidence
   - `WELL_GROUNDED` — strong evidence support
   - `STALE` — evidence may be outdated
   - `LOW_CREDIBILITY` — relies on low-rated evidence (>50% of sources rated ≤2 stars)
5. **Reconcile annotations** — signature-based dedup `(type, description[:80])`:
   - New annotations created, resolved ones marked `resolved_at`
   - Prevents annotation churn across recomputations
6. **Update section locks** — synthesis/recommendation sections locked until inquiries resolve
7. **Sync readiness** — auto-create checklist items from gaps, auto-complete when gaps resolve

### Key Models

**`BriefSection`** (`brief_models.py`):
- `section_id` — matches `<!-- section:ID -->` marker in markdown
- `section_type` — `decision_frame | inquiry_brief | synthesis | trade_offs | recommendation | custom`
- `inquiry` FK — links to `Inquiry` for grounding computation
- `grounding_status` — `empty | weak | moderate | strong | conflicted`
- `grounding_data` — JSON with cached metrics
- `is_locked` / `lock_reason` — prevents editing locked sections
- `user_confidence` — 1-4 scale (Phase 4)

**`BriefAnnotation`** (`brief_models.py`):
- `annotation_type` — `tension | blind_spot | ungrounded | evidence_desert | well_grounded | stale | circular | low_credibility`
- `priority` — `blocking | important | info`
- `source_signals` M2M — what triggered this annotation
- Lifecycle: created → `dismissed_at` (user) or `resolved_at` (system)

### Evidence Thresholds

Configurable per case via `case.investigation_preferences.evidence_threshold`:

| Level | Strong evidence min | Moderate min | Requires validation? |
|-------|--------------------|--------------|--------------------|
| `low` | 1 | 1 | No |
| `medium` | 3 | 1 | Yes |
| `high` | 5 | 2 | Yes |

### Readiness Sync

After grounding recomputation, the engine auto-manages readiness checklist items:

- **Create** items for new gaps (investigation needed, validation needed, tensions to resolve)
- **Auto-complete** items whose gaps resolved (evidence gathered, assumptions validated)
- Completion note explains why: e.g., "Evidence has been gathered — gap resolved by brief evolution"

---

## Evidence Linker

**File:** `backend/apps/cases/evidence_linker.py` (~19KB)

Establishes semantic connections between **claims** (extracted from documents) and **signals** (from the knowledge graph). Answers: "What evidence supports this claim?"

### Entry Point

```python
extract_and_link_claims(document_content, signals, inquiries=None)
→ { claims, summary, evidence_coverage }
```

### Pipeline

1. **Extract claims** (`_extract_claims`) — LLM identifies claims with types:
   - `fact | assumption | opinion | prediction | conclusion`
   - Returns: text, location, type, importance
2. **Pre-filter signals** (`_prefilter_signals_by_embedding`) — cosine similarity top-k per claim
   - Threshold: 0.4 similarity minimum
   - Top 5 signals per claim
   - Reduces LLM token cost by ~80%
3. **Link claims to signals** (`_link_claims_to_signals`) — LLM matches claims to filtered signals
   - Returns: linked_signals[], confidence, is_substantiated, suggestion
4. **Calculate coverage** — `substantiated / total` claims

### Evidence Persistence

`persist_evidence_links(linked_claims, case_id)` — two-tier matching strategy:

| Strategy | How | When |
|----------|-----|------|
| **Text prefix match** | First 50 chars of claim → search in evidence text | Fast path, ~150ms |
| **Embedding fallback** | Cosine similarity ≥ 0.75 between embeddings | If text match fails |

Creates `evidence.supports_signals.add(signal)` M2M relationships.

### Additional Capabilities

- **`get_evidence_suggestions()`** — AI-generated guidance for gathering missing evidence (type, sources, priority, search query)
- **`create_inline_citations()`** — Augments document with `[^N]` footnotes linking claims to their supporting signals

### Constants (`constants.py`)

| Constant | Value | Purpose |
|----------|-------|---------|
| `EVIDENCE_MATCH_PREFIX_LEN` | 50 | Chars for text prefix matching |
| `EVIDENCE_MATCH_LIMIT` | 5 | Max evidence records per claim |
| `EVIDENCE_EMBEDDING_SIMILARITY_THRESHOLD` | 0.75 | Min cosine similarity for embedding match |

---

## Scaffold Service

**File:** `backend/apps/cases/scaffold_service.py` (~22KB)

Transforms conversations (or blank input) into fully structured cases with inquiries, brief sections, signals, and investigation plans.

### Three Modes

#### 1. `scaffold_from_chat(transcript, user, project_id, skill_context=None)`

Full extraction from a conversation:

```
Transcript → LLM extraction → ScaffoldExtraction
    ↓
Create Case + CaseDocument (brief)
    ↓
Create Inquiries (one per key_uncertainty)
    ↓
Create BriefSections (Decision Frame + per-inquiry + Trade-offs + Recommendation)
    ↓
Create Signals (type=ASSUMPTION for each detected assumption)
    ↓
Bootstrap InvestigationPlan
    ↓
Emit CASE_SCAFFOLDED event
```

**LLM extracts:**
- `decision_question` — the core question being decided
- `key_uncertainties` — 2-5 items, each becomes an Inquiry
- `assumptions` — each becomes a Signal (type=ASSUMPTION)
- `constraints` — timeline, budget, regulatory, etc.
- `stakeholders` — name, interest, influence
- `stakes_level` — low / medium / high

**Skill-aware extraction:** When `skill_context` is provided, domain knowledge is injected into the LLM extraction prompt, producing domain-specific uncertainties and constraints.

#### 2. `scaffold_minimal(title, user, project_id)`

Blank case with minimal structure:
- Case + CaseDocument
- BriefSections: Decision Frame + Trade-offs + Recommendation
- Empty InvestigationPlan
- Synthesis sections start locked

#### 3. `evolve_scaffold(case_id)`

Delegates to `BriefGroundingEngine.evolve_brief(case_id)` — recomputes grounding for all sections.

### Generated Brief Markdown

Each section marked with HTML comment for frontend parsing:

```markdown
# Should we hire a contractor?

<!-- section:sf-abc123 -->
## Decision Frame
Background context here...

**Constraints:**
- Budget: Under $50k

<!-- section:sf-def456 -->
## Is the contractor faster than our team?
*Linked to inquiry: Speed comparison*
Why this matters: Timeline is critical...

<!-- section:sf-ghi789 -->
## Recommendation
*Suggested — builds from your inquiry conclusions*
```

---

## Integration Points

| System | How it connects |
|--------|----------------|
| **Signals** | Grounding counts/aggregates signals; annotations link to source signals |
| **Inquiries** | Section → Inquiry FK; evidence aggregated per inquiry |
| **Evidence** | Evidence items drive grounding status; linker creates signal↔evidence M2M |
| **Skills** | Skill context injected into scaffold extraction prompts |
| **Events** | `CASE_SCAFFOLDED`, `SIGNAL_EXTRACTED` events for audit trail |
| **Readiness** | Auto-derived from grounding gaps; auto-completed when gaps resolve |

## Error Handling

| Component | Failure | Fallback |
|-----------|---------|----------|
| GraphAnalyzer | Exception | Inline annotation heuristics |
| LLM extraction (scaffold) | JSON parse fail | Minimal ScaffoldExtraction |
| Embedding generation | None returned | Text-only matching in linker |
| Evidence chunk lookup | Not found | Log warning, continue |
| Readiness sync | Plan creation fails | Log, still save grounding |

---

## Key Files

```
backend/apps/cases/
├── brief_grounding.py      # BriefGroundingEngine.evolve_brief()
├── evidence_linker.py      # extract_and_link_claims(), persist_evidence_links()
├── scaffold_service.py     # CaseScaffoldService (3 modes)
├── brief_models.py         # BriefSection, BriefAnnotation models
├── constants.py            # Evidence matching thresholds
└── export_service.py       # Brief export to structured JSON
```
