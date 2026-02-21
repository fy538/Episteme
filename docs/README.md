# Episteme Documentation

> A decision investigation platform that helps you think through complex situations with structure, evidence, and grounded confidence — from orientation to outcome tracking.

## Quick Links

| I want to... | Go to |
|--------------|-------|
| Understand the product | [Product Vision](./concepts/PRODUCT_VISION.md) |
| See the competitive landscape | [Competitive Positioning](./strategy/COMPETITIVE_POSITIONING.md) |
| Understand the workflow | [Workflow & Value Map](./strategy/WORKFLOW_AND_VALUE_MAP.md) |
| Understand the architecture | [Three-Level Architecture](./architecture/THREE_LEVEL_ARCHITECTURE.md) |
| Set up local dev | [Local Dev Runbook](./guides/LOCAL_DEV_RUNBOOK.md) |
| Understand the API | [API Reference](./reference/API.md) |
| Deploy to production | [Deployment Guide](./guides/DEPLOYMENT_GUIDE.md) |

---

## Implementation Status

The product is built across nine implementation plans:

| Plan | Layer | Status | What It Implements |
|------|-------|--------|-------------------|
| Plan 1 | Foundation | Implemented | Hierarchical document clustering (RAPTOR-style) |
| Plan 2 | Foundation | Implemented | Organic companion (structure-aware agentic chat) |
| Plan 3 | Foundation | Implemented | Case extraction (CEAT framework) |
| Plan 4 | Feature Polish | Designed | RAG citations |
| Plan 5 | Feature Polish | Designed | Case graph visualization (ReactFlow) |
| Plan 6 | Feature Polish | Designed | Hierarchy refresh + change detection |
| Plan 7 | Product Completeness | Designed | Project discovery + onboarding |
| Plan 8 | Product Completeness | Designed | Case creation preview + companion bridge |
| Plan 9 | Product Completeness | Designed | Decision capture + outcome tracking |

---

## Concepts

Domain concepts, design philosophy, and product direction.

| Document | What it covers |
|----------|---------------|
| [Product Vision](./concepts/PRODUCT_VISION.md) | Three-level architecture, decision capture, design principles, implementation status |
| [Design Principles](./concepts/DESIGN_PRINCIPLES.md) | Core design philosophy and patterns |
| [Evidence vs Signals](./concepts/EVIDENCE_VS_SIGNALS.md) | The fundamental conceptual model — what signals and evidence are |
| [Decision State Architecture](./DECISION_STATE_ARCHITECTURE.md) | Architecture doctrine: "Projects are for memory. Cases are for thinking." |

## Architecture

System deep-dives — how things work under the hood.

| Document | What it covers |
|----------|---------------|
| [Three-Level Architecture](./architecture/THREE_LEVEL_ARCHITECTURE.md) | Master overview: how Project, Chat, and Case work together; data flow; tech stack |
| [Chat Streaming](./architecture/CHAT_STREAMING_ARCHITECTURE.md) | SSE pipeline, sectioned XML parsing, optimistic rendering, timeouts |
| [Event Sourcing](./architecture/EVENT_SOURCING.md) | Append-only event store, provenance vs operational, correlation IDs |
| [Celery Workflows](./architecture/CELERY_WORKFLOWS.md) | Async task orchestration, research pipeline, signal processing |
| [Evidence Ingestion & Companion](./architecture/EVIDENCE_INGESTION_AND_COMPANION.md) | Universal ingestion pipeline, companion service |
| [Extraction Engine](./architecture/EXTRACTION_ENGINE.md) | Four extraction pipelines, CEAT framework |

### Archived Architecture Docs

These docs describe systems that have been superseded or are aspirational:

| Document | Status |
|----------|--------|
| [Intelligence Engine](./archive/replaced-by-graph/INTELLIGENCE_ENGINE.md) | Replaced by CEAT extraction |
| [Brief Grounding & Evidence Linking](./archive/replaced-by-graph/BRIEF_GROUNDING_AND_EVIDENCE_LINKING.md) | Replaced by graph model |
| [Inquiries System](./archive/replaced-by-graph/INQUIRIES_SYSTEM.md) | Replaced by case investigation |
| [Investigation Plan Service](./archive/replaced-by-graph/INVESTIGATION_PLAN_SERVICE.md) | Replaced by case stages |
| [Auto-Reasoning & Cascade](./archive/phase2/AUTO_REASONING_CASCADE.md) | Phase 2 — not yet implemented |
| [Agent Orchestration](./archive/phase2/AGENT_ORCHESTRATION_DESIGN.md) | Phase 2 — not yet implemented |
| [Intelligent Agent Routing](./archive/phase2/INTELLIGENT_AGENT_ROUTING.md) | Phase 2 — not yet implemented |
| [Skill System](./archive/phase2/SKILL_SYSTEM_ARCHITECTURE.md) | Phase 2 — not yet implemented |
| [Memory Integration](./archive/aspirational/MEMORY_INTEGRATION.md) | Aspirational — partially implemented |

## Strategy

Business and product strategy.

| Document | What it covers |
|----------|---------------|
| [Product Funnel](./strategy/PRODUCT_FUNNEL.md) | Five-stage journey: Orient → Explore → Investigate → Decide → Learn |
| [Workflow & Value Map](./strategy/WORKFLOW_AND_VALUE_MAP.md) | Complete workflow with feature-to-value mapping |
| [Competitive Positioning & Moat](./strategy/COMPETITIVE_POSITIONING.md) | Landscape analysis including NotebookLM, moat layers, decision capture as differentiator |
| [Category & Positioning](./strategy/CATEGORY_AND_POSITIONING.md) | Category: Decision Investigation Platform, messaging hierarchy, language guide |
| [User Personas](./strategy/USER_PERSONAS.md) | Solo founder persona — jobs, pains, feature mapping |
| [Solo Founder AI Strategy](./strategy/SOLO_FOUNDER_AI_STRATEGY.md) | Cost-optimized model selection for solo operation |

## Guides

How-to and operational docs for getting things done.

| Document | What it covers |
|----------|---------------|
| [Local Dev Runbook](./guides/LOCAL_DEV_RUNBOOK.md) | Daily development operations, common commands |
| [Deployment Guide](./guides/DEPLOYMENT_GUIDE.md) | Production deployment process |
| [Fly.io Deployment](./guides/FLY_IO_DEPLOYMENT.md) | Fly.io-specific deployment guide |
| [Getting Started with AI](./guides/GETTING_STARTED_WITH_AI.md) | 5-minute AI infrastructure setup |
| [Settings Page Design](./guides/SETTINGS_PAGE_DESIGN.md) | Settings UI patterns and implementation |

## Reference

API specs, quick-reference lookups, and technical details.

| Document | What it covers |
|----------|---------------|
| [API Reference](./reference/API.md) | Complete REST API — all endpoints, auth, streaming, events |
| [Auth & Unified Search](./reference/AUTH_AND_SEARCH.md) | JWT auth, user preferences, semantic search across all content |
| [AI Services Quick Reference](./reference/AI_SERVICES_QUICK_REFERENCE.md) | Using PydanticAI services — patterns and examples |
| [AI System Architecture](./reference/AI_SYSTEM_ARCHITECTURE.md) | LLM provider abstraction, model configuration |
| [PydanticAI Migration](./reference/PYDANTIC_AI_MIGRATION.md) | Migration guide from raw LLM calls to PydanticAI |
| [Document System Quickstart](./reference/QUICKSTART_DOCUMENT_SYSTEM.md) | Document processing pipeline — PDF, DOCX, chunking |

## Research

External research and analysis that informed design decisions.

| Document | What it covers |
|----------|---------------|
| [Navigation Architecture Analysis](./research/navigation-architecture-analysis.md) | Analysis of navigation patterns |
| [Agentic Chat Architectures](./research/research-agentic-chat-architectures.md) | Research on agentic chat system designs |

## Plans

Implementation plans for features. See also the `PLAN_*.md` files in the project root.

| Document | What it covers |
|----------|---------------|
| [Core User Loop Improvements](./plans/CORE_USER_LOOP_IMPROVEMENTS.md) | Proposed UX improvements |

### Archived Plans

| Document | Status |
|----------|--------|
| [Dashboard Implementation Plan](./archive/phase2/DASHBOARD_IMPLEMENTATION_PLAN.md) | Phase 2 |
| [Readiness Phase 2-3 Plan](./archive/phase2/READINESS_PHASE_2_3_PLAN.md) | Phase 2 |
| [Context Modes & Output Skills](./archive/phase2/CONTEXT_MODES_AND_OUTPUT_SKILLS.md) | Phase 2 |

---

## Documentation Standards

- **Tier 1** (always update): README, LOCAL_DEV_RUNBOOK, API.md, DEPLOYMENT_GUIDE
- **Tier 2** (update when changed): Architecture docs, product vision, strategy documents
- **Tier 3** (ephemeral): Migration guides, troubleshooting notes

See the root [README.md](../README.md) for project setup and development commands.
