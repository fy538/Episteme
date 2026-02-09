# Episteme Documentation

> A rigorous "work state" layer between chat and outcomes — capturing intent, assumptions, evidence, and decisions as durable objects.

## Quick Links

| I want to... | Go to |
|--------------|-------|
| Set up local dev | [Local Dev Runbook](./guides/LOCAL_DEV_RUNBOOK.md) |
| Understand the API | [API Reference](./reference/API.md) |
| Deploy to production | [Deployment Guide](./guides/DEPLOYMENT_GUIDE.md) |
| Understand the product | [Product Vision](./concepts/PRODUCT_VISION.md) |
| Learn core concepts | [Evidence vs Signals](./concepts/EVIDENCE_VS_SIGNALS.md) |

---

## Architecture

System deep-dives — how things work under the hood.

| Document | What it covers |
|----------|---------------|
| [Intelligence Engine](./architecture/INTELLIGENCE_ENGINE.md) | Unified analysis, agent orchestration, signal extraction, interventions |
| [Chat Streaming](./architecture/CHAT_STREAMING_ARCHITECTURE.md) | SSE pipeline, sectioned XML parsing, optimistic rendering, timeouts |
| [Auto-Reasoning & Cascade](./architecture/AUTO_REASONING_CASCADE.md) | The three-way feedback loop: evidence → assumption status → brief grounding |
| [Brief Grounding & Evidence Linking](./architecture/BRIEF_GROUNDING_AND_EVIDENCE_LINKING.md) | Evidence quality tracking, claim-to-signal matching, scaffold service |
| [Event Sourcing](./architecture/EVENT_SOURCING.md) | Append-only event store, provenance vs operational, correlation IDs |
| [Celery Workflows](./architecture/CELERY_WORKFLOWS.md) | Async task orchestration, research pipeline, signal processing |
| [Inquiries System](./architecture/INQUIRIES_SYSTEM.md) | Evidence accumulation, objections, dependencies, resolution flow |
| [Evidence Ingestion & Companion](./architecture/EVIDENCE_INGESTION_AND_COMPANION.md) | Universal ingestion pipeline, graph analyzer, session receipts |
| [Investigation Plan Service](./architecture/INVESTIGATION_PLAN_SERVICE.md) | Versioned plans, assumption-signal sync, stage progression |
| [Agent Orchestration](./architecture/AGENT_ORCHESTRATION_DESIGN.md) | Multi-agent design, inflection detection, research loop |
| [Intelligent Agent Routing](./architecture/INTELLIGENT_AGENT_ROUTING.md) | Agent selection logic and routing decisions |
| [Skill System](./architecture/SKILL_SYSTEM_ARCHITECTURE.md) | Deep customization via domain-specific skills |
| [Memory Integration](./architecture/MEMORY_INTEGRATION.md) | Long-term memory system (**aspirational** — partially implemented) |

## Concepts

Domain concepts, design philosophy, and product direction.

| Document | What it covers |
|----------|---------------|
| [Product Vision](./concepts/PRODUCT_VISION.md) | Product strategy, UX principles, phased roadmap |
| [Design Principles](./concepts/DESIGN_PRINCIPLES.md) | Core design philosophy and patterns |
| [Evidence vs Signals](./concepts/EVIDENCE_VS_SIGNALS.md) | The fundamental conceptual model — what signals and evidence are |

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

## Strategy

Business and product strategy.

| Document | What it covers |
|----------|---------------|
| [Product Funnel](./strategy/PRODUCT_FUNNEL.md) | Three-layer product vision: Dump & Discover → Investigation → Decision Agent. The "journey is the product" framing. |
| [User Personas](./strategy/USER_PERSONAS.md) | Three primary personas: consultant, tech lead, solo founder — jobs, pains, feature mapping |
| [Competitive Positioning & Moat](./strategy/COMPETITIVE_POSITIONING.md) | Landscape analysis, moat layers, replication estimates, honest comparison vs. Claude/ChatGPT projects |
| [Workflow & Value Map](./strategy/WORKFLOW_AND_VALUE_MAP.md) | Complete 4-stage journey, feature-to-value mapping, metacognitive stack |
| [Category & Positioning](./strategy/CATEGORY_AND_POSITIONING.md) | Founder-first positioning, category options, messaging hierarchy, language guide |
| [Context Modes & Output Skills](./strategy/CONTEXT_MODES_AND_OUTPUT_SKILLS.md) | Chat mode design across contexts, output skill pattern, mode × skill × scope interaction |
| [Solo Founder AI Strategy](./strategy/SOLO_FOUNDER_AI_STRATEGY.md) | Cost-optimized model selection for solo operation |

## Research

External research and analysis that informed design decisions.

| Document | What it covers |
|----------|---------------|
| [Navigation Architecture Analysis](./research/navigation-architecture-analysis.md) | Analysis of navigation patterns |
| [Agentic Chat Architectures](./research/research-agentic-chat-architectures.md) | Research on agentic chat system designs |

## Plans

Aspirational designs and future roadmap items. **Not current behavior.**

| Document | What it covers |
|----------|---------------|
| [Core User Loop Improvements](./plans/CORE_USER_LOOP_IMPROVEMENTS.md) | Proposed UX improvements |
| [Dashboard Implementation Plan](./plans/DASHBOARD_IMPLEMENTATION_PLAN.md) | Dashboard design for future implementation |
| [Readiness Phase 2-3 Plan](./plans/READINESS_PHASE_2_3_PLAN.md) | Future phase planning |

---

## Documentation Standards

- **Tier 1** (always update): README, LOCAL_DEV_RUNBOOK, API.md, DEPLOYMENT_GUIDE
- **Tier 2** (update when changed): Architecture docs, product vision, design documents
- **Tier 3** (ephemeral): Migration guides, troubleshooting notes

See the root [README.md](../README.md) for project setup and development commands.
