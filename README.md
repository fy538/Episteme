# Episteme

A rigorous "work state" layer between chat and outcomes—capturing intent, assumptions, evidence, and decisions as durable objects.

## Project Structure

```
episteme/
├── backend/           # Django backend
├── frontend/          # Next.js frontend (coming soon)
└── docker/            # Docker configurations
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### Local Development Setup

1. **Clone the repository** (if from git):
   ```bash
   git clone <repo-url>
   cd episteme
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env if needed
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Run migrations**:
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

5. **Create superuser**:
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

6. **Access the application**:
   - Backend API: http://localhost:8000
   - Django Admin: http://localhost:8000/admin
   - API Docs: http://localhost:8000/api/ (coming soon)

### Development Commands

**View logs**:
```bash
docker-compose logs -f backend
docker-compose logs -f celery
```

**Run tests**:
```bash
docker-compose exec backend pytest
```

**Django shell**:
```bash
docker-compose exec backend python manage.py shell
```

**Create migrations**:
```bash
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate
```

**Stop services**:
```bash
docker-compose down
```

**Reset database** (careful - deletes all data):
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec backend python manage.py migrate
```

## Architecture Overview

### Core Primitives

1. **Event** - Append-only timestamped facts (source of truth)
2. **Signal** - Atomic units of meaning extracted from events
3. **Case** - Durable work object for investigations
4. **WorkingView** - Materialized snapshots for fast rendering

### ✅ Phase 0 (Complete)

- ✅ Event store foundation (append-only)
- ✅ Chat persistence (threads + messages)
- ✅ Case CRUD with provenance
- ✅ Background job infrastructure (Celery)
- ✅ Full REST API with JWT auth
- ✅ Event sourcing with dual-write pattern

### ✅ Phase 1 (Complete)

- ✅ Signal model with types (Assumption, Question, Constraint, etc.)
- ✅ Signal status lifecycle (suggested → confirmed/rejected)
- ✅ WorkingView materialization
- ✅ RejectedSignalFingerprint for deduplication
- ✅ Complete API for signal management
- ✅ Signal extraction with LLM + embeddings
- ✅ Temporal indexing (sequence_index)
- ✅ Semantic embeddings (sentence-transformers)
- ✅ Read-time deduplication (similarity.py)

### ✅ Phase 1.5 (Complete - AI Infrastructure)

- ✅ **PydanticAI** integration for structured LLM outputs
- ✅ Type-safe signal extraction (OpenAI GPT-4o-mini)
- ✅ Auto-title generation for chats and cases
- ✅ Conversation summarization service
- ✅ Free local embeddings (all-MiniLM-L6-v2)
- ✅ Similarity search utilities
- ✅ Async/await extraction pipeline

### ✅ Phase 2 (Complete - Projects, Documents, Query)

- ✅ Project model (top-level organization)
- ✅ Document model (upload/URL/text ingestion)
- ✅ Document processing (PDF, DOCX, TXT)
- ✅ Query engine (semantic search across all signals)
- ✅ Multi-source signals (chat + documents)
- ✅ Full hierarchy (Project → Case → Thread/Document → Signals)

### ✅ Phase 2.1 (Complete - Research-Backed Chunking)

- ✅ RecursiveTokenChunker (512 tokens, 15% overlap - research optimal)
- ✅ Token counting with tiktoken (accurate token-based chunking)
- ✅ PostgreSQL embedding storage (28x faster than external DBs)
- ✅ Context linking (prev/next chunks for quality retrieval)
- ✅ EmbeddingService abstraction (supports PostgreSQL, pgvector, Pinecone)
- ✅ Re-chunking management command
- ✅ Comprehensive tests

### Phase 3 (Next - Frontend & Analytics)

- [ ] Next.js frontend
- [ ] Case workspace UI with chips
- [ ] "What changed" diff visualization
- [ ] Signal clustering (themes)
- [ ] Timeline abstractions
- [ ] Artifacts (user-created outputs)

## Tech Stack

**Backend**:
- Django 5.0 + Django REST Framework
- PostgreSQL (event store + application data)
- Redis (Celery broker)
- Celery (background jobs)

**AI Infrastructure**:
- **PydanticAI**: Structured LLM outputs for one-off services (extraction, titles, summaries)
- **Google ADK** (coming soon): Agentic workflows (research, debates, critiques)
- **OpenAI GPT-4o-mini**: Fast extraction and classification
- **Sentence Transformers**: Local semantic embeddings

**Frontend** (coming soon):
- Next.js 14 + TypeScript
- Tailwind CSS
- React Query

## AI Architecture Strategy

Episteme uses a **two-framework approach** for clean separation of concerns:

### PydanticAI: Structured One-Off Services

For deterministic, single-call LLM tasks with strict schemas:
- ✅ Signal extraction from messages
- ✅ Auto-generate titles for chats and cases
- ✅ Summarize conversations
- ✅ Classify message intent
- ✅ Any task requiring validated, structured output

**Why PydanticAI?**
- Type-safe with Pydantic models
- Automatic validation and retries
- Zero JSON parsing boilerplate
- Perfect for Django/DRF projects

**Example**:
```python
from apps.common.ai_services import generate_chat_title

title = await generate_chat_title(messages)
# Returns: "Database Architecture Decision"
```

### Google ADK: Multi-Agent Workflows (Coming Soon)

For complex, multi-step reasoning requiring agent coordination:
- 🔄 Research generation (multi-source analysis)
- 🔄 Multi-perspective debates (simulating stakeholders)
- 🔄 Critique generation (devil's advocate)
- 🔄 Background monitoring agents

**Why ADK?**
- Built for agent orchestration
- Clean supervisor/worker patterns
- Perfect for long-horizon tasks

See `backend/PYDANTIC_AI_MIGRATION.md` for implementation details.

## Development Guidelines

### Event Sourcing

Events are append-only. Never delete or modify events. To "change" something, emit a new event.

### API Design

- RESTful endpoints under `/api/`
- JWT authentication
- Consistent error responses

### Code Style

```bash
# Format code
docker-compose exec backend black .
docker-compose exec backend isort .

# Lint
docker-compose exec backend flake8
```

## License

[License TBD]
