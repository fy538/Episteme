# Episteme

A rigorous "work state" layer between chat and outcomes—capturing intent, assumptions, evidence, and decisions as durable objects.

## Project Structure

```
episteme/
├── backend/           # Django backend
├── frontend/          # Next.js frontend (coming soon)
├── docs/              # Documentation files
├── docker/            # Docker configurations
└── README.md          # Project overview
```

## Documentation

### User Guides
- [Local Dev Runbook](./docs/LOCAL_DEV_RUNBOOK.md) - Daily development operations
- [API Reference](./docs/API.md) - Complete REST API documentation
- [Deployment Guide](./docs/DEPLOYMENT_GUIDE.md) - Production deployment
- [Fly.io Deployment](./docs/FLY_IO_DEPLOYMENT.md) - Fly.io specific guide

### Architecture & Design
- [Product Vision & UX](./docs/PRODUCT_VISION_AND_UX.md) - Product strategy and vision
- [Skill System Architecture](./docs/SKILL_SYSTEM_ARCHITECTURE.md) - Deep customization system
- [Agent Orchestration](./docs/AGENT_ORCHESTRATION_DESIGN.md) - Multi-agent design
- [Intelligent Agent Routing](./docs/INTELLIGENT_AGENT_ROUTING.md) - Agent selection logic
- [Evidence vs Signals](./docs/EVIDENCE_VS_SIGNALS.md) - Core conceptual model
- [Memory Integration](./docs/MEMORY_INTEGRATION.md) - Long-term memory system

### Backend Documentation
- [AI Services Quick Reference](./docs/backend/AI_SERVICES_QUICK_REFERENCE.md) - Using PydanticAI
- [PydanticAI Migration](./docs/backend/PYDANTIC_AI_MIGRATION.md) - Migration guide
- [Document System Quickstart](./docs/backend/QUICKSTART_DOCUMENT_SYSTEM.md) - Document processing

### Frontend Documentation
- [Frontend README](./frontend/README.md) - Frontend overview
- [Design System](./frontend/DESIGN_SYSTEM.md) - UI components and tokens
- [Testing Guide](./frontend/TESTING_GUIDE.md) - Testing practices

### Strategic Documentation
- [Solo Founder AI Strategy](./docs/SOLO_FOUNDER_AI_STRATEGY.md) - Cost-optimized model selection
- [Getting Started with AI](./docs/GETTING_STARTED_WITH_AI.md) - 5-minute AI setup

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

## Logging & Observability

- Backend logs to stdout; production uses JSON formatting.
- Request logs include `X-Correlation-ID` for tracing.
- Celery logs task start, completion, retries, and failures.
- Backend Sentry config: `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`.
- Frontend Sentry config: `NEXT_PUBLIC_SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_ENVIRONMENT`, `NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE`.

## Architecture Overview

### Core Primitives

1. **Event** - Append-only timestamped facts (source of truth)
2. **Signal** - Atomic units of meaning extracted from events
3. **Evidence** - Facts, metrics, and benchmarks extracted from documents
4. **Case** - Durable work object for investigations
5. **Artifact** - Block-based, version-controlled output (briefs, research)
6. **WorkingView** - Materialized snapshots for fast rendering

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

- ✅ RecursiveTokenChunker (512 tokens, 15% overlap)
- ✅ Token counting with tiktoken
- ✅ PostgreSQL embedding storage (28x faster than external DBs)
- ✅ Context linking (prev/next chunks)
- ✅ EmbeddingService abstraction

### ✅ Phase 2.2 - 2.4 (Complete - Evidence, Graph, Artifacts)

- ✅ **Evidence Model**: Facts, metrics, and credibility ratings
- ✅ **Knowledge Graph**: Signal dependencies and contradictions
- ✅ **Artifacts**: Block-based versioning and publishing
- ✅ **Google ADK Agents**: Multi-agent research, critique, and brief generation

### 🔄 Phase 3 (In Progress - Frontend)

- ✅ Next.js 14 + TypeScript infrastructure
- ✅ API Client (Chat, Cases, Signals, Documents)
- ✅ Chat Interface (Threads, Messages)
- ✅ Case Workspace (Basic view, Side panel)
- [ ] Evidence UI (Ratings, Source linking)
- [ ] Artifact Editor (Block-based editing, versioning)
- [ ] ADK Agent Control Panel (Trigger research/critique)

## Tech Stack

**Backend**:
- Django 5.0 + Django REST Framework
- PostgreSQL (event store + application data)
- Redis (Celery broker)
- Celery (background jobs)

**AI Infrastructure**:
- **PydanticAI**: Structured LLM outputs for one-off services (extraction, titles, summaries)
- **Google ADK**: Agentic workflows (research, debates, critiques)
- **OpenAI GPT-4o-mini**: Fast extraction and classification
- **Sentence Transformers**: Local semantic embeddings

**Frontend**:
- Next.js 14 + TypeScript
- Tailwind CSS
- React Query
- Zustand (State Management)
- Tiptap (Editor Foundation)

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

### Google ADK: Multi-Agent Workflows

For complex, multi-step reasoning requiring agent coordination:
- ✅ Research generation (multi-source analysis)
- ✅ Multi-perspective debates (simulating stakeholders)
- ✅ Critique generation (devil's advocate)
- 🔄 Background monitoring agents

**Why ADK?**
- Built for agent orchestration
- Clean supervisor/worker patterns
- Perfect for long-horizon tasks

See `docs/backend/PYDANTIC_AI_MIGRATION.md` for implementation details.

## Documentation Strategy

We maintain a **lean, useful documentation set** focused on helping developers, not preserving AI session transcripts.

### Documentation Rules

**Never Create:**
- Completion status files (`*_COMPLETE.md`, `*_SUMMARY.md`, `*_IMPLEMENTATION.md`)
- Session notes or implementation logs
- Multiple versions of the same content
- Temporary migration guides that outlive their purpose

**Always Maintain:**
- User-facing guides (setup, deployment, API reference)
- Architecture decision records for significant design choices
- Product vision and strategy documents

**Monthly Cleanup:**
- Delete any `*_COMPLETE.md` or `*_FIX.md` files
- Consolidate duplicate content
- Remove outdated migration guides
- Keep total docs under 25 files

### Documentation Tiers

**Tier 1 (Always Update):**
- README.md, LOCAL_DEV_RUNBOOK.md, API.md, DEPLOYMENT_GUIDE.md

**Tier 2 (Update When Changed):**
- Architecture docs, product vision, design documents

**Tier 3 (Ephemeral - Delete After Use):**
- Migration guides, troubleshooting notes, session summaries

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
