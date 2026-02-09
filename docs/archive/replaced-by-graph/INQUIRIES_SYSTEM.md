# Inquiries System

The bridge between raw signals and decision synthesis. Inquiries are focused investigation units that accumulate evidence, surface objections, track dependencies, and resolve with conclusions that feed back into case briefs.

## Lifecycle Overview

```
Signal extracted from conversation/document
    ↓
Promotion check (repetition, blocking, high confidence)
    ↓
Inquiry created (OPEN)
    ↓ evidence accumulates
INVESTIGATING
    ↓ confidence passes threshold
Ready to resolve (confidence > 0.6, ≥ 2 evidence, avg credibility ≥ 3.0)
    ↓
RESOLVED (conclusion + confidence)
    ↓
Auto-completes readiness items
Brief update suggested
```

---

## Signal Elevation

### Automatic Promotion Criteria

| Criterion | Trigger | Reason |
|-----------|---------|--------|
| Repetition | Same signal (by dedupe_key) appears 3+ times | `REPETITION` |
| Blocking question | Question type, confidence > 0.8 or repeated 2+ times | `BLOCKING` |
| High-confidence assumption | Assumption type, confidence > 0.85 | `HIGH_STRENGTH` |
| High-confidence claim | Claim type, confidence > 0.8 | `HIGH_STRENGTH` |

### Promotion Process

1. Inquiry created with auto-generated title based on signal type
2. Signal linked via `signal.inquiry` FK
3. All similar signals (matching dedupe_key) auto-linked to same inquiry
4. `INQUIRY_CREATED` event emitted

### Manual Elevation

- `POST /api/signals/{id}/promote_to_inquiry/` — Promote specific signal
- `POST /api/inquiries/create_from_assumption/` — Create from highlighted text
- `POST /api/inquiries/` — Direct creation

---

## Evidence Accumulation

### Direction Model

Evidence links to an inquiry with a **direction**:

| Direction | Meaning |
|-----------|---------|
| `supports` | Evidence backing the inquiry |
| `contradicts` | Evidence challenging the inquiry |
| `neutral` | Contextual background |

### Evidence Types

`document_full` · `document_chunks` · `experiment` · `external_data` · `user_observation`

### Aggregate Confidence

```
aggregate = (support_ratio - contradict_ratio × 0.5) × (avg_credibility / 5.0)
```
Clamped to 0.0–1.0.

| Aggregate | Category |
|-----------|----------|
| > 0.7 | **Strong** — sufficient to resolve |
| 0.4–0.7 | **Moderate** — more evidence needed |
| < 0.4 | **Weak** — insufficient or contradictory |

### Ready-to-Resolve Criteria

All three must be met:
1. Aggregate confidence > 0.6
2. At least 2 pieces of evidence
3. Average credibility ≥ 3.0

---

## Objection System

Challenges and alternative perspectives that strengthen reasoning.

### Objection Types

`alternative_perspective` · `challenge_assumption` · `counter_evidence` · `scope_limitation` · `missing_consideration`

### Sources

- **System** — AI-generated (e.g., auto-created on contradiction detection)
- **User** — Manually created by investigator
- **Document** — Extracted from source documents

### Lifecycle

`active → addressed` (with explanation in `addressed_how`) or `active → dismissed`

---

## Dependency Management

### blocked_by M2M

Inquiries can declare dependencies: if A is "blocked by" B, then B must resolve before A.

- Circular dependency validation on update (returns 400 if detected)
- `is_blocked` computed field: True if any blocking inquiry is unresolved
- Dependency graph endpoint for visualization

---

## Confidence Tracking

`InquiryHistory` records every confidence change with:
- New confidence value
- Trigger event (what caused the change)
- Human-readable reason
- Timestamp

Enables timeline visualizations: `20% → 45% → 65% → 70%`

---

## Resolution Flow

1. Investigator reviews evidence and objections
2. Writes conclusion text
3. Assigns confidence (0.0–1.0)
4. `POST /api/inquiries/{id}/resolve/`

### Side Effects

| Effect | Details |
|--------|---------|
| Event emission | `INQUIRY_RESOLVED` with resolution time, evidence counts, confidence |
| Readiness auto-complete | Linked `ReadinessChecklistItem` auto-completed via Django signal |
| Brief update | `generate_brief_update` API suggests brief revisions |
| Session receipt | Records accomplishment for companion panel |

### Reopening

`POST /api/inquiries/{id}/reopen/` — clears conclusion, confidence, resolved_at. Emits `INQUIRY_REOPENED` event.

---

## Investigation Plan Integration

Each `InvestigationPlan` contains phases with `inquiry_ids` arrays, linking plan stages to specific inquiries.

`POST /api/inquiries/{id}/generate_investigation_plan/` generates AI-suggested plans:
- **Hypothesis** — One-sentence testable statement
- **Research approaches** — 3-5 concrete, actionable methods
- **Evidence needed** — Specific types that would confirm/refute
- **Success criteria** — Definition of "resolved" for this inquiry

---

## API Endpoints

### Inquiry Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/inquiries/` | GET/POST | List/create |
| `/inquiries/{id}/` | GET/PATCH/DELETE | CRUD |
| `/inquiries/{id}/resolve/` | POST | Resolve with conclusion |
| `/inquiries/{id}/reopen/` | POST | Reopen resolved inquiry |
| `/inquiries/{id}/start_investigation/` | POST | Mark as investigating |
| `/inquiries/{id}/update_priority/` | PATCH | Change priority |
| `/inquiries/dashboard/?case_id={id}` | GET | Status summary + next actions |
| `/inquiries/{id}/evidence_summary/` | GET | Aggregated evidence + confidence |
| `/inquiries/{id}/add-evidence/` | POST | Quick add from chat |
| `/inquiries/create_from_assumption/` | POST | Create from highlighted text |
| `/inquiries/{id}/generate_brief_update/` | POST | Suggest brief updates |
| `/inquiries/{id}/update-dependencies/` | POST | Update blocked_by |
| `/inquiries/{id}/dependency-graph/` | GET | Dependency visualization |
| `/inquiries/{id}/confidence-history/` | GET | Confidence timeline |
| `/inquiries/{id}/generate_investigation_plan/` | POST | AI investigation plan |

### Evidence

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/evidence/` | GET/POST | List/create evidence |
| `/evidence/{id}/` | GET/PATCH/DELETE | CRUD |
| `/evidence/cite_document/` | POST | Cite document/chunks as evidence |

### Objections

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/objections/` | GET/POST | List/create |
| `/objections/{id}/` | GET/PATCH/DELETE | CRUD |
| `/objections/{id}/address/` | POST | Mark addressed with explanation |
| `/objections/{id}/dismiss/` | POST | Dismiss |

---

## Data Models

### Inquiry

| Field | Type | Purpose |
|-------|------|---------|
| `title` | TextField | The investigation question |
| `description` | TextField | Additional context |
| `case` | FK to Case | Parent case |
| `status` | CharField | `OPEN`, `INVESTIGATING`, `RESOLVED`, `ARCHIVED` |
| `elevation_reason` | CharField | `REPETITION`, `CONFLICT`, `BLOCKING`, `USER_CREATED`, `HIGH_STRENGTH` |
| `conclusion` | TextField | Final answer |
| `conclusion_confidence` | Float | 0.0–1.0 |
| `resolved_at` | DateTime | When resolved |
| `priority` | Integer | Higher = more important |
| `blocked_by` | M2M to self | Dependencies |
| `embedding` | JSON | 384-dim semantic vector |
| `origin_text` | TextField | Selected text that sparked inquiry |
| `text_span` | JSON | `{from, to, section}` in source document |

### Evidence

| Field | Type | Purpose |
|-------|------|---------|
| `inquiry` | FK to Inquiry | Parent |
| `evidence_text` | TextField | Quote or interpretation |
| `direction` | CharField | `supports`, `contradicts`, `neutral` |
| `evidence_type` | CharField | `document_full`, `document_chunks`, `experiment`, `external_data`, `user_observation` |
| `strength` | Float | 0.0–1.0 |
| `credibility` | Float | 0.0–1.0 |
| `source_document` | FK to Document | Whole document source |
| `source_chunks` | M2M to DocumentChunk | Specific chunks cited |
| `verified` | Boolean | User verified |

### Objection

| Field | Type | Purpose |
|-------|------|---------|
| `inquiry` | FK to Inquiry | Parent |
| `objection_text` | TextField | The challenge |
| `objection_type` | CharField | See types above |
| `source` | CharField | `system`, `user`, `document` |
| `status` | CharField | `active`, `addressed`, `dismissed` |
| `addressed_how` | TextField | Resolution explanation |

---

## Integration Points

| System | Connection |
|--------|-----------|
| **Signals** | `signal.inquiry` FK links signals to inquiry; promotion via `should_promote_to_inquiry()` |
| **Cases** | `inquiry.case` FK; plan phases contain `inquiry_ids` |
| **Brief sections** | `BriefSection.inquiry` FK; grounding computed per inquiry |
| **Readiness** | `ReadinessChecklistItem.linked_inquiry` auto-completes on resolve |
| **Events** | `INQUIRY_CREATED`, `INQUIRY_RESOLVED`, `INQUIRY_REOPENED` for provenance |
| **Companion** | Session receipts recorded; confidence history tracked |

---

## Key Files

```
backend/apps/inquiries/
├── models.py          # Inquiry, Evidence, Objection, InquiryHistory
├── views.py           # InquiryViewSet (14 custom actions), EvidenceViewSet, ObjectionViewSet
├── serializers.py     # Full, list, and create serializers
├── services.py        # InquiryService (promotion, resolution, statistics)
└── tests.py           # Promotion logic, resolution, statistics tests
```
