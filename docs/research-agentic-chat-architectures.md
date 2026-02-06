# Agentic Chat Architectures: How Frontier AI Companies Implement Multi-Agent Systems

> Research compiled February 2026. Focuses on architectural patterns from production systems.

---

## Table of Contents

1. [Multi-Agent Architectures Overview](#1-multi-agent-architectures-overview)
2. [Agent Specialization Patterns](#2-agent-specialization-patterns)
3. [Orchestration Patterns](#3-orchestration-patterns)
4. [Tool-Use Patterns](#4-tool-use-patterns)
5. [Context Management](#5-context-management)
6. [User Experience Patterns](#6-user-experience-patterns)
7. [Specific Implementations](#7-specific-implementations)
   - [Anthropic Claude Agent SDK & Research](#71-anthropic-claude-agent-sdk--multi-agent-research)
   - [OpenAI Agents SDK](#72-openai-agents-sdk)
   - [Google Agent Development Kit (ADK)](#73-google-agent-development-kit-adk)
   - [Microsoft Copilot Studio](#74-microsoft-copilot-studio)
   - [Cursor](#75-cursor)
   - [Replit](#76-replit)
   - [Notion](#77-notion)
   - [Linear](#78-linear)
   - [Perplexity](#79-perplexity)

---

## 1. Multi-Agent Architectures Overview

Across the industry, four dominant architectural patterns have emerged:

### Pattern A: Orchestrator-Worker (Fan-Out)
A lead/orchestrator agent decomposes a user query into subtasks, spawns specialized worker agents in parallel, and synthesizes their results. Used by **Anthropic Research**, **Perplexity Deep Research**, and **Google ADK Parallel agents**.

### Pattern B: Handoff Chain
A routing agent examines user intent and hands off the entire conversation to a specialized agent. The specialized agent runs to completion, then control returns. Used by **OpenAI Agents SDK**, **Microsoft Copilot connected agents**.

### Pattern C: Manager-Editor-Verifier
A manager agent plans work, editor agents execute individual tasks, and a verifier agent validates results with human feedback. Used by **Replit Agent**, and partially by **Cursor**.

### Pattern D: Pipeline (Sequential)
Agents execute in a fixed order like an assembly line (e.g., analyst -> architect -> implementer -> tester -> reviewer). Used by **Google ADK Sequential agents**, **Microsoft Copilot serial workflows**.

### Pattern E: Hierarchical Decomposition
Multi-level agent trees where high-level agents delegate to mid-level agents, which further delegate to leaf-level specialists. Used by **Google ADK**, **Microsoft Copilot embedded agents**.

Most production systems combine these patterns. For example, Anthropic's Research uses Pattern A (fan-out) with Pattern D (sequential post-processing via a CitationAgent).

---

## 2. Agent Specialization Patterns

### How Companies Separate Concerns

| Company | Specialization Approach |
|---------|------------------------|
| **Anthropic** | Lead agent (planning/synthesis) + Research subagents (search/filter) + CitationAgent (attribution) |
| **OpenAI** | Domain-specific agents (e.g., order-status agent, refund agent, FAQ agent) connected via handoffs |
| **Google ADK** | Coordinator agent + specialist agents (UI, API, DB) with workflow agents for control flow |
| **Microsoft** | Orchestrator + embedded subagents (internal) + connected agents (cross-org) |
| **Cursor** | Up to 8 parallel coding agents, each in isolated git worktrees |
| **Replit** | Manager agent + editor agents (coding) + verifier agent (validation/human feedback) |
| **Notion** | Central reasoning model coordinating modular sub-agents for search, edit, database ops |
| **Linear** | Triage agent (semantic search + LLM reasoning for issue routing/labeling) |
| **Perplexity** | Planner agent + search execution agents + ranking/filtering + synthesis agent |

### Common Specialization Categories
1. **Planning/Routing Agent** - Decomposes tasks, delegates work
2. **Research/Search Agent** - Gathers information from external sources
3. **Coding/Editing Agent** - Writes, modifies, and refactors code or documents
4. **Verification/Testing Agent** - Validates outputs, runs tests, checks quality
5. **Citation/Attribution Agent** - Ensures claims are properly sourced
6. **Synthesis Agent** - Aggregates results from multiple workers into a coherent response

---

## 3. Orchestration Patterns

### 3.1 Router/Dispatcher Pattern
A central LLM agent examines user intent and routes to the appropriate specialist.

**OpenAI Agents SDK implementation:**
- Agent receives user message
- LLM decides: produce final output, call a tool, or hand off to another agent
- Handoffs are modeled as tool calls: `transfer_to_agent("refund_specialist")`
- The Runner re-runs the loop with the new agent and accumulated context

**Google ADK implementation:**
- LLM agent generates `transfer_to_agent(agent_name='target')`
- Framework intercepts, locates target via `root_agent.find_agent()`
- Execution focus switches to the target agent
- Requires clear agent descriptions for informed routing

### 3.2 Fan-Out/Gather Pattern
Orchestrator spawns multiple workers in parallel, then aggregates.

**Anthropic Research implementation:**
- Lead agent (Claude Opus 4) spawns 3-5 subagents (Claude Sonnet 4) in parallel
- Each subagent gets: objective, output format, tool guidance, task boundaries
- Subagents explore independently with their own context windows
- Lead agent gathers results, determines if more research is needed
- Cuts research time by up to 90% for complex queries

### 3.3 Sequential Pipeline Pattern
Agents execute in strict order.

**Google ADK SequentialAgent:**
- Executes sub-agents one after another in predefined order
- Output of one agent passed as input to the next via shared session state
- `output_key` property automatically saves agent response to state

### 3.4 Loop/Iterative Pattern
Agents repeat until a condition is met.

**Google ADK LoopAgent:**
- Repeats sub-agent execution until `max_iterations` or `escalate=True`
- Generator-Critic pattern: one agent generates content, another reviews
- Loop breaks when review passes; feedback routes back otherwise

### 3.5 Effort-Scaling Pattern
**Anthropic** embeds explicit scaling rules in prompts:
- Simple fact-finding: 1 agent, 3-10 tool calls
- Direct comparisons: 2-4 subagents, 10-15 calls each
- Complex research: 10+ subagents with divided responsibilities

This is critical because agents naturally struggle to judge appropriate effort levels.

---

## 4. Tool-Use Patterns

### 4.1 Tool Categories Across Implementations

| Category | Examples | Used By |
|----------|----------|---------|
| **Search/Retrieval** | Web search, semantic search, vector DB queries | All |
| **Code Execution** | Terminal commands, sandboxed code interpreters | Cursor, Replit, Anthropic Agent SDK, Perplexity |
| **File System** | Read/write/edit files | Cursor, Replit, Anthropic Agent SDK |
| **Document Operations** | Create/edit pages, update databases | Notion, Linear |
| **External APIs** | Slack, GitHub, Google Drive, email | Notion, Linear, Microsoft Copilot |
| **Browser/Web** | Navigate, interact with web pages | Cursor, Anthropic Agent SDK |
| **Math/Computation** | Wolfram Alpha, code interpreters | Perplexity |

### 4.2 Tool Integration Approaches

**Function-as-Tool (OpenAI Agents SDK, Google ADK):**
- Any Python/TypeScript function can be a tool
- Automatic JSON schema generation from type annotations
- Pydantic-powered validation (OpenAI) or similar type checking

**MCP (Model Context Protocol) Integration:**
- Open standard backed by Anthropic, now adopted by Microsoft, Cursor, and others
- Standardizes how agents connect to external tools, data, and prompts
- Client-server architecture: MCP servers expose tools, agents are clients
- TypeScript SDKs available with growing ecosystem

**Custom DSL (Replit):**
- Instead of using standard function calling, Replit built a restricted Python-based DSL
- Agents generate code to invoke tools themselves
- This approach proved more reliable for their 30+ tool library with multiple arguments per tool

**Parallel Tool Execution:**
- Anthropic subagents execute 3+ tools simultaneously
- Cursor runs tests while editing code (parallelized tool use)
- Google ADK ParallelAgent runs tools concurrently with shared state

### 4.3 Tool Description Quality
Anthropic found that tool descriptions critically impact performance. Poor descriptions "can send agents down completely wrong paths." Each tool needs:
- Clear description of what it does
- When to use it vs. alternatives
- Expected input/output format
- Error handling guidance

---

## 5. Context Management

### 5.1 The Core Challenge
Long-running agents must work in discrete sessions, and each new session begins with no memory of what came before. Even frontier models will fail to build production-quality software with only a high-level prompt across multiple context windows.

### 5.2 Approaches by Company

**Anthropic - Structured Progress Files:**
- Initializer agent creates `claude-progress.txt` and initial git commit
- Coding agent reads progress file + git history at start of each session
- Makes incremental progress, then updates progress file
- Context compaction built into the Agent SDK to prevent window exhaustion

**Anthropic - Distributed Context (Research):**
- Each subagent has its own context window (separation of concerns)
- Lead agent saves plans to persistent memory before token limits hit
- When approaching limits, agents spawn fresh subagents with clean contexts
- Subagents store outputs externally, pass lightweight references to minimize loss
- Lead agent maintains state via external memory when conversations exceed 200K tokens

**OpenAI Agents SDK - Stateless with Explicit State:**
- Inspired by Swarm: no persistent state between calls
- Every handoff must include all context the next agent needs
- Structured state objects that persist across runs for personalization
- SQLAlchemy and encrypted session variants available

**Google ADK - Shared Session State:**
- Agents communicate through `context.state` dictionary
- `output_key` automatically saves agent responses to specified state keys
- ParallelAgent uses separate execution threads with shared session state
- Each parallel agent must write to unique keys to prevent race conditions

**Microsoft Copilot - Cross-Agent Context:**
- A2A protocol manages context across agents via `contextId`
- Limits inter-agent context to strictly necessary information
- Short-term memory management for parallel workflows

**Cursor - Git-Based Context:**
- Each parallel agent operates in its own git worktree
- Full copy of repo at current commit per agent
- `.cursor/worktrees.json` configures worktree setup (dependencies, environment)
- Results merged back via git operations

**Notion - Workspace as Memory:**
- Agents use Notion pages and databases as persistent memory
- Personalization page with instructions acts as a memory bank
- Can work across hundreds of pages simultaneously for up to 20 minutes

**Replit - Compressed Memory:**
- Dynamic prompt construction with memory compression
- Automatic commits at major steps for reversion capability
- Verifier agent maintains user feedback loop as external memory

### 5.3 Memory Taxonomy
Industry research identifies three memory layers:
1. **Working Memory** - Current context window, tool results, conversation state
2. **Short-Term Memory** - Session state, shared dictionaries, progress files
3. **Long-Term Memory** - Persistent databases, git history, user preference stores

### 5.4 Token Economics
- Multi-agent systems consume ~15x more tokens than standard chat (Anthropic)
- Token usage explains 80% of performance variance in research tasks
- Model quality matters more than token budget: Claude Sonnet 4 is a larger performance gain than doubling the token budget on Claude Sonnet 3.7
- Best suited for tasks where outcome value outweighs token cost

---

## 6. User Experience Patterns

### 6.1 Transparency Spectrum

Companies fall along a spectrum from "fully transparent" to "fully abstracted":

| Approach | Description | Examples |
|----------|-------------|----------|
| **Fully Transparent** | Show which agent is active, what it's doing, thinking trace | Linear (thinking panel), Cursor (per-agent progress) |
| **Progressive Disclosure** | Show status, reveal details on demand | Anthropic Research (expandable subagent progress) |
| **Task-Centric** | Show what's happening, not which agent | Notion (background task completion notifications) |
| **Fully Abstracted** | Single unified interface, agents invisible | Perplexity (user sees only the plan + final answer) |

### 6.2 Key UX Patterns

**Human-in-the-Loop:**
- Replit's verifier agent falls back to human interaction rather than autonomous decisions
- Cursor requires approval for shell commands not in allowlist
- Microsoft recommends human approval for high-impact cross-agent actions

**Human-on-the-Loop:**
- Cursor background agents run autonomously, notify on completion or when approval needed
- Notion agents work for up to 20 minutes in background, then report results
- Linear agent suggestions displayed alongside issues; human applies or rejects

**Confidence Visualization:**
- Traffic-light colors showing how certain the AI is
- Linear shows model reasoning alongside suggestions with alternative options
- Perplexity shows source citations with quality indicators

**Progressive Disclosure:**
- Show top-level status by default
- Expandable panels for detailed agent reasoning/trace
- Linear's thinking panel shows full research trace on demand

### 6.3 Design Principles (Industry Consensus)
1. Clearly show whether the agent or user is in control at any moment
2. Enable frictionless handoff of control while preserving workflow state
3. Provide unobtrusive prompts when the agent takes action autonomously
4. Multi-agent systems must communicate confidence, transparency, and control
5. The best design is often invisible (Mark Weiser's principle)

---

## 7. Specific Implementations

### 7.1 Anthropic Claude Agent SDK & Multi-Agent Research

**SDK Architecture:**
- Renamed from "Claude Code SDK" to "Claude Agent SDK" to reflect broader vision
- Core principle: give Claude access to a computer (terminal + filesystem)
- Context management via compaction (work on tasks without exhausting window)
- Filesystem-based configuration support

**Multi-Agent Research System:**
- **Lead Agent** (Claude Opus 4): Plans, decomposes, spawns subagents, synthesizes
  - Uses extended thinking to assess tools and query complexity
  - Saves plans to persistent memory before potential truncation
  - Determines if additional research rounds are needed
- **Subagents** (Claude Sonnet 4): Execute search, filter, explore
  - 3-5 spawned in parallel for complex queries
  - Each has own context window for separation of concerns
  - Use "interleaved thinking" to evaluate tool results
  - Execute 3+ tools simultaneously
- **CitationAgent**: Post-processing for source attribution
  - Identifies specific citation locations within documents
  - Ensures all claims are properly attributed
- **Performance**: Multi-agent outperforms single-agent by 90.2% on internal research eval
- **Failure Modes**: Agents try to do too much at once; mark features complete without testing

**Long-Running Agent Harness:**
- Two-fold solution: initializer agent + coding agent
- Initializer creates: `init.sh`, `claude-progress.txt`, initial git commit
- Coding agent: reads progress, makes incremental changes, updates artifacts
- Designed for multi-context-window work where each session starts fresh

**Best Practices:**
- Give each subagent one job; let orchestrator coordinate
- Orchestrator permissions: mostly "read and route"
- Define subagents with clear inputs/outputs and single goal
- Test-first discipline: testing agent writes tests, implementer makes them pass
- Dedicated code-review subagent for linting, complexity, security
- OpenTelemetry traces for prompts, tool invocations, token usage
- Rainbow deployments for updates without disrupting running agents

**Sources:**
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
- https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- https://platform.claude.com/docs/en/agent-sdk/overview

---

### 7.2 OpenAI Agents SDK

**Core Primitives:**
1. **Agents**: LLMs equipped with instructions and tools
2. **Handoffs**: Agents delegate to other agents (modeled as tool calls)
3. **Guardrails**: Input/output validation running in parallel with execution
4. **Tools**: Function tools (auto-schema from Python functions) + MCP server integration
5. **Tracing**: Built-in visualization, debugging, monitoring

**Agent Loop (Runner):**
1. LLM called for current agent with current input
2. If LLM returns `final_output` -> loop ends, result returned
3. If LLM does a handoff -> current agent/input updated, loop re-runs
4. If LLM produces tool calls -> tools executed, results appended, loop re-runs

**Handoff Mechanism:**
- Handoffs are explicit agent-to-agent delegation
- Modeled as function calls that the Runner intercepts
- Target agent receives accumulated conversation context
- Useful for domain-specialized agents (order status, refunds, FAQ)

**Guardrails Architecture:**
- Run in parallel with agent execution (not sequentially blocking)
- Fail fast when checks don't pass
- Support: input validation, output validation, PII detection, schema validation, content filtering
- Both input guardrails (before execution) and output guardrails (before returning)

**Stateless Design (Inherited from Swarm):**
- No persistent state between calls by default
- Every handoff must include all context the next agent needs
- Optional structured state objects for session persistence
- SQLAlchemy and encrypted session variants for production use

**Evolution from Swarm:**
- Swarm was educational/experimental; Agents SDK is production-ready
- Added: guardrails, tracing, MCP support, provider-agnostic model support
- Kept: lightweight design, explicit handoffs, clarity over opaque automation

**Sources:**
- https://openai.github.io/openai-agents-python/
- https://github.com/openai/openai-agents-python
- https://developers.openai.com/blog/openai-for-developers-2025/

---

### 7.3 Google Agent Development Kit (ADK)

**Design Philosophy:**
Make agent development feel like software development. Code-first, modular, composable.

**Agent Hierarchy:**
- Parent agent manages one or more sub-agents
- Each agent can have only one parent (tree structure)
- Framework automatically sets `parent_agent` attribute
- Agent instance can only be added as sub-agent once

**Three Communication Mechanisms:**
1. **Shared Session State**: Agents read/write `context.state`. One writes, next reads. Passive, async communication. `output_key` auto-saves responses.
2. **LLM-Driven Delegation**: Agent generates `transfer_to_agent(agent_name='target')`. Framework intercepts and switches execution. Requires clear agent descriptions.
3. **Explicit Invocation (AgentTool)**: Wrap agent as tool in another agent's tool list. Synchronous execution, returns response as tool result.

**Workflow Agents:**
- **SequentialAgent**: Assembly-line execution, ordered sub-agents, shared invocation context
- **ParallelAgent**: Concurrent execution, separate threads, shared session state (unique keys to prevent races)
- **LoopAgent**: Repeats until `max_iterations` or `escalate=True`

**Orchestration Levels:**
1. **Deterministic**: Workflow agents (Sequential, Parallel, Loop) for predictable pipelines
2. **Dynamic**: LLM-driven routing for intelligent delegation between specialists

**Common Patterns:**
- Coordinator/Dispatcher: Central LLM routes to specialists
- Sequential Pipeline: Validator -> Processor -> Output
- Parallel Fan-Out/Gather: Concurrent data fetch -> synthesis agent
- Hierarchical Decomposition: Multi-level delegation trees
- Generator-Critic: Generate content -> review -> iterate

**Ecosystem:**
- Optimized for Gemini models and Vertex AI
- Interactions API: Unified interface for stateful, multi-turn agentic workflows
- TypeScript SDK available alongside Python
- ~14k GitHub stars as of early 2026

**Sources:**
- https://google.github.io/adk-docs/agents/multi-agents/
- https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/
- https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/

---

### 7.4 Microsoft Copilot Studio

**Multi-Agent Architecture (Three Approaches):**

1. **Embedded Agents (Child Agents)**
   - Lightweight child created inside parent agent
   - Inherits parent's environment
   - Best for: logical modularization without separate deployment/auth
   - No reuse across scenarios

2. **Connected Agents**
   - Independently built and operated
   - Separate ownership, deployment, authentication
   - Reusable across scenarios
   - Used when action set exceeds ~30-40 tools (degrades orchestration quality)

3. **MCP Integration**
   - Open standard for tool/data/prompt connections
   - Enterprise connector governance
   - Host-controlled reasoning
   - Straightforward client-server interaction

**Protocol Support:**
- **MCP**: For tools and data with enterprise security; single orchestrator controls reasoning
- **A2A (Agent2Agent)**: For cross-platform agent messaging; agents opaque to each other; multi-organization coordination; dynamic negotiation

**Workflow Patterns:**
- Serial steps (sequential execution)
- Concurrent flows (parallel processing)
- Mixed orchestration (combining serial and parallel)
- Human review gates for high-impact actions

**Key Design Principles:**
- Least privilege access for each agent
- Prefer platform-native orchestration for internal flows
- Track all agent interactions (auditability)
- Policy enforcement at control-plane layer
- Human-in-the-loop for high-impact cross-agent actions
- Typed payload validation between components

**Model Support:**
- Anthropic models, Azure-hosted models, Microsoft Foundry models
- Bring-your-own-model options
- Chat and reasoning-specific model selection

**Sources:**
- https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/architecture/multi-agent-patterns
- https://www.microsoft.com/en-us/microsoft-copilot/blog/copilot-studio/multi-agent-orchestration-maker-controls-and-more-microsoft-copilot-studio-announcements-at-microsoft-build-2025/
- https://holgerimbery.blog/multi-agent-orchestration

---

### 7.5 Cursor

**Multi-Agent Coding Architecture (Cursor 2.0, October 2025):**

- Up to 8 parallel AI agents on a single prompt
- Each agent operates in its own isolated environment
- Purpose-built coding model called "Composer"

**Git Worktree Isolation:**
- Each agent runs in its own git worktree
- Command: `git worktree add /tmp/cursor-agent-1 HEAD`
- Each worktree gets complete repo copy at current commit
- Prevents file conflicts between parallel agents
- `.cursor/worktrees.json` configures setup (deps, environment)
- Remote worker sandboxes also available

**Background Agents:**
- Push agent runs to background, receive notifications
- Integration with Linear: start agent runs from issue workflows
- Useful for long refactors or test generation while continuing other work

**Sandboxed Execution:**
- Sandboxed terminals GA on macOS since v2.0
- Agent commands run in secure sandbox by default
- Read/write access to workspace, no internet access (unless allowlisted)

**Performance Architecture:**
- Parallelized tool use (running tests while editing code)
- Optimized inference infrastructure
- Training specifically for interactive workflows (not batch processing)

**Tool Access:**
- Terminal commands (sandboxed)
- File read/write/edit
- Semantic search across codebase
- Browser control
- Rules engine and Plan Mode
- Hooks for custom automation
- Slash commands

**Sources:**
- https://cursor.com/docs/configuration/worktrees
- https://cursor.com/changelog/2-0
- https://cursor.com/features
- https://devops.com/cursor-2-0-brings-faster-ai-coding-and-multi-agent-workflows/

---

### 7.6 Replit

**Three-Agent Architecture:**

1. **Manager Agent**: Oversees workflow, coordinates other agents, handles planning
2. **Editor Agents**: Handle specific coding tasks with limited scope; constrained to smallest possible task
3. **Verifier Agent**: Validates code quality; frequently falls back to user interaction rather than autonomous decisions

**Design Philosophy:**
- "We don't strive for full autonomy. We want the user to stay involved and engaged."
- Limiting each agent to smallest possible task reduces error accumulation
- Continuous feedback loops over autonomous progression

**Tool Use Innovation:**
- Rejected standard API function calling
- Built restricted Python-based DSL for tool invocation
- Agents generate code to invoke tools themselves
- More reliable for 30+ tool library with multiple arguments per tool

**Model and Prompt Engineering:**
- Claude 3.5 Sonnet outperformed earlier fine-tuning experiments
- Few-shot examples + lengthy task-specific instructions
- Dynamic prompt construction with memory compression
- XML-tagged sections for structured formatting
- Markdown organization for lengthy instructions

**Agent 3 (Late 2025 - 2026):**
- Up to 200 minutes of continuous autonomous operation
- Self-testing loop: generate code -> execute -> identify errors -> fix -> rerun
- Can spawn new specialized agents from natural language descriptions
- Generated agents integrate with Slack, email, Telegram
- Automatic commits at major steps for reversion capability

**Observability:**
- LangSmith integration for monitoring multi-turn conversations
- LangGraph code traces for identifying bottlenecks

**Sources:**
- https://www.langchain.com/breakoutagents/replit
- https://blog.replit.com/introducing-agent-3-our-most-autonomous-agent-yet
- https://www.infoq.com/news/2025/09/replit-agent-3/

---

### 7.7 Notion

**Architecture (Notion 3.0, September 2025):**

- Rebuilt from scratch: replaced task-specific prompt chains with central reasoning model
- Central reasoning model coordinates modular sub-agents
- Previous architecture limited: agents needed to make decisions, orchestrate tools, reason through ambiguity

**Agent Capabilities:**
- Create and edit pages
- Update and build databases
- Coordinate multi-step tasks across workspace
- Work across hundreds of pages simultaneously
- Up to 20 minutes of autonomous operation

**Tool Access:**
- Search across Notion, Slack, web
- Pull context from Slack, Google Drive, GitHub, Microsoft Teams
- Add/edit database entries at scale
- Create interconnected page structures
- All within user's permissions model

**Memory Architecture:**
- Notion pages and databases serve as persistent memory
- Personalization page with instructions acts as memory bank
- Users configure: how to triage tasks, format responses, reference information
- State maintained throughout extended operations

**Model Partnership:**
- Rebuilt on GPT-5 (partnership with OpenAI)
- Shift from smaller models (GPT-4o mini) to frontier models
- Enabled agentic approach where model pulls additional context as needed

**MCP Support:**
- Enterprise features: audit logs for MCP activity, multi-database queries
- Controls for which external AI tools can connect to workspace

**Sources:**
- https://www.notion.com/releases/2025-09-18
- https://www.notion.com/blog/introducing-notion-3-0
- https://openai.com/index/notion/

---

### 7.8 Linear

**Triage Intelligence Architecture:**

**Search Infrastructure:**
- Rebuilt from keyword-based to semantic search
- Vector search and semantic similarity for issue matching
- Unified search approach for surfacing candidate issues from backlogs

**Suggestion Pipeline:**
1. New issue triggers the system
2. Semantic search identifies candidate issues from existing backlog
3. LLM evaluates candidates, determines relationships (duplicate, related, unrelated)
4. System recommends: assignees, teams, labels, projects
5. Model provides reasoning alongside suggestions

**Model Evolution:**
- Started with smaller models (GPT-4o mini, Gemini 2.0 Flash) + rigid prompts
- Shifted to frontier models (GPT-5, Gemini 2.5 Pro)
- Larger models enabled agentic approach: model pulls additional context as needed
- Moved from tightly scoped prompts to autonomous context gathering

**Trust & Transparency UX:**
- AI suggestions visually distinguished from human-set metadata
- Hover reveals model reasoning in plain language + alternatives
- Thinking panel shows full trace: context pulled, decisions made, guidance influence

**Agent Ecosystem:**
- Agents formalized as first-class users (assign to issues, add to teams, @mention)
- "Linear for Agents" release (May 2025) + Agent Interaction Guidelines & SDK (July 2025)
- Integrates with: Cursor Agent, GitHub Copilot Agent, Sentry Agent
- Email intake and routing: email threads become issues with two-way comment sync

**Customization:**
- "Additional Guidance" settings with natural language prompts
- Teams steer suggestions toward their priorities
- Especially valuable for multi-product organizations

**Sources:**
- https://linear.app/now/how-we-built-triage-intelligence
- https://linear.app/ai

---

### 7.9 Perplexity

**Pro Search Architecture:**

**Planning-Execution Separation:**
The cognitive architecture deliberately separates planning from execution:
1. User submits query
2. AI creates a structured step-by-step plan
3. For each step, generates a list of search queries
4. Steps execute sequentially; previous results inform subsequent steps
5. Final synthesis from all gathered information

**Deep Research Mode:**
- Performs dozens of searches, reads hundreds of sources
- Iteratively searches, reads documents, reasons about next steps
- Refines research plan as it learns more
- Autonomously delivers comprehensive report

**Multi-Stage Ranking Pipeline:**
1. **Dual Retrieval**: Both lexical and semantic retrieval, merged into hybrid candidate set
2. **Progressive Refinement**: Earlier stages use fast lexical/embedding-based scorers
3. **Cross-Encoder Reranking**: Final sculpting by powerful cross-encoder reranker models
4. **Grouping & Filtering**: Documents grouped, filtered to most relevant
5. **LLM Synthesis**: Top-ranked documents passed to LLM for answer generation

**Tool Integration:**
- Code interpreters for on-the-fly calculations and file analysis
- Wolfram Alpha for mathematical evaluations
- Multiple LLM backends (users can select models)
- Per-model prompt engineering (each model processes prompts differently)

**Evaluation Framework:**
- Two agent harnesses: single-shot search + advanced agentic workflows
- Manual evaluation across diverse queries
- LLM-as-a-Judge ranking for scale
- A/B testing to balance latency/cost tradeoffs

**Architecture Characteristics:**
- Hybrid retrieval mechanisms
- Multi-stage ranking pipelines
- Distributed indexing
- Dynamic parsing through self-improving content understanding module

**Sources:**
- https://www.langchain.com/breakoutagents/perplexity
- https://www.perplexity.ai/hub/blog/introducing-perplexity-deep-research
- https://research.perplexity.ai/articles/architecting-and-evaluating-an-ai-first-search-api

---

## Cross-Cutting Themes

### Theme 1: Move From Single-Agent to Multi-Agent is Universal
Every company studied has moved or is moving toward multi-agent architectures. The single-agent approach consistently hits limitations around context management, error accumulation, and task complexity.

### Theme 2: Specialization Over Generalization
The most reliable agents follow a simple rule: give each agent one job. Orchestrators should have narrow permissions (mostly "read and route"). Subagents should have clear inputs/outputs and a single goal.

### Theme 3: Context is the Hardest Problem
Context management across agent boundaries remains the primary engineering challenge. Solutions range from structured files (Anthropic's `claude-progress.txt`), to shared state dictionaries (Google ADK), to stateless handoffs with explicit context passing (OpenAI), to workspace-as-memory (Notion).

### Theme 4: Token Economics Matter
Multi-agent systems are expensive (15x chat costs per Anthropic). Model quality improvements yield better returns than simply increasing token budgets. Companies are learning to scale effort to query complexity rather than using maximum resources on every request.

### Theme 5: Human-in-the-Loop is Non-Negotiable for Now
Every production system maintains human oversight at critical decision points. The spectrum ranges from approval gates (Cursor sandboxed commands) to continuous feedback (Replit verifier) to background notification patterns (Notion, Cursor background agents).

### Theme 6: MCP is Becoming the Standard Tool Interface
Model Context Protocol, originated by Anthropic, is being adopted across Microsoft Copilot, Cursor, Notion, and others as the standard way to connect agents to external tools and data sources.

### Theme 7: Observability is Essential
All production implementations emphasize tracing and monitoring: OpenAI's built-in tracing, Anthropic's OpenTelemetry integration, Replit's LangSmith integration. Without observability, debugging multi-agent systems is intractable.
