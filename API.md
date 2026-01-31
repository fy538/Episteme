# Episteme API Documentation

Complete API reference for Phase 0 & Phase 1.

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
