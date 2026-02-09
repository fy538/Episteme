# Investigation Plan Service

Manages versioned, immutable snapshots of investigation strategies. Every mutation creates a new `PlanVersion`, enabling complete audit trails, time-travel, and non-destructive rollback.

## Architecture

```
Case (1:1) ←→ InvestigationPlan
                    ↓
            PlanVersion (1, 2, 3, ...)    ← immutable snapshots
                    ↓
            content: {phases, assumptions, decision_criteria, metadata}
```

All plan mutations flow through `PlanService` → deep copy current content → apply change → create new version → update pointer → emit event → trigger brief re-grounding.

---

## Data Model

### InvestigationPlan (one-to-one with Case)

| Field | Type | Purpose |
|-------|------|---------|
| `stage` | CharField | `EXPLORING → INVESTIGATING → SYNTHESIZING → READY` |
| `current_version` | Integer | Points to latest accepted version number |
| `position_statement` | TextField | Evolving thesis |
| `created_from_event_id` | UUID | Provenance link |

### PlanVersion (immutable snapshots)

| Field | Type | Purpose |
|-------|------|---------|
| `version_number` | Integer | Sequential (1, 2, 3, ...) |
| `content` | JSON | Complete plan state |
| `created_by` | CharField | `system`, `ai_proposal`, `user_request`, `critique`, `restore` |
| `diff_summary` | TextField | Human-readable change description |
| `diff_data` | JSON | Structured diff for UI rendering |
| `created_from_event_id` | UUID | Provenance link |

### Content Structure

Each version's `content` JSON contains:

**Phases** — Investigation stages:
```json
{
  "id": "uuid", "title": "Initial Investigation",
  "description": "Address core questions", "order": 0,
  "inquiry_ids": ["inquiry-uuid-1", "inquiry-uuid-2"]
}
```

**Assumptions** — Testable beliefs linked to Signals:
```json
{
  "id": "uuid", "signal_id": "signal-uuid",
  "text": "Market is growing 20% YoY",
  "status": "untested|confirmed|challenged|refuted",
  "test_strategy": "Validate via Gartner reports",
  "evidence_summary": "2 supporting, 1 contradicting",
  "risk_level": "high"
}
```

**Decision criteria** — Success conditions:
```json
{
  "id": "uuid", "text": "At least 3 customer validations",
  "is_met": false, "linked_inquiry_id": "inquiry-uuid"
}
```

**Metadata:** `stage_rationale` explaining current stage.

---

## Assumption ↔ Signal Relationship

**Single source of truth:** The `Signal` model holds the authoritative `assumption_status` field.

- Plan assumptions store `signal_id` pointing to the Signal record
- When plan assumption status changes → updates linked Signal
- When assumption cascade recomputes status → syncs back to plan (new version)
- On plan initialization, assumptions linked to existing Signals via normalized text match

This bidirectional sync is depth-limited (max 3) to prevent infinite loops. See [AUTO_REASONING_CASCADE.md](./AUTO_REASONING_CASCADE.md).

---

## Service Methods

| Method | What it does | Creates Version? |
|--------|-------------|-----------------|
| `create_initial_plan()` | Setup on case creation; links assumptions to signals; creates v1 | Yes |
| `create_new_version()` | Accept AI proposal or user edit | Yes |
| `update_stage()` | Advance investigation phase (EXPLORING → INVESTIGATING → ...) | Yes |
| `restore_version()` | Revert to previous snapshot (creates new version with old content) | Yes |
| `update_assumption_status()` | Mark assumption confirmed/refuted/etc, syncs to Signal | Yes |
| `update_criterion_status()` | Toggle criterion as met/unmet | Yes |

### Mutation Flow

1. Validate change
2. Deep copy current content (prevent historical mutation)
3. Apply change to copy
4. `PlanVersion.create_snapshot()` → new immutable version
5. Update `plan.current_version` pointer
6. Emit event for provenance (`PLAN_VERSION_CREATED`)
7. Trigger `BriefGroundingEngine.evolve_brief()` (non-blocking, non-fatal)

All mutations wrapped in `@transaction.atomic`.

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/cases/{id}/plan/` | GET | Current plan with inline content |
| `/api/cases/{id}/plan/versions/` | GET | All historical versions |
| `/api/cases/{id}/plan/versions/{n}/` | GET | Specific version |
| `/api/cases/{id}/plan/stage/` | POST | Update investigation stage |
| `/api/cases/{id}/plan/restore/` | POST | Revert to previous version |
| `/api/cases/{id}/plan/accept-diff/` | POST | Accept AI proposal |
| `/api/cases/{id}/plan/assumptions/{id}/status/` | POST | Update assumption status |
| `/api/cases/{id}/plan/criteria/{id}/status/` | POST | Update criterion |

---

## Key Files

```
backend/apps/cases/
├── plan_service.py     # PlanService — all plan mutations
├── models.py           # InvestigationPlan, PlanVersion
└── views.py            # Plan API endpoints
```
