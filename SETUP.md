# Episteme Setup Guide

## Phase 0 & Phase 1 - Complete Setup

This guide will walk you through setting up Episteme with all Phase 0 and Phase 1 models.

### What's Included

**Phase 0 Models:**
- Event (append-only event store)
- ChatThread & Message (chat conversations)
- Case (durable work objects)

**Phase 1 Models:**
- Signal (extracted meaning)
- WorkingView (materialized snapshots)
- RejectedSignalFingerprint (deduplication)

---

## Quick Start

### 1. Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

The default values should work for local development.

### 2. Start Docker Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (database)
- Redis (Celery broker)
- Django backend
- Celery worker
- Celery beat

### 3. Run Database Migrations

```bash
# Create migrations
docker-compose exec backend python manage.py makemigrations

# Apply migrations
docker-compose exec backend python manage.py migrate
```

### 4. Create a Superuser

```bash
docker-compose exec backend python manage.py createsuperuser
```

Follow the prompts to create an admin user.

### 5. Verify Setup

Check that all services are running:

```bash
docker-compose ps
```

All services should show "Up" status.

---

## API Endpoints

### Authentication

```
POST /api/auth/token/          # Get JWT token
POST /api/auth/token/refresh/  # Refresh token
GET  /api/auth/me/             # Get current user
```

### Chat

```
GET    /api/chat/threads/                  # List threads
POST   /api/chat/threads/                  # Create thread
GET    /api/chat/threads/{id}/             # Get thread with messages
POST   /api/chat/threads/{id}/messages/    # Send message
```

### Cases

```
GET    /api/cases/              # List cases
POST   /api/cases/              # Create case
GET    /api/cases/{id}/         # Get case
PATCH  /api/cases/{id}/         # Update case
GET    /api/cases/{id}/work/    # Get working view
POST   /api/cases/{id}/refresh/ # Refresh working view
```

### Signals (Phase 1)

```
GET    /api/signals/?case_id={id}     # List signals for case
POST   /api/signals/{id}/confirm/     # Confirm signal
POST   /api/signals/{id}/reject/      # Reject signal
PATCH  /api/signals/{id}/edit/        # Edit signal text
```

### Events

```
GET /api/events/?case_id={id}        # Get case events
GET /api/events/?thread_id={id}      # Get thread events
GET /api/events/case/{id}/timeline/  # Case timeline
```

---

## Testing the Setup

### 1. Get an Auth Token

```bash
# Get token
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}'
```

Save the `access` token for subsequent requests.

### 2. Create a Chat Thread

```bash
curl -X POST http://localhost:8000/api/chat/threads/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Thread"}'
```

### 3. Send a Message

```bash
curl -X POST http://localhost:8000/api/chat/threads/THREAD_ID/messages/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Hello, Episteme!"}'
```

The assistant will respond asynchronously via Celery.

### 4. Create a Case

```bash
curl -X POST http://localhost:8000/api/cases/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Test Case",
    "position":"We should use Postgres for the event store",
    "stakes":"high",
    "thread_id":"THREAD_ID"
  }'
```

### 5. Check Events

```bash
curl http://localhost:8000/api/events/?case_id=CASE_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

You should see `CaseCreated` and `CaseLinkedToThread` events.

---

## Development Workflow

### View Logs

```bash
# Backend logs
docker-compose logs -f backend

# Celery worker logs
docker-compose logs -f celery

# All logs
docker-compose logs -f
```

### Django Shell

```bash
docker-compose exec backend python manage.py shell
```

Example session:

```python
from apps.events.models import Event
from apps.chat.models import ChatThread
from apps.cases.models import Case

# List all events
Event.objects.all()

# Get latest case
Case.objects.last()
```

### Run Tests

```bash
docker-compose exec backend pytest
```

### Code Formatting

```bash
# Format code
docker-compose exec backend black .
docker-compose exec backend isort .

# Check lint
docker-compose exec backend flake8
```

### Database Operations

```bash
# Create new migrations after model changes
docker-compose exec backend python manage.py makemigrations

# Apply migrations
docker-compose exec backend python manage.py migrate

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
docker-compose exec backend python manage.py migrate
```

---

## Architecture Notes

### Event Sourcing Pattern

Events are the **single source of truth**. Every important action creates an event:

1. User sends message → `UserMessageCreated` event → Message row created
2. User creates case → `CaseCreated` event → Case row created
3. User confirms signal → `SignalStatusChanged` event → Signal updated

**Why?**
- Complete audit trail
- Can rebuild state from events
- Enables "what changed" diffs
- Supports replay and debugging

### Dual-Write Pattern (Chat & Cases)

For performance, we maintain read-optimized tables alongside events:

- **Events table**: source of truth (append-only)
- **Message/Case tables**: read models (optimized for queries)

If they get out of sync, you can rebuild from events.

### Phase 1: Signal Extraction (Stub)

Signal extraction is currently stubbed. To implement:

1. Add LLM integration (OpenAI/Anthropic) in `apps/signals/extractors.py`
2. Update `tasks/workflows.py` to call extraction after messages
3. Implement deduplication logic using `dedupe_key`

---

## Next Steps

### Phase 1 Completion Tasks

1. **Implement Signal Extraction**
   - Add LLM API calls
   - Extract assumptions, questions, constraints
   - Implement dedupe logic

2. **Build Frontend**
   - Next.js chat interface
   - Case panel component
   - Chip UI (confirm/edit/reject)

3. **Add Tests**
   - Unit tests for services
   - Integration tests for workflows
   - API endpoint tests

4. **Monitoring**
   - Add logging
   - Set up error tracking (Sentry)
   - Performance monitoring

### Troubleshooting

**Services won't start:**
```bash
docker-compose down
docker-compose up -d
docker-compose logs
```

**Database connection errors:**
- Check that `db` service is healthy: `docker-compose ps`
- Check DATABASE_URL in `.env`

**Migrations failing:**
```bash
# Drop all tables and start fresh
docker-compose down -v
docker-compose up -d
docker-compose exec backend python manage.py migrate
```

**Celery not processing tasks:**
```bash
docker-compose logs celery
# Check that Redis is running
docker-compose ps redis
```

---

## Resources

- Django Docs: https://docs.djangoproject.com/
- DRF Docs: https://www.django-rest-framework.org/
- Celery Docs: https://docs.celeryproject.org/
- PostgreSQL JSONB: https://www.postgresql.org/docs/current/datatype-json.html
