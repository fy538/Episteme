# AI System Architecture

> Current state of Episteme's AI agent system. Last updated: February 2025.

---

## 1. Overview

Episteme's AI system is a **config-driven, multi-step research engine** built on three principles:

1. **Config changes behavior, code stays the same** — Skills inject domain knowledge via YAML config + markdown prompts. No code changes needed for new verticals.
2. **Provider-agnostic** — Any LLM with a `generate()` method works. Switch Anthropic ↔ OpenAI with one config line.
3. **Event-sourced** — Append-only event store is the source of truth. Checkpoints, trajectories, and progress are all events.

### System Diagram

```
User Chat
  │
  ├─ Direct LLM response (simple questions)
  │
  └─ Agent Routing ──────────────────────────────────────────────┐
       │                                                          │
       ▼                                                          │
  InflectionDetector (LLM analyzes conversation)                  │
       │                                                          │
       ▼                                                          │
  Suggestion: "Run Research Agent?" ─── confirmation.py           │
       │                                                          │
       ▼                                                          │
  AgentOrchestrator ─── AgentRegistry                             │
       │                   │                                      │
       ▼                   ▼                                      │
  Celery Task ──── generate_research_artifact_v2                  │
       │                                                          │
       ▼                                                          │
  ┌──────────────────────────────────────────────────────┐        │
  │  ResearchLoop (config-driven)                        │        │
  │                                                      │        │
  │  ┌──────┐   ┌────────┐   ┌─────────┐   ┌─────────┐  │        │
  │  │ Plan │──▶│ Search │──▶│ Extract │──▶│Evaluate │  │        │
  │  └──────┘   └────────┘   └─────────┘   └────┬────┘  │        │
  │                                              │       │        │
  │                  ┌───────────────┐     ┌─────▼────┐  │        │
  │                  │  Synthesize   │◀────│Complete? │  │        │
  │                  └───────┬───────┘     └──────────┘  │        │
  │                          │                           │        │
  └──────────────────────────┼───────────────────────────┘        │
                             │                                    │
                             ▼                                    │
                    Artifact + ArtifactVersion                    │
                             │                                    │
                             ▼                                    │
                    Replace placeholder in chat ◀─────────────────┘
```

### Key Data Flow

```
Skill YAML ──▶ ResearchConfig ──▶ ResearchLoop behavior
Skill Markdown ──▶ prompt_extension ──▶ LLM system prompt
Case context ──▶ ResearchContext ──▶ Plan decomposition
Tool config ──▶ resolve_tools_for_config() ──▶ Search backends
```

---

## 2. LLM Providers

**Location:** `backend/apps/common/llm_providers/`

### Provider Protocol

Any object with `generate()` qualifies as a provider:

```python
class LLMProviderProtocol(Protocol):
    async def generate(
        self,
        messages: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4000,
        temperature: float = 0.3,
    ) -> str: ...
```

Providers that only expose `stream_chat()` (async iterator of chunks) are supported via automatic fallback that collects the stream.

### Implementations

| Provider | File | Default Model | Features |
|----------|------|---------------|----------|
| **Anthropic** | `anthropic_provider.py` | `claude-haiku-4-5` | Prompt caching (75-85% TTFT reduction, 90% cost reduction) |
| **OpenAI** | `openai_provider.py` | `gpt-4o-mini` | Standard chat completions |

### Context Windows

| Model | Tokens |
|-------|--------|
| Claude Haiku/Sonnet 4.5 | 200,000 |
| Claude Opus 4.6 | 200,000 |
| GPT-4o / GPT-4o-mini | 128,000 |

### Factory

```python
from apps.common.llm_providers.factory import get_llm_provider

provider = get_llm_provider('chat')  # Reads from settings.AI_MODELS['chat']
# Format: "anthropic:claude-haiku-4-5" or "openai:gpt-4o-mini"
```

---

## 3. Research Loop (v2)

**Location:** `backend/apps/agents/research_loop.py`

The core engine. Runs a multi-step loop: **Plan → Search → Extract → Evaluate → (iterate?) → Contrary → Synthesize**.

### Steps

| Step | What It Does | LLM Call? |
|------|-------------|-----------|
| **Plan** | Decompose question into 2-5 sub-queries with strategy | Yes |
| **Search** | Execute queries in parallel via tools (web, documents, MCP, sub-agents) | No (tool calls) |
| **Extract** | Pull structured fields from search results | Yes |
| **Evaluate** | Score findings on relevance + quality using rubric | Yes |
| **Compact** | Condense findings when token budget runs low (tier 1: score filter, tier 2: LLM digest) | Conditional |
| **Completeness** | Check if research is done (min sources + semantic evaluation of `done_when`) | Yes |
| **Contrary** | Search for contradicting evidence (if configured) | Yes |
| **Synthesize** | Write final markdown report with citations | Yes |

### Iteration Loop

The search/extract/evaluate steps repeat up to `config.search.max_iterations` (default 5). Each iteration can add follow-up queries from citation relationships. The loop exits when:

- Completeness check passes (`done_when` condition met)
- Budget ceiling reached (`max_sources` or `max_search_rounds`)
- Context budget exhausted (triggers continuation)
- No more queries to execute

### Key Classes

| Class | Purpose |
|-------|---------|
| `ResearchLoop` | Main orchestrator — `run(question, context)` and `resume_from_checkpoint()` |
| `ResearchConfig` | All behavior configuration (from skills) |
| `ResearchContext` | Case metadata passed to plan step |
| `ResearchPlan` / `SubQuery` | Decomposed strategy |
| `Finding` / `ScoredFinding` | Extracted + scored facts |
| `ResearchResult` | Final output (content, blocks, findings, metadata) |

### Shared Iteration Method

Both `run()` and `resume_from_checkpoint()` delegate to `_iterate_and_synthesize()` — a single method containing the search/extract/evaluate/compact/contrary/synthesize logic. This eliminates code duplication and ensures resumed loops have full feature parity (trajectory recording, context budget checks, etc.).

---

## 4. Agent Types

### Active

| Agent | Engine | File | Status |
|-------|--------|------|--------|
| **Research v2** | ResearchLoop (multi-step) | `research_loop.py` | **Primary** |

### Legacy (deprecated, still has callers)

| Agent | Engine | File | Status |
|-------|--------|------|--------|
| **Research v1** | Google ADK (single-shot) | `adk_agents.py` + `research_agent.py` | Deprecated — use v2 |
| **Critique** | Google ADK | `adk_agents.py` + `critique_agent.py` | Deprecated — callers in `document_generator.py`, `cases/views.py` |
| **Brief** | Google ADK | `adk_agents.py` | Deprecated |
| **Debate** | Google ADK | `debate_agent.py` | Used by `document_generator.py` |

### What They Produce

- **Research**: Markdown report with sections (Executive Summary, Key Findings, Supporting Evidence, Contrary Views, Limitations, Sources)
- **Critique**: Unexamined assumptions, evidence gaps, logical issues, missing considerations
- **Brief**: Decision framework synthesizing signals + evidence
- **Debate**: Multi-perspective analysis with persona positions + synthesis

---

## 5. Tool System

**Location:** `backend/apps/agents/research_tools.py`

### ResearchTool Protocol

```python
class ResearchTool(ABC):
    name: str

    async def execute(
        self,
        query: str,
        domains: list[str] | None = None,
        excluded_domains: list[str] | None = None,
        max_results: int = 5,
    ) -> list[SearchResult]: ...
```

### Implementations

| Tool | File | Backend | Purpose |
|------|------|---------|---------|
| **WebSearchTool** | `research_tools.py` | Exa API (primary) → Tavily (fallback) → LLM knowledge | Web search |
| **DocumentSearchTool** | `research_tools.py` | Embedding similarity on case documents | Internal document search |
| **MCPResearchTool** | `mcp_tool.py` | Any MCP server (stdio/SSE) | External data sources (Westlaw, SEC EDGAR, etc.) |
| **SubAgentTool** | `sub_agent_tool.py` | Inline agent execution | Hierarchical agent composition |

### Tool Resolution

`resolve_tools_for_config(sources_config, case_id, user_id)` builds the tool list:

1. Always includes `WebSearchTool`
2. Adds `DocumentSearchTool` if `case_id` is provided
3. Adds `SubAgentTool` wrappers for each entry in `sources.sub_agents`
4. Adds `MCPResearchTool` wrappers for each entry in `sources.mcp_servers`

### MCP Integration

```yaml
# Skill config example
episteme:
  research_config:
    sources:
      mcp_servers:
        - name: westlaw
          url: https://mcp.westlaw.com/sse    # SSE transport
          tool_filter: [search_cases, get_case_text]
        - name: local_db
          command: npx -y @my/mcp-server       # stdio transport
```

`MCPClient` handles JSON-RPC protocol: initialize → list_tools → call_tool. Supports both stdio (subprocess) and SSE (httpx) transports.

### Sub-Agent Composition

`SubAgentTool` wraps agent invocation as a tool so the research loop can spawn sub-agents (e.g., run a critique agent as part of research):

- **Depth cap**: Max 2 levels to prevent circular invocation
- **Timeout**: 120 seconds per sub-agent call
- **Inline execution**: Runs in-process (not via Celery) so parent loop can await results

---

## 6. Agent Registry

**Location:** `backend/apps/agents/registry.py`

Replaces hardcoded `if/elif` dispatch in orchestrator with pluggable registration.

```python
@dataclass
class AgentDescriptor:
    name: str                    # "research", "critique", "brief"
    description: str
    entry_point: Any             # Celery task reference
    required_params: list[str]
    can_be_sub_agent: bool
```

### Default Registrations

| Name | Task | Sub-Agent Eligible |
|------|------|--------------------|
| `research` | `generate_research_artifact_v2` | Yes |
| `critique` | `generate_critique_artifact` | Yes |
| `brief` | `generate_brief_artifact` | No |

### Usage

```python
from apps.agents.registry import AgentRegistry, register_default_agents

register_default_agents()

descriptor = AgentRegistry.get("research")
descriptor.entry_point.delay(case_id=..., topic=..., user_id=...)
```

---

## 7. Skill System

**Location:** `backend/apps/skills/`

Skills are the primary mechanism for configuring agent behavior without code changes.

### How Skills Configure Agents

```
SKILL.md file
  ├─ YAML frontmatter
  │   └─ episteme.research_config → ResearchConfig dataclass
  │       ├─ sources: what to search
  │       ├─ search: how to decompose queries
  │       ├─ extract: what fields to pull
  │       ├─ evaluate: quality rubric
  │       ├─ completeness: when to stop
  │       └─ output: report format
  │
  └─ Markdown body → prompt_extension (injected into LLM system prompt)
```

### Injection Flow

```python
# 1. Load skills for case
active_skills, skill_context = await _load_skills_and_inject(case, 'research')

# 2. skill_context contains:
{
    'system_prompt_extension': str,     # Markdown body from SKILL.md
    'research_config': ResearchConfig,  # Typed config from YAML
    'custom_signal_types': [...],
    'evidence_standards': {...},
    'artifact_template': {...},
}

# 3. Config drives loop behavior, prompt drives LLM behavior
loop = ResearchLoop(
    config=skill_context['research_config'],
    prompt_extension=skill_context['system_prompt_extension'],
    ...
)
```

### Multi-Skill Merging

When multiple skills are active, `_merge_research_configs()` merges them:

- **Sources**: Union of primary/supplementary lists (deduped)
- **Search/Extract/Evaluate**: Later skills override earlier ones
- **Completeness**: Boolean OR for flags (e.g., `require_contrary_check`)
- **Prompt extensions**: Concatenated with section headers

### Skill Lifecycle

```
Personal (draft) → Personal (active) → Team → Organization → Public
                         ↕
                    Fork (copy)
                         ↕
                  Case ↔ Skill (bidirectional conversion)
```

---

## 8. Orchestration

**Location:** `backend/apps/agents/orchestrator.py`

### Agent Routing Pipeline

```
User sends message in chat
         │
         ▼
InflectionDetector.analyze_for_agent_need()
  - LLM analyzes last N messages
  - Detects: research_depth, critique_assumptions, synthesis_decision, none
  - Returns: suggested_agent, confidence, reasoning, suggested_topic
         │
         ▼
AgentOrchestrator creates inline suggestion:
  "I can run a Research Agent to investigate this. [Run] [No thanks]"
         │
         ▼
confirmation.py: check_for_agent_confirmation()
  - LLM classifies user response: CONFIRM / DECLINE / CLARIFY / IGNORE
         │
         ▼
If CONFIRM:
  AgentOrchestrator.run_agent_in_chat()
    1. Create placeholder message in chat
    2. Emit AGENT_WORKFLOW_STARTED event
    3. Dispatch to registry → Celery task
    4. Return immediately (async execution)
         │
         ▼
Background Celery Task:
    1. Load skills → build config + prompt extension
    2. Create ResearchLoop
    3. Run loop (emits AGENT_PROGRESS events → placeholder updates)
    4. Create Artifact + ArtifactVersion
    5. Emit AGENT_COMPLETED event
    6. Replace placeholder with results
```

### Intelligence Layer

| Detector | File | Purpose |
|----------|------|---------|
| **InflectionDetector** | `inflection_detector.py` | Detects when conversation needs agent escalation |
| **StructureDetector** | `structure_detector.py` | Detects when case/inquiry structure would help |
| **Confirmation** | `confirmation.py` | Natural language intent detection (confirm/decline/clarify) |

All three use LLM-based semantic analysis (not regex patterns).

---

## 9. Harness Infrastructure

The "agent harness" is the infrastructure layer wrapping the LLM, analogous to an operating system for agents.

### Checkpointing & Resume

**Location:** `backend/apps/agents/checkpoint.py`

Serialize loop state to event store after each phase boundary. On retry, reconstruct from latest checkpoint.

```python
# Automatic — loop emits checkpoints at plan/evaluate/compact boundaries
loop = ResearchLoop(checkpoint_callback=save_checkpoint, ...)

# Resume if checkpoint exists
checkpoint = load_latest_checkpoint(correlation_id)
if checkpoint:
    result = await ResearchLoop.resume_from_checkpoint(checkpoint, ...)
```

`ResearchCheckpoint` stores: correlation_id, question, iteration, phase, plan_dict, findings_dicts, config_dict, context_dict, prompt_extension.

### Trajectory Capture

**Location:** `backend/apps/agents/trajectory.py`

Record structured decision trajectories at each step for prompt improvement and fine-tuning.

```python
recorder = TrajectoryRecorder(correlation_id="...")

# Automatically recorded at 6 steps: plan, search, extract, evaluate, completeness, synthesize
# Each event captures: input_summary, output_summary, decision_rationale, metrics, duration_ms

# Saved as single AGENT_TRAJECTORY event per workflow
recorder.save_to_events(case_id=case_id)
```

Opt-in: pass `trajectory_recorder=None` for zero overhead.

### Context Budget Tracking

**Location:** `backend/apps/agents/context_manager.py`

Prevents context window overflow via proactive tracking.

```python
ContextBudgetTracker:
  - Estimates token usage (~4 chars/token)
  - Tracks: used_by_prompts, used_by_findings, used_by_plan
  - Triggers continuation when < 10% remaining
```

### Session Continuity

When context budget is exhausted:

1. `build_handoff_summary()` — LLM compresses findings + plan into summary
2. `create_continuation_context()` — Builds prompt for new session
3. New ResearchLoop runs with continuation context
4. Results merged (findings combined, latest synthesis used)

Safety: Max 2 continuations (3 total sessions).

---

## 10. Event Store

**Location:** `backend/apps/events/models.py`

Append-only, immutable event log. Source of truth for all state changes.

### Agent Event Lifecycle

```
AGENT_WORKFLOW_STARTED    → Agent launched from chat
AGENT_PROGRESS (×N)       → Step updates (planning, searching, evaluating...)
AGENT_CHECKPOINT (×N)     → Loop state snapshots (at plan/evaluate/compact boundaries)
AGENT_COMPLETED           → Agent finished, artifact created
AGENT_FAILED              → Agent error
AGENT_TRAJECTORY          → Full decision trajectory (one per workflow)
```

### Event Types

Events are organized into two groups:

- **Actively emitted** (~25 types): Chat, case lifecycle, inquiries, signals, workflows, agents, structure detection
- **Reserved / not yet emitted** (~20 types): Document lifecycle, evidence, objections, citations, agent routing — defined for planned features, preserved in migrations

---

## 11. Artifact Generation

**Location:** `backend/apps/artifacts/workflows.py`

### Workflow Tasks

| Task | Engine | Status |
|------|--------|--------|
| `generate_research_artifact_v2` | ResearchLoop | **Active** |
| `generate_research_artifact` | ADK | Deprecated (emits `DeprecationWarning`) |
| `generate_critique_artifact` | ADK | Deprecated |
| `generate_brief_artifact` | ADK | Deprecated |

### Shared Helpers

```python
_create_artifact_with_version(
    title, artifact_type, case, user, generated_by,
    generation_prompt, blocks, generation_time_ms,
    input_signals_qs, input_evidence_qs, skills_used,
) → (artifact, version)

_load_skills_and_inject(case, agent_type) → (active_skills, skill_context)
```

### v2 Workflow Flow

1. Gather case context (signals, evidence)
2. Load skills → build config + prompt extension
3. Set up provider + tools
4. Check for existing checkpoint (resume support)
5. Create trajectory recorder
6. Run loop (or resume from checkpoint)
7. Handle continuations if context exhausted
8. Create Artifact + ArtifactVersion
9. Update placeholder in chat with results

---

## 12. Configuration Reference

### ResearchConfig Hierarchy

```
ResearchConfig
├── sources: SourcesConfig
│   ├── primary: [SourceEntry]        # e.g. [{type: "court_opinions", domains: [...]}]
│   ├── supplementary: [SourceEntry]
│   ├── trusted_publishers: [TrustedPublisher]
│   ├── excluded_domains: [str]
│   ├── sub_agents: [str]             # e.g. ["critique"]
│   └── mcp_servers: [MCPServerConfig]
├── search: SearchConfig
│   ├── decomposition: str            # simple | issue_spotting | hypothesis_driven | ...
│   ├── parallel_branches: int        # default 3
│   ├── max_iterations: int           # default 5
│   ├── budget: BudgetConfig          # max_sources=25, max_search_rounds=8
│   ├── follow_citations: bool
│   └── citation_depth: int           # default 2
├── extract: ExtractConfig
│   ├── fields: [ExtractionField]     # named fields with type (text/boolean/choice/numeric)
│   └── relationships: [str]
├── evaluate: EvaluateConfig
│   ├── mode: str                     # hierarchical | corroborative | hybrid
│   ├── quality_rubric: str           # prose rubric for LLM
│   └── criteria: [EvaluationCriterion]
├── completeness: CompletenessConfig
│   ├── min_sources: int              # default 3
│   ├── max_sources: int              # default 25
│   ├── require_contrary_check: bool
│   ├── require_source_diversity: bool
│   └── done_when: str                # prose condition for LLM
└── output: OutputConfig
    ├── format: str                   # memo | brief | report | table | annotated_bibliography
    ├── sections: [str]
    ├── citation_style: str           # inline | footnote | bluebook | apa | chicago | mla
    └── target_length: str            # brief | standard | detailed
```

### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `MAX_FOLLOWUPS_PER_ROUND` | 3 | Follow-up queries per iteration |
| `MAX_RESULTS_PER_QUERY` | 5 | Search results per query |
| `MAX_CONTRARY_FINDINGS` | 5 | Findings sent to contrary check |
| `MAX_CITATION_LEADS_PER_ROUND` | 5 | Citation follow-ups per round |
| `COMPACTION_TOKEN_THRESHOLD` | 60,000 | Token estimate triggering compaction |
| `COMPACT_KEEP_RATIO` | 0.6 | Fraction of findings kept after compaction |
| `MIN_FINDINGS_FOR_COMPACTION` | 20 | Don't compact below this count |
| `MIN_FINDINGS_AFTER_COMPACT` | 10 | Floor after compaction |
| `MAX_SUB_AGENT_DEPTH` | 2 | Hierarchical agent nesting limit |
| `SUB_AGENT_TIMEOUT_SECONDS` | 120 | Sub-agent execution timeout |
| `MAX_CONTINUATIONS` | 2 | Session continuity limit (3 total sessions) |

---

## 13. File Reference

### Core Agent Engine

| File | Purpose | Key Exports |
|------|---------|-------------|
| `agents/research_loop.py` | Multi-step research engine | `ResearchLoop`, `ResearchResult`, `ResearchContext`, `ScoredFinding` |
| `agents/research_config.py` | Declarative configuration | `ResearchConfig`, `SourcesConfig`, `SearchConfig`, `MCPServerConfig` |
| `agents/research_prompts.py` | LLM prompt templates | `build_plan_prompt`, `build_extract_prompt`, `build_evaluate_prompt`, `build_synthesize_prompt` |
| `agents/research_tools.py` | Pluggable search backends | `ResearchTool`, `WebSearchTool`, `DocumentSearchTool`, `resolve_tools_for_config` |

### Harness Infrastructure

| File | Purpose | Key Exports |
|------|---------|-------------|
| `agents/checkpoint.py` | Crash recovery via event store | `ResearchCheckpoint`, `save_checkpoint`, `load_latest_checkpoint` |
| `agents/trajectory.py` | Decision recording for analysis | `TrajectoryRecorder`, `TrajectoryEvent` |
| `agents/context_manager.py` | Context window management | `ContextBudgetTracker`, `build_handoff_summary`, `create_continuation_context` |
| `agents/registry.py` | Pluggable agent dispatch | `AgentRegistry`, `AgentDescriptor`, `register_default_agents` |
| `agents/sub_agent_tool.py` | Hierarchical composition | `SubAgentTool` |
| `agents/mcp_client.py` | MCP protocol client | `MCPClient`, `MCPToolDefinition` |
| `agents/mcp_tool.py` | MCP as ResearchTool | `MCPResearchTool` |

### Intelligence & Routing

| File | Purpose | Key Exports |
|------|---------|-------------|
| `agents/orchestrator.py` | Workflow orchestration | `AgentOrchestrator` |
| `agents/inflection_detector.py` | Detects agent need from conversation | `InflectionDetector` |
| `agents/structure_detector.py` | Detects structure readiness | `StructureReadinessDetector` |
| `agents/confirmation.py` | Intent classification | `check_for_agent_confirmation` |
| `agents/messages.py` | Suggestion message helpers | `create_agent_suggestion_message` |

### Legacy Agents (Deprecated)

| File | Purpose | Status |
|------|---------|--------|
| `agents/adk_agents.py` | Google ADK agent wrappers | Active callers exist |
| `agents/research_agent.py` | ADK research implementation | Used by `document_generator.py` |
| `agents/critique_agent.py` | ADK critique implementation | Used by `document_generator.py` |
| `agents/debate_agent.py` | ADK debate simulation | Used by `document_generator.py` |
| `agents/document_generator.py` | Orchestrates ADK agents | Used by `tasks/workflows.py`, `cases/views.py` |

### Supporting Systems

| File | Purpose |
|------|---------|
| `common/llm_providers/base.py` | Provider protocol + context window registry |
| `common/llm_providers/factory.py` | `get_llm_provider()` factory |
| `common/llm_providers/anthropic_provider.py` | Claude with prompt caching |
| `common/llm_providers/openai_provider.py` | OpenAI chat completions |
| `skills/injection.py` | `build_skill_context()`, `_merge_research_configs()` |
| `skills/conversion.py` | Case ↔ Skill bidirectional conversion |
| `artifacts/workflows.py` | Celery tasks for artifact generation |
| `events/models.py` | Append-only event store |

### Tests

| File | Tests | Coverage |
|------|-------|----------|
| `agents/tests/test_checkpoint.py` | 15 | Serialization, persistence, loop integration, resume, resume+trajectory |
| `agents/tests/test_registry.py` | 22 | Descriptor, CRUD, singleton, lazy task, sub-agent, resolve_tools |
| `agents/tests/test_trajectory.py` | 12 | Event serialization, recorder lifecycle, loop integration |
| `agents/tests/test_mcp.py` | 21 | Client, tool normalization, config, resolve_tools |
| `agents/tests/test_context_manager.py` | 18 | Budget, tracker, handoff, continuation |
| `agents/tests/helpers.py` | — | Shared `make_test_provider()`, `make_test_tool()` |
