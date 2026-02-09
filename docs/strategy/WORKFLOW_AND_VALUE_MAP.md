# Workflow & Value Map

The epistemic orientation workflow in v1, with feature-to-value mapping.

---

## [V1 SCOPE] The Orientation Workflow

Episteme's v1 implements a single coherent mode: **structured orientation** — making assumptions and contradictions visible through graph visualization and conversational editing.

```
USER UPLOADS DOCUMENTS OR STARTS CONVERSATION
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  GRAPH CONSTRUCTION (automatic)                      │
│  Extract claims, assumptions, contradictions         │
│  → Build structured node/edge graph                  │
│  → Detect contradictions via embedding similarity    │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
            ┌──────────────────────┐
            │  GRAPH VISUALIZATION │  ← Orientation
            │  (see the structure) │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ CONVERSATIONAL EDITING│  ← Refine
            │ Talk to agent, graph │     the graph
            │    updates in place   │
            └──────────────────────┘
```

**Meta-principle:** Help you think, not think for you. The graph is the product. Everything else is a lens on it.

---

## Core Workflow: Upload Docs → Extract Graph → See Structure → Converse

### Stage 1: Dump & Discover (Entry Point)

**Goal:** Overcome "I can't see the forest for the trees."

**User experience:**
- Upload documents (PDFs, notes, links) — no structure required
- System produces Evidence Map showing: agreements, contradictions, gaps, hidden assumptions
- One-click "Investigate" on any tension → creates case with pre-loaded context

**Features active:**

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| Bulk ingestion | Universal pipeline: PDFs, URLs, notes | Everything feeds one system |
| Cross-document analysis | Extract claims, find contradictions via embeddings | Visible agreements and fights |
| Assumption surfacing | Identify what's claimed but not proven | See your bets |
| Gap analysis | What should be present but isn't? | Absence becomes visible |
| Evidence Map render | Four-section diagnosis, not summary | Diagnosis of your information landscape |

**Transformation:**

| Before | After |
|--------|-------|
| "I have 8 documents" | "I can see where they agree, fight, and stay silent" |
| Hidden contradictions | Explicit contradictions with source references |
| Unknown unknowns | Named gaps with suggested investigation areas |

---

### Stage 2: Graph Visualization (Orientation)

**Goal:** See the state of your thinking made visible.

**User experience:**
- View graph: nodes (assumptions, claims, evidence), edges (relationships), visual indicators (grounded/ungrounded/conflicted)
- Zoom in/out, explore clusters, see what's central vs. peripheral
- Contradiction indicators highlight where sources fight

**Features active:**

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| Node visualization | Assumptions, claims, evidence as distinct nodes | See what you're thinking |
| Edge visualization | Relationships: supports, contradicts, relates-to | See why it matters |
| Grounding indicators | Visual markers: evidence-linked vs. floating | See what's proven |
| Contradiction highlighting | Explicit conflict markers on edges | See where docs fight |
| Interactive exploration | Click to dive deeper, collapse clusters | Active understanding, not passive reading |

**What the graph shows:**

```
Graph Node Types (V1):
├── Assumption (user belief, may be untested)
├── Claim (extracted from documents)
├── Evidence (sourced, credibility-rated)
│
Edge Types (V1):
├── SUPPORTS (evidence backs assumption)
├── CONTRADICTS (evidence challenges assumption)
├── RELATES_TO (assumptions depend on each other)
└── SOURCE (evidence comes from document)
```

**Transformation:**

| Before | After |
|--------|-------|
| "This seems reasonable" | "This is grounded in 2 sources and contradicts 1" |
| Mental model is implicit | Mental model is explicit and visual |
| Can't see dependencies | Can see what depends on what |

---

### Stage 3: Conversational Editing (Refinement)

**Goal:** Talk naturally; graph updates accordingly.

**User experience:**
- Chat with agent about the topic
- Agent understands graph structure, not just words
- Corrections, refinements, new assumptions → agent updates the graph
- See the graph react in real-time to your conversation

**Features active:**

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| Natural language → graph edits | "Actually, I think X is more important" | Agent refines the graph automatically |
| Assumption refinement | "Let me clarify that assumption" | Direct conversation interface to structure |
| Evidence addition | "I found a source that says..." | Evidence integrates into graph immediately |
| Contradiction resolution | "This doc contradicts my earlier thinking" | Agent helps reconcile the conflict |
| Agent-as-questioner | "What would change your mind about X?" | Agent challenges grounded in actual graph state |

**The conversational flow:**

```
User: "Actually, the regulatory constraint is lower than I thought"
  ↓
Agent: "OK, I'm updating that assumption from 'High barrier' to 'Medium'.
        That affects: your timeline assumption, your go-to-market options,
        and your risk assessment. Here's what changed."
  ↓
Graph: Assumption updated, cascading consequences shown
  ↓
User sees: Delta view — what changed due to this refinement
```

**Transformation:**

| Before | After |
|--------|-------|
| Edits are destructive (lose old thinking) | Edits are recorded; full history preserved |
| Conversation and structure are separate | Conversation refines structure in real-time |
| "Here's my thinking" (static) | "Here's my current thinking" (evolving) |

---

## Feature → Value Mapping [V1]

| Feature | Purpose | Value |
|---------|---------|-------|
| **Graph Model** | Structure beliefs, evidence, relationships | See your thinking made visible |
| **Contradiction Detection** | Auto-find where sources fight | Surface hidden conflicts |
| **Assumption Extraction** | Identify untested beliefs | Know what you're betting on |
| **Gap Analysis** | Detect absence, not just presence | See what's missing |
| **Evidence Linking** | Connect proof to claims | Ground your thinking |
| **Conversational Editing** | Refine graph through natural chat | Talk, not forms |
| **Delta View** | Show impact of new information | Every document changes something |
| **Event Sourcing** | Immutable history | "How did we get here?" is always answerable |

---

## [FUTURE SCOPE] The Full Journey (Post-V1)

V1 implements **orientation only** — structure + visibility. Future versions add:

- **Readiness (Post-V1):** Track evidence sufficiency, unlock gates, confidence calibration
- **Plan (Post-V1):** Investigation roadmap, assumption testing, staged progress
- **Brief (Post-V1):** Narrative synthesis, output export, stakeholder deliverables

These four lenses (Graph, Readiness, Plan, Brief) will eventually give you "one state, four views." V1 delivers the Graph lens fully and foundation for the others.

---

## The Meta-Principle

**We help you think. We don't think for you.**

The workflow doesn't prescribe a path. It lets you:
- Dump documents and see contradictions
- Talk naturally and refine the graph
- Explore visually and find blind spots
- Return whenever you have new information

The system's job is to make your thinking visible and highlight what's missing. Your job is to decide what to do about it.
