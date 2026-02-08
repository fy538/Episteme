# Event Sourcing & Provenance

The append-only event store that serves as the authoritative audit trail for all significant actions in Episteme. Maintains strict immutability, auto-categorizes events as **provenance** (user-facing timeline) or **operational** (internal system state), and links related events via correlation IDs.

## Architecture

```
Action occurs (user, assistant, or system)
    ↓
EventService.append()          ← ONLY entry point for event creation
    ├── Validate payload (must be dict)
    ├── Auto-categorize (provenance vs operational)
    ├── Auto-denormalize (inject case_title into payload)
    └── Event.objects.create()
         ↓
    Immutable record stored
    (save() raises ValueError on update, delete() raises ValueError)
```

---

## Immutability — Three Layers

| Layer | Mechanism |
|-------|-----------|
| **Model** | `save()` raises `ValueError` on update attempts; `delete()` raises `ValueError` |
| **Service** | Only `EventService.append()` creates events — no direct `Event.objects.create()` |
| **API** | `ReadOnlyModelViewSet` — no create/update/delete endpoints exposed |

---

## Event Model

| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key (auto-generated) |
| `timestamp` | DateTime | Auto-set on creation, indexed |
| `actor_type` | Enum | `USER`, `ASSISTANT`, or `SYSTEM` |
| `actor_id` | UUID | User ID (null for system actors) |
| `type` | String | 67 defined event types |
| `category` | String | `PROVENANCE` or `OPERATIONAL` (auto-assigned) |
| `payload` | JSON | Self-contained event data |
| `correlation_id` | UUID | Groups related events (workflows, multi-step ops) |
| `case_id` | UUID | Denormalized for query efficiency |
| `thread_id` | UUID | Chat context link |

**7 composite indexes** for efficient querying:
- `(timestamp)`, `(case_id, timestamp)`, `(thread_id, timestamp)`
- `(type, timestamp)`, `(correlation_id)`
- `(actor_type, actor_id, timestamp)`, `(category, case_id, timestamp)`

---

## Event Categories

Events are auto-categorized based on type. The split determines what users see vs. what operators debug.

### Provenance Events (23 types) — User-Facing Timeline

| Domain | Event Types |
|--------|------------|
| Case lifecycle | `CASE_CREATED`, `CASE_CREATED_FROM_ANALYSIS`, `CASE_SCAFFOLDED`, `CASE_ARCHIVED` |
| Inquiries | `INQUIRY_CREATED`, `INQUIRY_RESOLVED`, `INQUIRY_REOPENED`, `INQUIRIES_AUTO_CREATED` |
| Knowledge | `DOCUMENT_ADDED`, `EVIDENCE_ADDED`, `SIGNAL_PROMOTED`, `SIGNAL_DISMISSED` |
| Synthesis | `BRIEF_EVOLVED`, `BRIEF_SECTION_WRITTEN`, `BRIEF_SECTION_REVISED`, `STRUCTURE_ACCEPTED`, `STRUCTURE_DISMISSED` |
| Research | `RESEARCH_COMPLETED` |
| Ingestion | `EVIDENCE_INGESTED`, `URL_FETCHED` |
| User decisions | `CONFIDENCE_CHANGED`, `POSITION_REVISED` |
| Planning | `PLAN_CREATED`, `PLAN_VERSION_CREATED`, `PLAN_STAGE_CHANGED` |

### Operational Events (21 types) — Internal System State

| Domain | Event Types |
|--------|------------|
| Messaging | `USER_MESSAGE_CREATED`, `ASSISTANT_MESSAGE_CREATED` |
| Agent execution | `AGENT_WORKFLOW_STARTED`, `AGENT_PROGRESS`, `AGENT_COMPLETED`, `AGENT_FAILED`, `AGENT_CHECKPOINT`, `AGENT_TRAJECTORY` |
| Workflows | `WORKFLOW_STARTED`, `WORKFLOW_COMPLETED` |
| Signal processing | `SIGNAL_EXTRACTED`, `SIGNAL_STATUS_CHANGED`, `SIGNAL_EDITED` |
| Analysis | `CONVERSATION_ANALYZED_FOR_CASE`, `CONVERSATION_ANALYZED_FOR_AGENT`, `STRUCTURE_SUGGESTED` |
| Plan diffs | `PLAN_DIFF_PROPOSED`, `PLAN_DIFF_ACCEPTED`, `PLAN_DIFF_REJECTED`, `PLAN_RESTORED` |
| Views | `WORKING_VIEW_MATERIALIZED` |
| Case ops | `CASE_PATCHED`, `CASE_LINKED_TO_THREAD` |

Plus **23 reserved types** for planned features.

---

## Correlation IDs — Distributed Tracing

Three-tier implementation links HTTP requests, logs, and events:

### 1. Middleware (entry point)
```
Incoming request → extract X-Correlation-ID header (or generate UUID)
    → set ContextVar for request duration
    → response carries same ID back
```

### 2. ContextVar (propagation)
Thread-safe context variable accessible throughout async/sync execution.

### 3. Event + Log Integration
All events and log records include `correlation_id` for tracing.

**Agent workflow example:**
```
AGENT_WORKFLOW_STARTED (correlation_id=abc)
  → AGENT_PROGRESS (correlation_id=abc, step=gathering_context)
  → AGENT_PROGRESS (correlation_id=abc, step=researching)
  → AGENT_COMPLETED (correlation_id=abc)
```

Query all related events: `Event.objects.filter(correlation_id=abc).order_by('timestamp')`

---

## EventService API

### Append (creation)

```python
EventService.append(
    event_type,           # Required: one of 67 defined types
    payload,              # Required: JSON-serializable dict
    actor_type=SYSTEM,    # USER, ASSISTANT, or SYSTEM
    actor_id=None,        # User UUID if actor is USER
    correlation_id=None,  # For grouping related events
    case_id=None,         # Denormalized ownership link
    thread_id=None,       # Chat context
) → Event
```

Auto-behaviors:
- Validates payload is a dict
- Auto-injects `case_title` into payload (avoids joins in timeline queries)
- Auto-assigns `category` based on event type

### Query methods

| Method | Returns | Use Case |
|--------|---------|----------|
| `get_case_timeline(case_id)` | Provenance events, DESC by timestamp | User-facing timeline |
| `get_thread_timeline(thread_id)` | All events, ASC by timestamp | Thread context |
| `get_workflow_events(correlation_id)` | All events with correlation ID, ASC | Workflow debugging |

---

## REST API

```
GET /api/events/                                  # List (filtered by user ownership)
    ?case_id=<uuid>
    ?thread_id=<uuid>
    ?correlation_id=<uuid>
    ?type=CaseCreated
    ?types=CaseCreated,InquiryResolved
    ?exclude_types=AgentProgress
    ?category=provenance|operational
    ?limit=50  (max 200)

GET /api/events/case/<case_id>/timeline/          # Case provenance timeline
GET /api/events/thread/<thread_id>/timeline/      # Thread event sequence
GET /api/events/workflow/<correlation_id>/         # Workflow execution trace
```

**Access control:** Users only see events from their own cases and threads.

---

## Usage Patterns

**54 `EventService.append()` calls** across 16 modules. Key patterns:

| Pattern | Example | Actor |
|---------|---------|-------|
| User action | Case created, signal dismissed | USER |
| System automation | Inquiries auto-created, brief evolved | SYSTEM |
| Agent workflow | Research started → progress → completed (shared correlation_id) | SYSTEM |
| Evidence ingestion | Evidence added with retrieval metadata | SYSTEM |
| Plan mutation | Plan version created with diff summary | USER or SYSTEM |

---

## Payload Conventions

Payloads are event-specific JSON dicts (no rigid schema):

- **Case events:** `{title, position, stakes, thread_id}`
- **Evidence events:** `{evidence_count, document_id, links_created, contradictions_detected, retrieval_method}`
- **Agent events:** `{agent_type, step, message, placeholder_message_id}`
- **Plan events:** `{plan_id, version_number, created_by, diff_summary}`

---

## Key Files

```
backend/apps/events/
├── models.py           # Event model with immutability enforcement
├── services.py         # EventService.append() + query methods
├── views.py            # ReadOnlyModelViewSet + timeline endpoints
├── serializers.py      # EventSerializer (all fields read-only)
└── migrations/         # 5 migrations (initial → provenance categories → ingestion types)

backend/apps/common/
├── correlation.py      # ContextVar-based correlation ID
└── middleware/
    └── request_logging.py  # X-Correlation-ID injection + structured logging
```
