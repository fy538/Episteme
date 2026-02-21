# Workflow & Value Map

The five-stage decision investigation workflow, with feature-to-value mapping.

---

## The Decision Investigation Workflow

Episteme implements a five-stage workflow that matches natural cognitive progression from confusion to grounded confidence — and then to learning:

```
┌─────────────────────────────────────────────────────────────────┐
│  ORIENT (Project)                                               │
│  Upload documents → hierarchical clustering → landscape view    │
│  → See what your docs cover, where they fight, what they miss  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  EXPLORE (Chat)                                                 │
│  Talk to organic companion → structure emerges from conversation│
│  → Decision trees, checklists, comparison frameworks, probes   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  INVESTIGATE (Case)                                             │
│  CEAT extraction → assumption tracking → blind spot detection   │
│  → See what you're betting on without proof                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  DECIDE (Capture)                                               │
│  Record decision → rationale → confidence → caveats             │
│  → Formal artifact: what you decided, and why                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LEARN (Outcome)                                                │
│  30/60/90 day check-ins → record what happened → calibrate      │
│  → Personal decision intelligence over time                     │
└─────────────────────────────────────────────────────────────────┘
```

**Meta-principle:** Help you think, not think for you. Structure emerges from your words. The system's job is to make your thinking visible and highlight what's missing.

---

## Stage 1: Orient — Project Landscape

**Goal:** Overcome "I can't see the forest for the trees."

**User experience:**
- Create a project for a domain of concern
- Upload documents (PDFs, notes, links) — no structure required
- System builds a hierarchical theme map using RAPTOR-style recursive agglomerative clustering
- LLM summaries at each level of the hierarchy explain what themes contain
- Landscape view reveals coverage depth and gaps

**Features active:**

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| Hierarchical clustering | Documents → chunks → embeddings → recursive agglomerative clustering with LLM summaries | See thematic structure of your knowledge |
| Gap detection | Compare what's present against what should be present | Absence becomes visible |
| Landscape view | Interactive hierarchy with coverage indicators | Navigate, don't read |
| Document accumulation | Add docs over time; hierarchy rebuilds | Knowledge compounds |

**Transformation:**

| Before | After |
|--------|-------|
| "I have 8 documents" | "I can see 4 themes, 2 gaps, and 1 area of contradiction" |
| Hidden contradictions | Explicit: "These 2 sources disagree on growth rate" |
| Unknown unknowns | Named gaps: "Nothing addresses unit economics" |

---

## Stage 2: Explore — Companion Conversation

**Goal:** Think through your situation with a partner that builds structure, not just answers.

**User experience:**
- Chat within a project context — companion accesses all project documents
- Companion detects thinking mode and adapts behavior:
  - Decision mode → decision tree
  - Comparison mode → comparison framework
  - Risk mode → failure scenarios + assumptions
  - Exploration mode → clarifying loop
- Structure emerges organically from conversation
- When a decision point crystallizes, companion suggests creating a case

**Features active:**

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| Organic companion | Structure-aware agent that detects thinking mode | Structure from words, not forms |
| Decision tree building | Automatic when companion detects decision mode | See options you hadn't explicitly compared |
| Checklist generation | Automatic for risk/readiness contexts | Know what needs addressing |
| Comparison frameworks | Automatic when comparing options | Side-by-side with assumption tracking |
| Clarifying loop | Probing questions when thinking is vague | Sharpen your reasoning before investigating |
| Case suggestion | Companion detects investigation-ready decision points | Natural bridge to rigorous analysis |

**Transformation:**

| Before | After |
|--------|-------|
| "ChatGPT agreed with me" | "The companion built a decision tree and surfaced 3 untested assumptions" |
| Conversation disappears | Structure persists — come back tomorrow |
| You ask for a framework | Framework emerges from your words |

---

## Stage 3: Investigate — Case Analysis

**Goal:** Get a specific decision right with rigor.

**User experience:**
- Case created from companion conversation or manually via QuickCaseModal
- Decision question serves as a focusing lens
- CEAT extraction applied: Claims, Evidence, Assumptions, Tensions
- Assumption lifecycle tracking: untested → confirmed → challenged → refuted
- Blind spot detection identifies what hasn't been considered
- Stage progression: exploring → investigating → synthesizing → ready

**Features active:**

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| CEAT extraction | Extract Claims, Evidence, Assumptions, Tensions from case context | Structured reasoning landscape |
| Assumption tracking | Lifecycle: untested → confirmed/challenged/refuted | Know what you're betting on |
| Blind spot analysis | Detect areas not addressed by current investigation | See what you're missing |
| Evidence linking | Connect evidence to specific assumptions | Ground your reasoning |
| Readiness tracking | Stage-adaptive progression through investigation | Know when you're ready vs. tired |
| Delta view | "What did this document change about your decision?" | Every upload is consequential |
| Document upload + cascade | New evidence triggers assumption status recomputation | Living investigation, not static analysis |

**Transformation:**

| Before | After |
|--------|-------|
| "I feel ready" | "5 of 7 assumptions tested. 2 tensions acknowledged. 1 blind spot remaining." |
| "I have a lot of research" | "Research linked to specific assumptions — I can see what it proves and what it doesn't" |
| "This doc seems relevant" | "This doc confirmed 1 assumption, challenged another, and raised 2 new questions" |

---

## Stage 4: Decide — Decision Capture

**Goal:** Record what you decided and why, while the reasoning is fresh.

**User experience:**
- Case reaches "ready" stage — system prompts for decision
- Record DecisionRecord: decision text, key reasons, confidence (0-100), caveats
- System links decision to specific assumptions being bet on
- Set outcome check date: 30, 60, or 90 days
- Case status moves to "decided"

**Features active:**

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| DecisionRecord | Formal artifact: decision, reasons, confidence, caveats | Accountable reasoning |
| Assumption linking | Decision linked to specific assumptions being bet on | Know exactly what you're risking |
| Outcome check date | Set 30/60/90 day reminder | Built-in accountability |
| Case status transition | Case moves to "decided" | Clear lifecycle completion |

**Transformation:**

| Before | After |
|--------|-------|
| "We decided to go enterprise-first" | "We decided enterprise-first because [3 reasons]. Confidence: 65%. Betting on [2 untested assumptions]. Check back April 15." |
| Decision rationale lost to memory | Decision rationale captured formally at the moment of decision |

---

## Stage 5: Learn — Outcome Tracking

**Goal:** Come back later and see how it turned out. Become a better thinker over time.

**User experience:**
- System reminds at outcome check date
- Record what actually happened — which assumptions were right, which were wrong
- See confidence calibration over time
- Build personal decision journal revealing patterns

**Features active:**

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| Outcome reminders | Periodic task checks for due outcome reviews | Don't forget to learn |
| Outcome notes | Record what happened against original decision | Close the loop |
| Assumption validation | See which assumptions held vs. failed | Learn your blind spots |
| Decision journal | Accumulated history of decisions + outcomes | Personal decision intelligence |

**Transformation:**

| Before | After |
|--------|-------|
| "Why did we make that choice?" | Full record: rationale, confidence, caveats, what actually happened |
| Same mistakes repeated | "I'm consistently overconfident about timelines" — adjust next time |
| No feedback loop | Decisions → outcomes → patterns → better future decisions |

---

## Feature → Value Mapping (Complete)

| Feature | Stage | Purpose | Value |
|---------|-------|---------|-------|
| **Hierarchical clustering** | Orient | Build thematic structure from documents | See the landscape, not just the docs |
| **Gap detection** | Orient | Detect absence, not just presence | See what's missing |
| **Organic companion** | Explore | Build structure from conversation | Structure from words, not forms |
| **Thinking mode detection** | Explore | Adapt behavior to user's cognitive mode | Right structure at the right time |
| **CEAT extraction** | Investigate | Extract Claims, Evidence, Assumptions, Tensions | Structured reasoning landscape |
| **Assumption lifecycle** | Investigate | Track untested → confirmed/challenged/refuted | Know what you're betting on |
| **Blind spot analysis** | Investigate | Detect what hasn't been considered | See what you're missing |
| **Delta view** | Investigate | Show impact of new information | Every upload changes something |
| **Evidence linking** | Investigate | Connect proof to claims | Ground your thinking |
| **DecisionRecord** | Decide | Capture decision with rationale | Accountable decisions |
| **Outcome tracking** | Learn | Record what actually happened | Learn from your decisions |
| **Confidence calibration** | Learn | Track prediction accuracy over time | Become a better thinker |
| **Event sourcing** | All | Immutable audit trail | "How did we get here?" is always answerable |
| **Conversational editing** | All | Talk to the agent, agent edits the state | Natural interaction, not forms |

---

## Implementation Roadmap

The five-stage workflow is built across nine implementation plans:

### Foundation (Implemented)
- **Plan 1**: Hierarchical document clustering — RAPTOR-style recursive clustering, project landscape view
- **Plan 2**: Organic companion — structure-aware agentic chat, thinking mode detection, clarifying loop
- **Plan 3**: Case extraction — CEAT graph extraction, blind spot analysis, assumption tracking

### Feature Polish (Designed)
- **Plan 4**: RAG citations — source-grounded responses with numbered citation markers
- **Plan 5**: Case graph visualization — interactive CEAT graph with ReactFlow
- **Plan 6**: Hierarchy refresh + change detection — theme evolution tracking across rebuilds

### Product Completeness (Designed)
- **Plan 7**: Project discovery + onboarding — project list page, first-run experience, NewProjectModal
- **Plan 8**: Case creation preview + companion bridge — editable CasePreviewCard, QuickCaseModal
- **Plan 9**: Decision capture + outcome tracking — DecisionRecord model, outcome journal, check-in reminders

---

## The Meta-Principle

**We help you think. We don't think for you.**

The workflow doesn't prescribe a path. It lets you:
- Upload documents and see the landscape
- Talk naturally and watch structure emerge
- Investigate decisions with tracked assumptions
- Record what you decided and why
- Come back later and learn from the results

The system's job is to make your thinking visible, highlight what's missing, and help you learn from every decision you make. Your job is to decide what to do about it.
