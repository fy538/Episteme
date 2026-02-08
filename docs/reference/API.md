# Episteme API Documentation

Complete API reference.

## Base URL

```
http://localhost:8000/api
```

## Authentication

All endpoints (except `/auth/token/`) require JWT authentication.

### Get Token

```http
POST /api/auth/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Refresh Token

```http
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Get Current User

```http
GET /api/auth/me/
Authorization: Bearer {access_token}
```

---

## Chat API

### List Threads

```http
GET /api/chat/threads/
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": "uuid",
    "title": "My Thread",
    "user": 1,
    "primary_case": null,
    "created_at": "2024-01-20T10:00:00Z",
    "updated_at": "2024-01-20T10:00:00Z",
    "message_count": 5,
    "latest_message": {
      "id": "uuid",
      "role": "assistant",
      "content": "Hello...",
      "created_at": "2024-01-20T10:00:00Z"
    }
  }
]
```

### Create Thread

```http
POST /api/chat/threads/
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Design Review Prep"
}
```

### Get Thread (with messages)

```http
GET /api/chat/threads/{thread_id}/
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "My Thread",
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "Hello",
      "created_at": "2024-01-20T10:00:00Z",
      "event_id": "uuid"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "Hi there!",
      "created_at": "2024-01-20T10:00:01Z",
      "event_id": "uuid"
    }
  ]
}
```

### Send Message

```http
POST /api/chat/threads/{thread_id}/messages/
Authorization: Bearer {token}
Content-Type: application/json

{
  "content": "What are the key assumptions in my approach?"
}
```

**Response:** (user message, assistant response comes async)
```json
{
  "id": "uuid",
  "thread": "thread_uuid",
  "role": "user",
  "content": "What are the key assumptions...",
  "created_at": "2024-01-20T10:00:00Z",
  "event_id": "event_uuid"
}
```

---

## Cases API

### List Cases

```http
GET /api/cases/
Authorization: Bearer {token}
```

**Query params:**
- `status`: Filter by status (draft|active|archived)
- `stakes`: Filter by stakes (low|medium|high)

### Create Case

```http
POST /api/cases/
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Should we use Postgres or MongoDB?",
  "position": "We should use Postgres because...",
  "stakes": "high",
  "thread_id": "thread_uuid"  // optional
}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Should we use Postgres or MongoDB?",
  "status": "draft",
  "stakes": "high",
  "position": "We should use Postgres because...",
  "confidence": null,
  "user": 1,
  "linked_thread": "thread_uuid",
  "created_from_event_id": "event_uuid",
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-20T10:00:00Z"
}
```

### Get Case

```http
GET /api/cases/{case_id}/
Authorization: Bearer {token}
```

### Update Case

```http
PATCH /api/cases/{case_id}/
Authorization: Bearer {token}
Content-Type: application/json

{
  "position": "Updated position text",
  "confidence": 0.85,
  "status": "active"
}
```

### Get Working View

Get the materialized snapshot of a case (for fast rendering).

```http
GET /api/cases/{case_id}/work/
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "uuid",
  "case": "case_uuid",
  "summary_json": {
    "title": "Should we use Postgres or MongoDB?",
    "position": "We should use Postgres...",
    "stakes": "high",
    "confidence": 0.85,
    "status": "active",
    "assumptions": [
      {
        "id": "signal_uuid",
        "type": "Assumption",
        "text": "We need strong consistency",
        "status": "confirmed"
      }
    ],
    "questions": [],
    "constraints": []
  },
  "based_on_event_id": "event_uuid",
  "created_at": "2024-01-20T10:00:00Z"
}
```

### Refresh Working View

Force create a new working view snapshot.

```http
POST /api/cases/{case_id}/refresh/
Authorization: Bearer {token}
```

---

## Signals API (Phase 1)

### List Signals

```http
GET /api/signals/
Authorization: Bearer {token}
```

**Query params:**
- `case_id`: Filter by case
- `thread_id`: Filter by thread
- `type`: Filter by type (Assumption|Question|Constraint|etc.)
- `status`: Filter by status (suggested|confirmed|rejected)

**Response:**
```json
[
  {
    "id": "uuid",
    "event": "event_uuid",
    "type": "Assumption",
    "text": "We need strong consistency guarantees",
    "normalized_text": "we need strong consistency guarantees",
    "span": {"message_id": "uuid", "start": 0, "end": 50},
    "confidence": 0.85,
    "status": "suggested",
    "dedupe_key": "hash...",
    "case": "case_uuid",
    "thread": "thread_uuid",
    "created_at": "2024-01-20T10:00:00Z"
  }
]
```

### Confirm Signal

Change signal status from `suggested` to `confirmed`.

```http
POST /api/signals/{signal_id}/confirm/
Authorization: Bearer {token}
```

**Response:** Updated signal object

### Reject Signal

Change signal status from `suggested` to `rejected`.
This creates a `RejectedSignalFingerprint` to prevent re-suggesting.

```http
POST /api/signals/{signal_id}/reject/
Authorization: Bearer {token}
```

### Edit Signal Text

```http
PATCH /api/signals/{signal_id}/edit/
Authorization: Bearer {token}
Content-Type: application/json

{
  "text": "Updated assumption text"
}
```

---

## Events API

Events are read-only (created automatically by the system).

### List Events

```http
GET /api/events/
Authorization: Bearer {token}
```

**Query params:**
- `case_id`: Filter by case
- `thread_id`: Filter by thread
- `correlation_id`: Filter by workflow
- `type`: Filter by event type

**Response:**
```json
[
  {
    "id": "uuid",
    "timestamp": "2024-01-20T10:00:00.123Z",
    "actor_type": "user",
    "actor_id": "user_uuid",
    "type": "CaseCreated",
    "payload": {
      "title": "My Case",
      "position": "...",
      "stakes": "high"
    },
    "correlation_id": "uuid",
    "case_id": "case_uuid",
    "thread_id": null
  }
]
```

### Get Case Timeline

```http
GET /api/events/case/{case_id}/timeline/
Authorization: Bearer {token}
```

Returns all events for a case in chronological order.

### Get Thread Timeline

```http
GET /api/events/thread/{thread_id}/timeline/
Authorization: Bearer {token}
```

Returns all events for a thread in chronological order.

---

## Event Types Reference

### Chat Events

- `UserMessageCreated`: User sends a message
- `AssistantMessageCreated`: Assistant responds

### Case Events

- `CaseCreated`: New case created
- `CasePatched`: Case fields updated
- `CaseLinkedToThread`: Case linked to a thread

### Signal Events (Phase 1)

- `SignalExtracted`: Signal extracted from message
- `SignalsLinkedToCase`: Signals linked to case
- `SignalStatusChanged`: Signal confirmed/rejected
- `SignalEdited`: Signal text edited

### WorkingView Events

- `WorkingViewMaterialized`: New snapshot created

### Workflow Events

- `WorkflowStarted`: Async workflow started
- `WorkflowCompleted`: Async workflow completed

---

## Chat Streaming API

### Unified Stream (SSE)

Primary endpoint for chat interaction. Returns a Server-Sent Events stream with chat response, reflection, signals, and action hints from a single LLM call.

```http
POST /api/chat/threads/{thread_id}/unified-stream/
Authorization: Bearer {token}
Content-Type: application/json
Accept: text/event-stream

{
  "content": "What are the key risks here?",
  "context": {
    "mode": "case",
    "caseId": "uuid",
    "inquiryId": "uuid"
  }
}
```

**SSE Events:**
- `response_chunk`: `{ "delta": "text token" }`
- `reflection_chunk`: `{ "delta": "reflection token" }`
- `signals`: `{ "signals": [{ "type": "Assumption", "text": "...", "confidence": 0.8 }] }`
- `action_hints`: `{ "action_hints": [{ "type": "suggest_case", "reason": "...", "data": {...} }] }`
- `done`: `{ "message_id": "uuid", "reflection_id": "uuid", "signals_count": 3 }`
- `error`: `{ "message": "Error description" }`

See [CHAT_STREAMING_ARCHITECTURE.md](../architecture/CHAT_STREAMING_ARCHITECTURE.md) for full pipeline details.

---

## Inquiries API

### List Inquiries

```http
GET /api/inquiries/
Authorization: Bearer {token}
```

**Query params:**
- `case_id`: Filter by case
- `status`: Filter by status (open|investigating|resolved|archived)

### Create Inquiry

```http
POST /api/inquiries/
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Is the contractor faster than our team?",
  "case": "case_uuid",
  "elevation_reason": "user_created"
}
```

### Resolve Inquiry

```http
POST /api/inquiries/{id}/resolve/
Authorization: Bearer {token}
Content-Type: application/json

{
  "conclusion": "Yes, based on evidence from benchmarks...",
  "conclusion_confidence": 0.85
}
```

### Reopen Inquiry

```http
POST /api/inquiries/{id}/reopen/
Authorization: Bearer {token}
```

### Add Evidence to Inquiry

```http
POST /api/inquiries/{id}/add-evidence/
Authorization: Bearer {token}
Content-Type: application/json

{
  "evidence_text": "User observation from conversation",
  "direction": "supports",
  "strength": 0.7
}
```

### Update Dependencies

```http
POST /api/inquiries/{id}/update-dependencies/
Authorization: Bearer {token}
Content-Type: application/json

{
  "blocked_by": ["inquiry-uuid-1", "inquiry-uuid-2"]
}
```

### Get Dependency Graph

```http
GET /api/inquiries/{id}/dependency-graph/
Authorization: Bearer {token}
```

### Generate Investigation Plan

```http
POST /api/inquiries/{id}/generate_investigation_plan/
Authorization: Bearer {token}
Content-Type: application/json

{
  "brief_context": "Optional context from the brief"
}
```

### Generate Conclusion

```http
POST /api/inquiries/{id}/generate_conclusion/
Authorization: Bearer {token}
```

---

## Evidence API

### List Evidence

```http
GET /api/evidence/
Authorization: Bearer {token}
```

**Query params:**
- `inquiry`: Filter by inquiry UUID
- `direction`: Filter by direction (supports|contradicts|neutral)
- `document`: Filter by source document UUID

### Create Evidence

```http
POST /api/evidence/
Authorization: Bearer {token}
Content-Type: application/json

{
  "inquiry": "inquiry_uuid",
  "evidence_type": "observation",
  "evidence_text": "Based on benchmarks...",
  "direction": "supports",
  "strength": 0.8
}
```

### Cite Document as Evidence

```http
POST /api/evidence/cite_document/
Authorization: Bearer {token}
Content-Type: application/json

{
  "inquiry_id": "uuid",
  "document_id": "uuid",
  "chunk_ids": ["uuid1", "uuid2"],
  "evidence_text": "User interpretation",
  "direction": "supports",
  "strength": 0.8,
  "thread_id": "uuid"
}
```

---

## Objections API

### List Objections

```http
GET /api/objections/
Authorization: Bearer {token}
```

**Query params:**
- `inquiry`: Filter by inquiry UUID
- `status`: Filter by status
- `source`: Filter by source

### Address Objection

```http
POST /api/objections/{id}/address/
Authorization: Bearer {token}
Content-Type: application/json

{
  "addressed_how": "We resolved this by gathering additional benchmark data..."
}
```

### Dismiss Objection

```http
POST /api/objections/{id}/dismiss/
Authorization: Bearer {token}
```

---

## Projects API

### List/Create Projects

```http
GET /api/projects/
POST /api/projects/
Authorization: Bearer {token}
```

**Create body:**
```json
{
  "title": "Q1 Strategy",
  "description": "Quarterly planning decisions"
}
```

**Note:** DELETE performs soft delete (sets `is_archived=True`).

### Refresh Project Stats

```http
POST /api/projects/{id}/refresh_stats/
Authorization: Bearer {token}
```

---

## Documents API

### List/Create Documents

```http
GET /api/documents/
POST /api/documents/
Authorization: Bearer {token}
```

**Query params:**
- `project_id`: Filter by project
- `case_id`: Filter by case

**Create:** Supports file upload via multipart form data.

### Search Within Document

```http
POST /api/documents/{id}/search/
Authorization: Bearer {token}
Content-Type: application/json

{
  "query": "search terms"
}
```

### Get Document Chunks

```http
GET /api/documents/{id}/chunks/
Authorization: Bearer {token}
```

---

## Skills API

### List/Create Skills

```http
GET /api/skills/
POST /api/skills/
Authorization: Bearer {token}
```

Multi-level access control: public, organization, or user-owned skills.

### Create New Version

```http
POST /api/skills/{id}/create_version/
Authorization: Bearer {token}
Content-Type: application/json

{
  "skill_md_content": "# Skill Name\n...",
  "resources": {},
  "changelog": "Updated decision framework"
}
```

### List Versions

```http
GET /api/skills/{id}/versions/
Authorization: Bearer {token}
```

### Suggest Skills for Case

```http
POST /api/skills/suggest_for_case/
Authorization: Bearer {token}
Content-Type: application/json

{
  "case_id": "uuid"
}
```

### Spawn Case from Skill

```http
POST /api/skills/{id}/spawn_case/
Authorization: Bearer {token}
```

### Fork / Promote Skill

```http
POST /api/skills/{id}/fork/
POST /api/skills/{id}/promote/
Authorization: Bearer {token}
```

---

## Cases API (Additional Endpoints)

These extend the base Cases CRUD documented above.

### Scaffold Case

```http
POST /api/cases/scaffold/
Authorization: Bearer {token}
Content-Type: application/json

{
  "project_id": "uuid",
  "thread_id": "uuid",
  "mode": "chat"
}
```

Or minimal mode:
```json
{
  "project_id": "uuid",
  "title": "Decision title",
  "decision_question": "What should we do about...?",
  "mode": "minimal"
}
```

### Evolve Brief (Recompute Grounding)

```http
POST /api/cases/{id}/evolve-brief/
Authorization: Bearer {token}
```

Returns grounding delta with updated sections, new/resolved annotations, and readiness changes.

### Get Evidence Landscape

```http
GET /api/cases/{id}/evidence-landscape/
Authorization: Bearer {token}
```

Returns evidence counts, assumption validation status, inquiry progress, and unlinked claims.

### Readiness Checklist

```http
GET /api/cases/{id}/readiness-checklist/
POST /api/cases/{id}/readiness-checklist/
Authorization: Bearer {token}
```

GET returns items + progress. POST creates new checklist item.

### Update Checklist Item

```http
PATCH /api/cases/{id}/readiness-checklist/{item_id}/
DELETE /api/cases/{id}/readiness-checklist/{item_id}/
Authorization: Bearer {token}
```

### User Confidence

```http
PATCH /api/cases/{id}/user-confidence/
Authorization: Bearer {token}
Content-Type: application/json

{
  "user_confidence": 75,
  "what_would_change_mind": "If benchmarks showed..."
}
```

### Premortem

```http
PATCH /api/cases/{id}/premortem/
Authorization: Bearer {token}
Content-Type: application/json

{
  "premortem_text": "This could fail if..."
}
```

### Export Brief

```http
GET /api/cases/{id}/export/?type=full
GET /api/cases/{id}/export/?type=executive_summary
GET /api/cases/{id}/export/?type=per_section&sections=sf-abc123,sf-def456
Authorization: Bearer {token}
```

---

## Event Types Reference (Updated)

### Chat Events

- `UserMessageCreated`: User sends a message
- `AssistantMessageCreated`: Assistant responds

### Case Events

- `CaseCreated`: New case created
- `CasePatched`: Case fields updated
- `CaseLinkedToThread`: Case linked to a thread
- `CaseScaffolded`: Case scaffolded from chat or minimal input

### Signal Events

- `SignalExtracted`: Signal extracted from message
- `SignalsLinkedToCase`: Signals linked to case
- `SignalStatusChanged`: Signal confirmed/rejected
- `SignalEdited`: Signal text edited

### Agent Events

- `AgentWorkflowStarted`: Specialized agent spawned
- `ConversationAnalyzedForAgent`: Inflection detection ran

### Workflow Events

- `WorkflowStarted`: Async workflow started
- `WorkflowCompleted`: Async workflow completed (includes unified analysis)

### Structure Events

- `StructureSuggested`: Structure detection suggested case/inquiry creation

### WorkingView Events

- `WorkingViewMaterialized`: New snapshot created

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

Common status codes:
- `400`: Bad Request (validation error)
- `401`: Unauthorized (missing/invalid token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `500`: Internal Server Error

---

## Pagination

List endpoints support pagination:

**Query params:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50)

**Response:**
```json
{
  "count": 100,
  "next": "http://localhost:8000/api/cases/?page=2",
  "previous": null,
  "results": [...]
}
```

---

## Rate Limiting

Currently no rate limiting in development.
Production will enforce limits per user/IP.

---

## Webhooks (Future)

Phase 2+ will support webhooks for:
- Case state changes
- Signal extraction completion
- Working view updates
