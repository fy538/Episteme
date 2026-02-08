# Intelligence Engine

The Intelligence Engine is the coordination layer that turns a single user message into multiple AI analyses. It combines unified analysis, agent orchestration, signal extraction, proactive interventions, and deep research — all orchestrated to help users think through complex decisions.

## Architecture Overview

```
User Message
    ↓
ChatService.create_user_message() → Event appended (source of truth)
    ↓
assistant_response_workflow (async)
    ├── Agent inflection check (every 3 turns)
    ├── Intervention pattern check
    ├── UnifiedAnalysisEngine.analyze() ← single LLM call
    │   ├── <response> → chat UI (streamed)
    │   ├── <reflection> → companion panel (streamed)
    │   ├── <signals> → signal extraction (buffered JSON)
    │   └── <action_hints> → inline cards (buffered JSON)
    └── Post-processing: save message, reflection, signals, emit events
        └── Async: generate embeddings (Celery)
```

---

## Unified Analysis Engine (`intelligence/engine.py`)

The core innovation: instead of 3 separate LLM calls (response, reflection, signals), a **single call** returns all outputs using XML-sectioned streaming.

**`UnifiedAnalysisEngine.analyze_simple()`:**
1. Get message count and recent signals (last 10 non-dismissed)
2. Get patterns from companion `GraphAnalyzer`
3. Check extraction rules → should we extract signals this turn?
4. Build system + user prompts (mode-aware)
5. Stream from LLM → parse through `SectionedStreamParser`
6. Yield `StreamEvent` objects for each section

**Stream Event Types:**
- `RESPONSE_CHUNK` / `RESPONSE_COMPLETE` — chat response
- `REFLECTION_CHUNK` / `REFLECTION_COMPLETE` — meta-cognitive observation
- `SIGNALS_COMPLETE` — extracted signals array
- `ACTION_HINTS_COMPLETE` — suggested next actions
- `DONE` — final aggregate

See [CHAT_STREAMING_ARCHITECTURE.md](./CHAT_STREAMING_ARCHITECTURE.md) for the full streaming pipeline details.

---

## Agent Orchestration (`agents/`)

### Inflection Detector (`inflection_detector.py`)

Uses the **fast LLM provider** (Haiku) to detect when a conversation needs a specialized agent. Checks every 3 turns.

| Inflection Type | Trigger | Agent |
|----------------|---------|-------|
| `research_depth` | Multiple complex questions needing investigation | Research Agent |
| `critique_assumptions` | Stated position with unvalidated uncertainties | Critique Agent |
| `synthesis_decision` | Enough information collected, ready to decide | Brief Agent |

- Analyzes last 6 messages as context window
- Returns confidence score; threshold is **0.75** to activate
- Returns `suggested_topic` for agent focus

### Agent Spawning (`orchestrator.py`)

When inflection is detected above threshold:

1. Create placeholder message in chat (e.g., "Research Agent Running")
2. Emit `AGENT_WORKFLOW_STARTED` event
3. Look up agent in `AgentRegistry` → dispatch Celery task
4. Return immediately (non-blocking)

Agent updates the placeholder message with progress as it works.

### Research Agent (`research_loop.py`)

Multi-step deep investigation pipeline:

```
PLAN → SEARCH → EXTRACT → EVALUATE → CHECK COMPLETENESS → SYNTHESIZE
                    ↑                        │
                    └── iterate if incomplete ┘
```

| Step | What it does |
|------|-------------|
| **PLAN** | LLM decomposes research question into sub-queries |
| **SEARCH** | Execute sub-queries + contrary findings (devil's advocate) |
| **EXTRACT** | LLM extracts structured findings with direct quotes |
| **EVALUATE** | Score relevance + quality (fair scoring regardless of agreement) |
| **CHECK** | Enough info? → iterate with follow-ups or proceed |
| **SYNTHESIZE** | Markdown report with citations and conflicting evidence |

**Context Thinning** (keeps cost bounded as findings accumulate):
- **40k tokens:** Noise removal — drop low-scoring findings
- **60k tokens:** Observation masking — strip raw source text
- **80k tokens:** LLM compaction digest

**Research Config** (`research_config.py`): Declarative YAML-like spec for agent behavior — decomposition strategy, sources, extract fields, evaluation rubrics, done-when criteria. Config changes behavior; code stays the same.

---

## Signal Extraction Pipeline

### Extraction Rules (`intelligence/extraction_rules.py`)

Balances cost vs. coverage — doesn't extract every message but never misses important signals.

| Condition | Action |
|-----------|--------|
| First message in thread | Always extract |
| Trigger phrases ("I assume", "not sure if", "should we", "deadline") | Extract |
| ≥2 turns AND ≥200 chars since last extraction | Extract |
| ≥5 turns without any extraction | Force extract |
| Otherwise | Skip (saves LLM cost) |

### Signal Types

`DecisionIntent` · `Claim` · `Goal` · `Constraint` · `Assumption` · `Question` · `EvidenceMention`

### Signal Lifecycle

```
Extracted from LLM → Deduplicated (SHA256) → Stored with embedding (384-dim)
    ↓                                              ↓
Can be dismissed                          Can be elevated to Inquiry
    ↓                                              ↓
Assumption signals track:                  Linked to Evidence
untested → confirmed / challenged / refuted
```

### Deduplication

- **Key:** `SHA256(type + ":" + text.lower())` → 64-char hex
- **Scope:** Per-thread (non-dismissed signals)
- **Batch query:** Single DB hit to find existing keys (avoids N+1)

---

## Intervention System (`chat/interventions.py`)

Proactive pattern detection that suggests structured actions to the user.

### How It Works

1. `InterventionService.check_and_intervene()` runs after message processing
2. Checks cooldown (max every 3 turns)
3. `PatternDetectionEngine.analyze_thread()` looks for patterns:
   - **multiple_questions** → suggest organizing into an inquiry
   - **unvalidated_assumptions** → suggest validation
   - **case_structure** → suggest creating a case
   - **high_signal_density** → suggest organizing signals
4. Checks dismissed suggestions (won't re-suggest)
5. Creates `InlineActionCard` in chat via `CardBuilder`

---

## File Structure

```
backend/apps/
├── intelligence/               # Core analysis engine
│   ├── engine.py              # UnifiedAnalysisEngine
│   ├── prompts.py             # Prompt construction
│   ├── case_prompts.py        # Case-specific prompt extensions
│   ├── parser.py              # SectionedStreamParser
│   ├── extraction_rules.py    # When to extract signals
│   ├── handlers.py            # Post-stream processing
│   └── title_generator.py     # Thread title generation
│
├── agents/                     # Agent orchestration
│   ├── orchestrator.py        # AgentOrchestrator
│   ├── inflection_detector.py # When to use agents
│   ├── research_loop.py       # Research agent pipeline
│   ├── research_config.py     # Declarative research config
│   ├── research_prompts.py    # Research step prompts
│   └── registry.py            # Agent registry (extensible)
│
├── signals/                    # Signal system
│   ├── models.py              # Signal model + types
│   ├── extractors.py          # PydanticAI signal extraction
│   └── memory_retrieval.py    # Signal retrieval for context
│
├── chat/                       # Chat coordination
│   ├── views.py               # unified_stream endpoint
│   ├── services.py            # ChatService
│   ├── interventions.py       # Proactive suggestions
│   ├── pattern_detection.py   # Pattern analysis engine
│   └── card_builders.py       # Intervention card templates
│
└── common/                     # Shared infrastructure
    ├── ai_services.py         # One-off LLM services (PydanticAI)
    ├── ai_schemas.py          # Pydantic types for LLM output
    ├── llm_providers/         # Provider abstraction layer
    │   ├── anthropic_provider.py
    │   └── openai_provider.py
    └── embedding_service.py   # 384-dim sentence-transformers
```

---

## Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| `AI_MODELS.chat` | Claude Opus | Main analysis model |
| `AI_MODELS.fast` | Claude Haiku | Inflection detection, quick tasks |
| `AI_MODELS.reasoning` | Claude Opus | Complex reasoning tasks |
| `AI_MODELS.extraction` | Claude Haiku | Signal extraction |
| Extraction: min turns between | 2 | Don't extract too frequently |
| Extraction: min chars between | 200 | Wait for meaningful content |
| Extraction: max turns without | 5 | Force eventually |
| Agent check interval | Every 3 turns | Inflection detection frequency |
| Agent confidence threshold | 0.75 | Minimum to activate agent |
| Research max iterations | 2 | Default depth for research loop |

---

## Extensibility

| Extension | How |
|-----------|-----|
| New signal type | Add to `VALID_SIGNAL_TYPES` in handlers.py, update prompts |
| New agent | Implement agent class, register in `AgentRegistry` |
| New LLM provider | Implement `LLMProviderProtocol` interface |
| New extraction rule | Add condition to `ExtractionRulesEngine.should_extract()` |
| New action hint type | Update prompt in `prompts.py`, add frontend handler |
| New intervention pattern | Add to `PatternDetectionEngine`, create card builder |
