# Extraction Engine Architecture

The extraction engine is the system that turns raw inputs — documents, conversations, research — into structured knowledge graph nodes and edges. It is the single most important subsystem in Episteme because the quality of everything downstream (the Evidence Map, the delta narratives, the graph-aware agent) depends entirely on the quality of extraction.

This document covers the current state, the target architecture, the gap between them, and the engineering spec for closing it.

---

## Current State

Episteme currently has **four separate extraction pipelines** that evolved independently. They share some infrastructure (embedding model, LLM providers) but produce different output types into different models with no unified integration layer.

### Pipeline 1: Document → Evidence

**Path:** `process_document_workflow` → `DocumentService.process_document()` → `EvidenceExtractor`

**What it does:**
1. Extract text from file (PDF, DOCX, TXT) via `DocumentProcessor`
2. Chunk into 512-token segments with 15% overlap via `RecursiveTokenChunker`
3. Generate 384-dim embeddings per chunk via `SentenceTransformer('all-MiniLM-L6-v2')`
4. Store chunks as `DocumentChunk` rows with linked embeddings
5. Extract evidence from each chunk individually via LLM
6. Link evidence to existing signals via auto-reasoning

**Output model:** `Evidence` (fact, metric, claim, quote, benchmark)

**LLM usage:**
- Extraction: `openai:gpt-4o-mini` — one call per chunk
- Auto-reasoning relationship classification: `claude-haiku-4-5` — one call per evidence-signal candidate pair

**Strengths:**
- Reliable chunking with overlap and context linking (prev/next chunk IDs)
- Per-item error handling — one bad chunk doesn't fail the whole document
- Provenance chain: Evidence → DocumentChunk → Document

**Weaknesses:**
- Extracts per-chunk, not per-document. Misses document-level claims and cross-section reasoning.
- Only extracts "evidence" (facts/metrics). Doesn't extract claims, assumptions, or detect intra-document tensions.
- Uses a fast/cheap model (gpt-4o-mini) that produces generic extractions. "Market is growing" instead of "Document claims TAM will reach $4.2B by 2027 citing Gartner."
- One LLM call per chunk is expensive at scale (a 20-page PDF = ~40 chunks = 40 LLM calls).
- Auto-reasoning runs per evidence item against all signals — O(evidence × signals) LLM calls.
- Evidence lives in its own model, disconnected from the graph.

### Pipeline 2: Chat → Signals

**Path:** `unified_stream` → `UnifiedAnalysisEngine` → `UnifiedAnalysisHandler._save_signals()`

**What it does:**
1. User sends message in chat
2. Unified analysis generates response + reflection + signals in one streaming LLM call
3. Handler parses signal JSON, deduplicates via `dedupe_key` (SHA-256 hash of type:text)
4. Creates `Signal` rows linked to thread/case
5. Generates embeddings async via `generate_signal_embeddings.delay()`

**Output model:** `Signal` (assumption, claim, question, constraint, goal, decisionintent, evidence)

**LLM usage:** Single streaming call that produces response + signals together (the unified analysis approach)

**Extraction gating:** `ExtractionRulesEngine` decides when to extract based on turn count (every 2 turns), character accumulation (200+ chars), trigger phrases ("I assume", "we decided"), and forced extraction after 5 turns without any.

**Strengths:**
- Single LLM call for response + extraction — no extra latency
- Trigger phrase detection surfaces assumptions immediately
- Deduplication prevents duplicate signals from repeated conversations

**Weaknesses:**
- Signals live in the `Signal` model, disconnected from the graph
- No integration step — signals are extracted but never cross-referenced against evidence
- No relationship detection between signals (depends_on, contradicts fields exist on Signal but aren't populated by this pipeline)
- Extraction quality depends on the chat model, which is optimized for conversation, not structured extraction

### Pipeline 3: Document Claims → Signal Links (Evidence Linker)

**Path:** `extract_and_link_claims()` in `evidence_linker.py`

**What it does:**
1. Extract claims from a document (LLM call)
2. For each claim, find similar signals via embedding pre-filtering (cosine > 0.4, top 5)
3. LLM evaluates claim-signal relationships: support, relevance, substantiation status
4. Persist as `evidence.supports_signals` M2M links

**Output:** M2M relationships between `Evidence` and `Signal`

**LLM usage:**
- Claim extraction: `claude-haiku-4-5` (one call)
- Claim-signal matching: `claude-haiku-4-5` (one call with batch of claims + filtered signals)

**Strengths:**
- Two-phase approach (embed pre-filter → LLM evaluate) is efficient
- Produces actual relationship links, not just isolated extractions

**Weaknesses:**
- Only links claims to signals, doesn't detect contradictions or tensions
- Coupled to the brief grounding system, not reusable
- Uses embedding threshold of 0.4 which is very permissive — may produce noisy candidates

### Pipeline 4: Research Findings → Evidence

**Path:** `extract_evidence_from_findings()` → `EvidenceIngestionService.ingest()`

**What it does:**
1. Research agent produces `ScoredFinding` objects
2. Findings filtered by relevance score threshold
3. Converted to `Evidence` via universal ingestion service
4. Synthetic `Document` + `DocumentChunk` created for provenance
5. Embeddings generated, auto-reasoning runs

**Output model:** `Evidence` (same as Pipeline 1)

**Strengths:**
- Universal ingestion point — any evidence source converges here
- Full provenance even for synthesized content

**Weaknesses:**
- Research findings enter the system as flat evidence, not as structured claims/assumptions
- No integration against existing knowledge — auto-reasoning only links to individual signals
- The research agent doesn't know what the graph already contains, so it can't target gaps

### Shared Infrastructure

| Component | Location | Used By |
|-----------|----------|---------|
| Embedding model | `SentenceTransformer('all-MiniLM-L6-v2')` — 384 dims | All pipelines |
| Embedding cache | `LRU(100, 5min TTL)` in `apps/common/embeddings.py` | Pipelines 1, 3, 4 |
| Embedding storage | `PostgreSQLJSONBackend` (JSON column, linear scan) | Pipeline 1 |
| LLM provider resolution | `get_model(settings.AI_MODELS[key])` | All pipelines |
| Text extraction | `DocumentProcessor` (PDF, DOCX, TXT) | Pipeline 1 |
| Chunking | `RecursiveTokenChunker` (512 tokens, 15% overlap, tiktoken cl100k_base) | Pipeline 1 |
| Deduplication | SHA-256 hash of `type:normalized_text` | Pipeline 2 |

### What's Missing

The current system has no:
- **Unified output model.** Evidence, Signal, and (soon) Node are three separate representations of knowledge.
- **Cross-document integration.** Documents are processed in isolation. No system detects that Document A contradicts Document B.
- **Intra-document tension detection.** A document that contradicts itself is processed as a bag of independent evidence items.
- **Document-level extraction.** Per-chunk extraction misses the document's thesis, argument structure, and implicit assumptions.
- **Feedback loop from graph to extraction.** The extraction prompt doesn't know what the project already contains, so it can't prioritize gaps or flag contradictions.
- **Delta narrative.** The system processes documents but doesn't tell the user what changed and why it matters.

---

## Target Architecture

### Design Principles

1. **One pipeline, multiple triggers.** Document upload, chat conversation, and research completion all feed into the same extraction → integration → delta pipeline. The extraction prompt varies by source. Integration and delta generation are source-agnostic.

2. **Document-level extraction, chunk-level provenance.** The LLM sees the full document (or large sections) to extract the document's argument structure. But every extracted node traces back to specific chunks for provenance.

3. **Integration is the aha moment.** Extraction alone (Phase A) tells you what a document says. Integration (Phase B) tells you how it changes what you know. The aha moment is always in Phase B.

4. **Quality over quantity.** 5 specific, well-classified nodes per document beats 20 generic ones. The extraction prompt must enforce specificity. "The market is growing" is a failure. "Document claims TAM will reach $4.2B by 2027 citing Gartner" is a success.

5. **Conservative contradiction detection.** Different emphasis is not a contradiction. Different numbers for the same metric IS. The integration prompt must distinguish genuine tensions from semantic overlap.

6. **Provenance on everything.** Every node traces to its source (document + chunk, chat message, research finding). Every edge traces to its creation context. Trust requires traceability.

7. **The first document matters.** Even a single document should produce useful structure — claims, evidence, assumptions, and intra-document tensions. The user shouldn't need to upload two documents before the system does something interesting.

### Unified Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                         TRIGGERS                                 │
│                                                                  │
│  Document Upload     Chat Conversation     Research Completion   │
│  (single or batch)   (signal promotion)    (finding extraction)  │
└────────┬─────────────────────┬─────────────────────┬────────────┘
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PREPROCESSING                                 │
│                                                                  │
│  Documents: text extraction → chunking → chunk embeddings        │
│  Chat: signal extraction (existing unified analysis pipeline)    │
│  Research: finding scoring + filtering                           │
│                                                                  │
│  Output: preprocessed content ready for Phase A                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PHASE A: EXTRACTION                              │
│                 "What does this say?"                             │
│                                                                  │
│  Input: preprocessed content (full document / chat signals /     │
│         research findings)                                       │
│                                                                  │
│  LLM call: source-specific extraction prompt                     │
│    - Documents: extract claims, evidence, assumptions from full  │
│      document text. Detect intra-document tensions.              │
│    - Chat: promote extracted signals to typed graph nodes        │
│    - Research: extract structured findings as evidence + claims  │
│                                                                  │
│  Post-processing:                                                │
│    - Map nodes to source chunks (text match → embedding fallback)│
│    - Generate node embeddings (384-dim, same model as chunks)    │
│    - Validate type/status combinations                           │
│                                                                  │
│  Output: Node[] with embeddings + chunk provenance               │
│  Target: 5-12 nodes per document, 1-3 per chat signal batch,    │
│          3-8 per research report                                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PHASE B: INTEGRATION                             │
│                 "How does this change what we know?"              │
│                                                                  │
│  Input: new Node[] + existing project graph                      │
│                                                                  │
│  Context assembly:                                               │
│    - Small graph (≤30 nodes): include all existing nodes + edges │
│    - Large graph (>30 nodes): pgvector similarity search per     │
│      new node (top-5 similar existing nodes), deduplicate,       │
│      include all edges between selected nodes                    │
│                                                                  │
│  LLM call: integration prompt with existing graph + new nodes    │
│    - Create edges (supports, contradicts, depends_on)            │
│    - Detect tensions (genuine contradictions between nodes)       │
│    - Recommend status updates (untested → challenged, etc.)      │
│    - Identify gaps (important topics not covered by graph)        │
│                                                                  │
│  Special case — first document:                                  │
│    - No existing graph → skip cross-document integration         │
│    - BUT still detect intra-document tensions (from Phase A)     │
│    - Still create edges between the document's own nodes         │
│    - Still surface assumptions with no evidence                  │
│                                                                  │
│  Output: Edge[], Tension Node[], status changes, gap nodes       │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PHASE C: DELTA GENERATION                        │
│                 "What just happened and why does it matter?"      │
│                                                                  │
│  Input: all graph mutations from this extraction event           │
│                                                                  │
│  Compute:                                                        │
│    - Structured patch (every create/update/delete with before    │
│      and after values)                                           │
│    - Impact counts (nodes created, edges created, tensions       │
│      surfaced, assumptions challenged)                           │
│                                                                  │
│  LLM call: narrative generation from patch data                  │
│    - 2-3 sentences: what changed, what was challenged, what's    │
│      still missing                                               │
│    - Opinionated voice — not "2 nodes added" but "The market     │
│      report directly contradicts your pitch deck's growth rate.  │
│      Your assumption about partner renewal remains untested."    │
│                                                                  │
│  Output: GraphDelta (patch + narrative + impact counts)          │
│  Emits: GRAPH_DELTA_COMPUTED event for frontend                  │
└─────────────────────────────────────────────────────────────────┘
```

### Trigger-Specific Extraction Details

#### Trigger 1: Document Upload

The primary extraction path. This is where most knowledge enters the system.

**Preprocessing (existing pipeline, kept intact):**
1. `DocumentProcessor.extract_text(file_path)` — PDF pages, DOCX paragraphs, plain text
2. `RecursiveTokenChunker.chunk_with_page_info()` — 512 tokens, 15% overlap, recursive splitting (sections → paragraphs → sentences → tokens)
3. `SentenceTransformer.encode()` — 384-dim embeddings per chunk
4. `DocumentChunk.objects.create()` — store with prev/next linking

**Phase A extraction prompt:**

The LLM receives the full document text (or batched sections for long documents). This is a deliberate departure from the current per-chunk approach. Per-chunk extraction misses the forest for the trees — it can extract a metric from page 7 but can't identify the document's central thesis or detect that section 3 contradicts section 8.

```
System: You are analyzing a document to extract its key knowledge
components for a reasoning graph. Extract ONLY what matters —
quality over quantity.

For each item, classify as:
- CLAIM: A specific assertion or conclusion the document makes.
  Must be concrete enough to be proven wrong.
- EVIDENCE: A concrete fact, data point, metric, or observation.
  Must be verifiable or sourced.
- ASSUMPTION: A belief the document takes for granted without
  proving. The gap between what's stated and what's assumed.

Rules:
- Extract 3-7 claims (the document's key assertions)
- Extract 2-5 evidence items (concrete facts supporting claims)
- Surface 1-3 implicit assumptions (beliefs assumed without proof)
- For each item, quote the EXACT passage it comes from
- For assumptions, explain what would need to be true and what
  evidence is missing
- SPECIFICITY IS MANDATORY. Reject vague extractions.
  BAD:  "The market is growing"
  GOOD: "Document claims TAM will reach $4.2B by 2027 citing
        Gartner research"
- Flag any INTRA-DOCUMENT TENSIONS — places where the document
  contradicts itself or makes claims unsupported by its own
  evidence
```

**Chunk provenance mapping:**

After extraction, each node must link to its source chunk(s). Two-pass approach:
1. **Text prefix match:** Compare first 80 chars of `source_passage` (lowercased) against each chunk's text. Fast, handles exact quotes.
2. **Embedding fallback:** If no text match, embed the source passage and find the most similar chunk via pgvector (cosine distance, threshold 0.85, top 2).

**Why full-document extraction matters for first upload:**

A single document, processed through the current per-chunk pipeline, produces a flat list of evidence items. No structure, no insight. With document-level extraction, that same document produces:
- Claims: what the document asserts
- Evidence: what facts support those claims
- Assumptions: what the document takes for granted
- Intra-document tensions: where the document contradicts itself
- Intra-document edges: which evidence supports which claims

This is already useful before a second document is uploaded. The user sees the document's argument structure made visible. "I didn't realize my pitch deck's growth projection has no cited source" is an aha moment from a single document.

**Long document handling:**

Documents exceeding the LLM context window (currently ~128K tokens for Sonnet) need batching. Strategy:
- If document fits in context: send full text
- If document exceeds context: split into major sections (using heading detection from page/paragraph metadata in chunks), process each section, then run a consolidation pass that merges overlapping extractions

Target: a 50-page PDF should produce 8-15 nodes, not 50. The extraction prompt's "quality over quantity" constraint prevents over-extraction.

#### Trigger 2: Chat Conversation

When the user converses with the graph-aware agent, two things happen in parallel:
1. The agent generates a response (visible to user)
2. The agent emits `<graph_edits>` (structural mutations to the graph)

The `<graph_edits>` section IS the extraction output for chat. The agent decides what to extract based on the conversation and the current graph state. This is different from document extraction — it's guided by an agent that can see the full graph context and make judgment calls about what deserves to become a node.

**When the agent creates nodes from chat:**
- User states a belief → Assumption node (untested)
- User shares a fact → Evidence node (uncertain, source=chat)
- User makes a claim → Claim node
- User asks "what am I missing?" → Agent may surface gap nodes
- User challenges an existing node → Status update or new contradicting edge

**Phase B for chat-originated nodes:**

Same integration pipeline as documents, but lighter. Chat typically produces 1-3 nodes per interaction, so integration is fast — check the new node against the top-5 similar existing nodes, create edges if relationships are substantive.

**Delta for chat:**

The delta narrative for chat edits should be concise and immediate: "Added assumption: 'Sales team can handle enterprise deals.' No evidence for or against this in your documents." This appears inline in the chat stream, not as a separate notification.

#### Trigger 3: Research Completion

When the research agent completes a report, its findings should enter the graph. This is not yet implemented in the V1 plan but is the natural next step.

**Extraction approach:**

The research agent already produces structured output (sections: Key Findings, Data Points, etc.). Post-processing extracts nodes from these sections:
- Key Findings → Claim nodes (with evidence source links)
- Data Points → Evidence nodes (with external source URLs)
- Recommendations → Claim nodes (status: unsubstantiated until validated)
- Caveats → Assumption nodes or Tension nodes

**Phase B integration is high-value here** because research was (ideally) triggered to fill gaps in the graph. The delta narrative should directly address whether the research answered the question it was asked: "Research on competitor pricing confirmed your pricing assumption but surfaced a new risk: Competitor B is offering free tiers."

**Future enhancement — research-aware extraction:**

The research agent should receive the current graph (via serialization) so it can:
1. Target untested assumptions and knowledge gaps
2. Avoid researching things the graph already has strong evidence for
3. Frame findings in terms of existing nodes ("This finding supports/contradicts [A3]")

This turns research from "go find stuff" into "go fill these specific holes."

---

## Migration Path: Current → Target

The graph extraction pipeline runs **parallel** to the existing system. No existing pipelines are modified or removed.

### What stays unchanged

| Component | Why |
|-----------|-----|
| `DocumentProcessor` (text extraction) | Works well, no reason to change |
| `RecursiveTokenChunker` | Good chunking with overlap, page metadata preservation |
| `SentenceTransformer` embedding model | Consistent embeddings across all pipelines |
| `DocumentChunk` model | Chunk storage is independent of what extraction produces |
| `Signal` extraction from chat | Cases still use signals; graph runs in parallel |
| `Evidence` extraction from chunks | Existing cases rely on evidence model; graph runs in parallel |

### What's added

| Component | Purpose |
|-----------|---------|
| `graph/extraction.py` | Phase A: document-level node extraction |
| `graph/integration.py` | Phase B: cross-document integration |
| `graph/delta_service.py` | Phase C: delta computation + narrative |
| `graph/tasks.py` | Celery task: `process_document_to_graph` |
| `graph/edit_handler.py` | Chat → graph edits bridge |
| `common/vector_utils.py` | pgvector similarity search helpers |

### What changes

| Component | Change |
|-----------|--------|
| `tasks/workflows.py` | After `process_document_workflow` completes, trigger `process_document_to_graph.delay()` |
| `Document` model | New fields: `extraction_status`, `extraction_error` |
| Embedding storage | Migrate from JSON column to pgvector `VectorField(384)` for Node.embedding |

### What's deprecated (but not removed)

| Component | Replaced by | When to remove |
|-----------|-------------|----------------|
| `EvidenceExtractor` per-chunk extraction | `graph/extraction.py` document-level extraction | When no cases depend on `Evidence` model |
| `AutoReasoningPipeline` | `graph/integration.py` Phase B | When no cases depend on `Signal.supports_signals` M2M |
| `EvidenceIngestionService` | Direct `Node` creation via `GraphService` | When research pipeline uses graph |
| `evidence_linker.py` | Graph edges (supports/contradicts) | When briefs read from graph instead of evidence links |

---

## Extraction Quality

The extraction engine lives or dies on extraction quality. A perfect integration pipeline operating on generic extractions produces generic insights. This section defines what good extraction looks like and how to enforce it.

### What good extraction looks like

**Bad extraction (current system typical output):**
```json
{
  "type": "evidence",
  "text": "Market is growing",
  "confidence": 0.7
}
```

**Good extraction (target):**
```json
{
  "type": "claim",
  "content": "The US enterprise SaaS market will reach $4.2B by 2027, growing at 28% CAGR",
  "status": "unsubstantiated",
  "source_passage": "Our analysis projects the US enterprise SaaS market reaching $4.2B by 2027, representing a 28% compound annual growth rate.",
  "properties": {
    "specificity": "high",
    "source_context": "Section 2: Market Sizing, paragraph 3"
  },
  "reasoning": "Classified as claim rather than evidence because the 28% CAGR is a projection, not an observed metric. The document provides no external source for this number."
}
```

The difference: specificity, correct classification (claim vs. evidence), provenance, and reasoning about *why* it's classified this way.

### Extraction quality levers

1. **Model choice.** Phase A uses Claude Sonnet, not Haiku or gpt-4o-mini. Extraction is the most important LLM call in the system — it runs once per document and affects everything downstream. The cost difference between Haiku and Sonnet is trivial compared to the quality difference in structured extraction.

2. **Specificity enforcement in the prompt.** The extraction prompt must include examples of BAD vs. GOOD extractions. LLMs mirror the quality of examples more than instructions.

3. **Type/status validation.** The `VALID_STATUSES_BY_TYPE` dict (from V1 spec) is enforced at model level. A claim can be supported/contested/unsubstantiated. An assumption can be untested/confirmed/challenged/refuted. Invalid combinations are rejected and re-classified.

4. **Post-extraction filtering.** After LLM extraction, filter out nodes where:
   - `content` is fewer than 20 characters (too vague)
   - `content` duplicates another extracted node (embedding cosine > 0.92)
   - `source_passage` doesn't appear in the document (hallucinated provenance)

5. **Extraction reasoning as a quality signal.** Requiring the LLM to explain its classification ("reasoning" field) forces deeper analysis. If the reasoning is generic ("This is a claim because it's an assertion"), the extraction is probably low quality.

### Intra-document tension detection

Phase A should detect tensions WITHIN a single document. This is critical for the first-upload experience.

Common intra-document tensions:
- **Contradictory claims across sections.** Executive summary says "growth is accelerating," financial section shows declining quarter-over-quarter revenue.
- **Claims unsupported by the document's own evidence.** Pitch deck claims "no direct competitors" but lists competitive advantages (implying competitors exist).
- **Quantitative inconsistencies.** One section says "28% YoY growth," another says "revenue grew from $10M to $11M" (which is 10%, not 28%).

The extraction prompt includes an explicit instruction to flag these. The extracted nodes include a `tensions` array:

```json
{
  "tensions": [
    {
      "content": "Growth rate inconsistency: executive summary claims 28% YoY but financials show 10%",
      "severity": "high",
      "between": [0, 3],
      "description": "The executive summary states 28% annual growth, but the revenue figures ($10M → $11M) imply only 10% growth"
    }
  ]
}
```

These become Tension nodes in Phase A itself, without requiring Phase B.

---

## LLM Configuration

| Phase | Model | Temperature | Max Tokens | Rationale |
|-------|-------|-------------|------------|-----------|
| Phase A: Document extraction | Claude Sonnet | 0.2 | 4096 | Structured extraction needs precision. Sonnet's reasoning quality justifies the cost for a once-per-document call. |
| Phase A: Chat signal promotion | (same model as chat agent) | — | — | Already handled by the graph-aware agent's `<graph_edits>` output. No separate LLM call needed. |
| Phase B: Integration | Claude Sonnet | 0.3 | 4096 | Cross-document reasoning is the hardest task. Slight temperature increase for better tension detection. |
| Phase C: Delta narrative | Claude Haiku | 0.4 | 512 | Simple summarization from structured data. Speed matters, quality bar is lower. |
| Document summary | Claude Haiku | 0.2 | 256 | Compact context for large-graph Phase B. |
| Node embedding | SentenceTransformer (local) | — | — | Same model as chunk embeddings. No API cost. |

---

## Orchestration

### Single document upload

```
User uploads document
  │
  ├─ [existing pipeline] process_document_workflow (Celery)
  │    └─ text extract → chunk → embed → store chunks
  │    └─ (legacy) evidence extract → auto-reasoning
  │
  └─ [new pipeline] process_document_to_graph (Celery, triggered after existing pipeline)
       │
       ├─ extraction_status = 'extracting'
       ├─ Phase A: extract_nodes_from_document()
       │    ├─ Load document.content_text (full text)
       │    ├─ LLM extraction call (Sonnet)
       │    ├─ Map nodes to source chunks
       │    ├─ Generate node embeddings
       │    ├─ Create Node rows via GraphService
       │    └─ Detect intra-document tensions
       │
       ├─ extraction_status = 'integrating'
       ├─ Phase B: integrate_new_nodes()
       │    ├─ Assemble context (all existing nodes if ≤30, else pgvector top-K)
       │    ├─ LLM integration call (Sonnet)
       │    ├─ Create edges
       │    ├─ Create tension nodes
       │    ├─ Apply status updates
       │    └─ Create gap nodes
       │
       ├─ Phase C: create_delta()
       │    ├─ Build structured patch from all mutations
       │    ├─ LLM narrative call (Haiku)
       │    └─ Create GraphDelta row
       │
       ├─ extraction_status = 'completed'
       └─ Emit GRAPH_EXTRACTION_COMPLETED event
```

### Bulk upload (multiple documents)

No special orchestration. Each document triggers its own `process_document_to_graph` task independently. Documents process in parallel (Phase A) and integrate sequentially (Phase B) because each integration runs against the graph that exists at that moment.

The order of integration affects which tensions are detected first, but by the time all documents complete, the graph converges to the same state. Doc 3's Phase B may find tensions with Doc 1 that Doc 2's Phase B missed — because Doc 2 processed before Doc 1 finished.

**If integration order quality becomes a problem** (unlikely for V1), the improvement is a batch integration mode: wait for all Phase A extractions to complete, then run one large Phase B that compares all new nodes against each other and any pre-existing graph. This is the `DocumentBatch` model approach — a Celery chord or counter-based barrier. Deferred until proven necessary.

### Chat conversation

```
User sends message
  │
  └─ [unified_stream]
       ├─ Agent sees serialized graph in system prompt
       ├─ Agent generates response + <graph_edits>
       ├─ Frontend renders response
       │
       └─ [handle_completion]
            ├─ Parse <graph_edits> JSON
            ├─ GraphEditHandler.apply_edits()
            │    ├─ Resolve node references ([C1], [A2], new-0)
            │    ├─ Create/update/remove nodes via GraphService
            │    ├─ Lightweight Phase B: integrate new nodes
            │    └─ Create GraphDelta (trigger='chat_edit')
            │
            └─ Yield SSE graph_edits event to frontend
```

### Research completion (future)

```
Research agent completes
  │
  └─ [generate_research_workflow]
       ├─ Create CaseDocument (the readable report)
       │
       └─ [NEW] extract_graph_from_research()
            ├─ Parse structured findings from research output
            ├─ Phase A: extract nodes from findings
            ├─ Phase B: integrate against project graph
            ├─ Phase C: generate delta
            └─ Emit GRAPH_EXTRACTION_COMPLETED event
```

---

## Performance Characteristics

### Per-document cost

| Step | Time | LLM Calls | Cost (est.) |
|------|------|-----------|-------------|
| Text extraction | <1s | 0 | $0 |
| Chunking | <1s | 0 | $0 |
| Chunk embeddings | 1-3s (local) | 0 | $0 |
| Phase A extraction | 5-15s | 1 (Sonnet) | ~$0.02-0.05 |
| Node embeddings | <1s (local) | 0 | $0 |
| Chunk provenance mapping | 1-2s | 0 | $0 |
| Phase B integration | 5-20s | 1 (Sonnet) | ~$0.02-0.08 |
| Phase C delta narrative | 2-5s | 1 (Haiku) | ~$0.001 |
| **Total** | **15-45s** | **3** | **~$0.04-0.13** |

Compare to current per-chunk pipeline: 40 chunks × 1 LLM call each = 40 calls at ~$0.001 each = $0.04, but taking 60-120s with lower quality output.

The new pipeline is **faster** (3 calls vs. 40), **similar cost**, and **dramatically better quality** because it operates at document level.

### Scaling characteristics

| Project size | Phase B context strategy | Integration time |
|-------------|-------------------------|-----------------|
| 0 nodes (first doc) | Skip cross-document integration | ~0s |
| 1-30 nodes | Send full graph to LLM | 5-10s |
| 30-100 nodes | pgvector top-5 per new node | 10-15s |
| 100-300 nodes | pgvector top-5 + document summaries | 15-20s |
| 300+ nodes | pgvector top-3 + summaries only | 15-20s (constant) |

Phase B cost is bounded because the LLM context is capped at ~30 context nodes regardless of graph size. The pgvector query itself is O(log n) with HNSW index.

---

## Observability

Every extraction run should produce structured logs for debugging extraction quality:

```python
{
    "event": "graph_extraction_completed",
    "document_id": "uuid",
    "project_id": "uuid",
    "phase_a": {
        "duration_ms": 8200,
        "nodes_extracted": 8,
        "by_type": {"claim": 4, "evidence": 3, "assumption": 1},
        "intra_tensions": 1,
        "chunks_matched": 7,
        "chunks_fallback_embedding": 1
    },
    "phase_b": {
        "duration_ms": 12500,
        "existing_graph_size": 42,
        "context_nodes_used": 30,
        "context_strategy": "pgvector_topk",
        "edges_created": 5,
        "tensions_surfaced": 1,
        "status_updates": 2,
        "gaps_identified": 1
    },
    "phase_c": {
        "duration_ms": 2100,
        "narrative_length": 187
    },
    "total_duration_ms": 23800,
    "total_llm_calls": 3,
    "estimated_cost_usd": 0.07
}
```

This lets us track extraction quality over time, identify slow phases, and catch degradation early.

---

## Extraction Granularity: Assertional Significance

The extraction engine must produce nodes at the right level of granularity. Too granular and the graph is noisy. Too broad and it's useless.

**The test: assertional significance.** Extract at the level where someone could meaningfully agree or disagree with the statement. If a reasonable person could say "I disagree with that" or "that contradicts my data," it belongs in the graph. If it's just background noise or a data point with no argumentative function, it stays in chunks.

| Level | Example | Extract? |
|-------|---------|----------|
| Too granular | "Revenue was $10M in Q4" | No — raw data point, lives in chunks |
| Right level | "The company claims revenue growth is accelerating, citing $10M Q4 revenue" | Yes — assertional, someone could contest the "accelerating" interpretation |
| Too broad | "The document discusses the company's finances" | No — meta-description, not a knowledge claim |

**Individual data points** (a single number, a single name, a bare statistic) stay in chunks for retrieval. They become nodes only when they carry argumentative weight — when they support, contradict, or underpin a claim.

**The extraction prompt enforces this** with specificity rules and bad/good examples. The `_EXTRACTION_SYSTEM_PROMPT` includes explicit instructions to skip boilerplate and extract only substantive, falsifiable assertions.

---

## Node Importance Scoring

Every extracted node carries an importance score as an integer in `properties.importance`:

| Score | Label | Description | Max per document |
|-------|-------|-------------|-----------------|
| **3** | Core | The document's thesis or central argument | 1-2 |
| **2** | Supporting | Claims, evidence, or assumptions that directly support the core argument | Unlimited |
| **1** | Peripheral | Background context, minor details, tangential observations | Unlimited |

### Design decisions

- **Integer, not float.** Three levels are enough for prioritization. Float precision (0.0-1.0) implies false granularity and makes it harder to sort/filter.
- **Stored in `properties` JSONField, not a model column.** Avoids a migration for a field that's only used for sorting/display. Queried in Python on already-fetched querysets (orientation view groups are small).
- **Default for legacy nodes: 2.** Existing nodes without importance are treated as supporting — a safe middle ground.

### Where importance is used

1. **Orientation view** — Each category (contradictions, hidden_assumptions, agreements, gaps) is sorted by importance descending. Core nodes appear first.
2. **LLM serialization** — When `max_nodes` limit is hit, importance=3 nodes are always included. Importance=1 nodes are dropped first.
3. **Document subgraph view** — The per-document argument structure shows the thesis first, then supporting nodes, then peripheral details.

---

## Document Role Taxonomy

Every extracted node also carries `properties.document_role` describing its function within the source document's argument structure:

| Role | Description | Typical node_type | Typical importance |
|------|-------------|-------------------|-------------------|
| `thesis` | The document's central argument or conclusion | claim | 3 |
| `supporting_claim` | A claim that supports the thesis | claim | 2 |
| `supporting_evidence` | Evidence cited to back up claims | evidence | 2 |
| `foundational_assumption` | An assumption the argument depends on | assumption | 2-3 |
| `counterpoint` | A counter-argument or qualification | claim, tension | 2 |
| `background` | Context or background information | evidence, claim | 1 |
| `detail` | Minor or peripheral detail | any | 1 |

Role and importance are related but not redundant. Role describes **function** (what this node does in the argument), importance describes **priority** (how central it is). A `foundational_assumption` could be importance=3 (if the entire argument collapses without it) or importance=2 (if it's one of several load-bearing assumptions).

---

## Intra-Document Edges (Phase A)

Phase A now creates edges within a single document, not just nodes. This gives each document an internal argument structure:

```
[thesis] The company should expand into enterprise
    ↑ supports
[supporting_claim] Enterprise deals have 3x higher LTV
    ↑ supports
[supporting_evidence] Pilot with Acme Corp yielded $500K ARR
    ↑ depends_on
[foundational_assumption] Enterprise sales cycle is manageable (6 months)
```

### Edge types in Phase A

| Edge type | Meaning | Example |
|-----------|---------|---------|
| `supports` | Source provides evidence/reasoning for target | Evidence → Claim, Sub-claim → Thesis |
| `depends_on` | Source requires target to hold | Claim → Assumption it relies on |
| `contradicts` | Source conflicts with target | Intra-document inconsistency |

### Edge creation flow

The extraction prompt asks the LLM to return both `nodes` and `edges` in a single call:

```json
{
  "nodes": [
    {"id": "n0", "type": "claim", "content": "...", "importance": 3, "document_role": "thesis", ...},
    {"id": "n1", "type": "evidence", "content": "...", "importance": 2, "document_role": "supporting_evidence", ...}
  ],
  "edges": [
    {"source_id": "n1", "target_id": "n0", "edge_type": "supports"}
  ]
}
```

Temp IDs (`n0`, `n1`...) are resolved to real Node UUIDs after creation. Edges are created via `GraphService.create_edge()` with `source_type='document_extraction'` and `source_document` set.

Phase B (integration) then adds **cross-document** edges on top of these intra-document edges.

---

## Long Document Handling

Documents exceeding 80K tokens (roughly 60+ pages) don't fit in a single Sonnet context window with room for the prompt and response. The extraction pipeline handles this with a two-pass approach:

### Pass 1: Section extraction with summary context

1. **Generate document summary** via Haiku (3-4 sentences from the first ~8K tokens). Cheap and fast.
2. **Split text into sections** at paragraph boundaries, each section ≤80K tokens.
3. **Extract per-section** with the full extraction prompt, plus a preamble:
   ```
   You are extracting from SECTION {i} of {n} of "{title}".
   DOCUMENT SUMMARY: {summary}
   ```
   The summary gives each section extraction enough context to understand the broader argument.
4. **Prefix temp IDs** with section index (`s0_n0`, `s1_n0`) to avoid collisions.

### Pass 2: Deduplication + consolidation

After all sections are extracted:

1. **Embedding-based deduplication.** Generate embeddings for all extracted nodes. Pairs with cosine similarity > 0.90 are duplicates. Keep the node with higher importance (or longer content as tiebreaker). Remap edge IDs to surviving nodes.

2. **Consolidation LLM call** (only if >2 sections). Receives all deduplicated nodes (compact format, no full document text) and:
   - Assigns a document-wide thesis (which section extraction couldn't confidently do)
   - Creates cross-section edges (evidence from section 1 supporting a claim in section 3)
   - Detects cross-section tensions

Most V1 target documents (pitch decks, reports, memos) are under 30K tokens and use the single-call path. The two-pass approach is a safety net for large documents, not the common case.

---

## Document Deletion Cascade

`Node.source_document` and `Edge.source_document` use `on_delete=models.CASCADE`. When a document is deleted:

1. All nodes with `source_document=that_document` are deleted
2. Django's CASCADE on `Edge.source_node` and `Edge.target_node` deletes all edges connected to those nodes
3. All edges with `source_document=that_document` (intra-document edges) are also deleted directly
4. The `GraphDelta` rows for that document have `source_document=SET_NULL` — they survive as historical records

### Why CASCADE, not SET_NULL

Nodes extracted from a document that no longer exists have no value and no provenance. A node saying "Document claims TAM is $4.2B" is meaningless if the document is gone — the user can't verify it, can't trace it, can't trust it. Better to cleanly remove it and let the graph reflect only knowledge with verifiable sources.

**Nodes created via chat** (`source_document=None`) are unaffected by document deletion. **Nodes created by integration** (with `source_type='integration'`) also typically have `source_document=None` and survive.

### Re-extraction on re-upload

If a user re-uploads an updated version of a document, the old document's nodes are CASCADE-deleted, and the new document goes through fresh extraction. This is simpler and more correct than trying to diff and merge extracted nodes from two versions of the same document.
