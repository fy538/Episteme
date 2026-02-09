# Decision State Architecture

The architectural doctrine for Episteme. Every feature, every view, every interaction pattern derives from this document.

---

## The Doctrine

**Projects are for memory. Cases are for thinking. Decisions are just one kind of case outcome.**

Episteme maintains a **Project** — a long-lived sensemaking container — and spawns **Cases** within it as focused cognitive episodes. Everything the user sees is a derived projection of graph state. Nothing is edited independently. The state is the product.

> One project, many cases, one graph, four lenses: orientation (graph), permission (readiness), momentum (plan), memory (brief).

If every feature respects this, the product feels inevitable instead of clever.

---

## Why This Architecture

The research is unambiguous: humans feel ready to decide when a plausible story exists where key assumptions are visible, tensions are acknowledged, uncertainty feels bounded, and a workable path forward is imaginable.

Not optimality. Not certainty. Plausibility + bounded risk + commitment affordance.

That means Episteme is not "decision support" in the abstract. It is a **story-construction engine constrained by reality**. The graph is the story. The four lenses are the ways humans need to see it.

But decisions are only one cognitive mode. Before deciding, people need to orient, frame, explore, and bound risk. The architecture must serve all of these — without forcing anyone to pretend they have a decision when they don't.

---

## The Hierarchy: Projects → Cases → Decision State

### Projects: Domains of Concern

A Project is not a decision. It is a **domain of concern** — a long-lived container where confusion is allowed to live.

Examples:
- "Our startup's technical direction"
- "Go-to-market exploration"
- "Fundraising prep"
- "2026 product strategy"

**What a Project handles:**
- Document ownership (all documents belong here, never to cases)
- Ongoing orientation (the permanent landscape view)
- Accumulation of evidence, claims, assumptions, tensions over time
- Long-term context and memory

**What a Project never does:**
- Require commitment
- Show readiness gating
- Push toward a decision
- Generate a plan with blockers

The Project graph is always in orientation mode. It grows with every document upload and every case resolution. It is the founder's evolving understanding of their domain.

```
Project {
    id: uuid
    title: string                        // "Our startup's technical direction"
    documents: Document[]                // All documents live here
    graph: Graph                         // The orientation graph — always active
    cases: Case[]                        // Focused episodes within this project
    created_at: datetime
}
```

### Cases: Focused Cognitive Episodes

A Case is a **temporary subgraph + governance rules over the persistent project knowledge base.**

A Case has:
- A specific **Focus** (what are we looking at?)
- A specific **Mode** (how are we looking at it?)
- A specific **intent** (even if that intent is "understand")

Cases are time-bounded, cognitively scoped, and structurally opinionated.

Examples of Cases inside the same Project ("Our startup's technical direction"):
- "Is our current infra enterprise-ready?" (decision mode)
- "What are the scalability risks?" (risk bounding mode)
- "What's actually contested in our architecture?" (orientation mode)
- "Should we refactor now or later?" (decision mode)
- "Postmortem: latency incident" (post-decision review)

All drawing from the same underlying Project knowledge.

```
Case {
    id: uuid
    project: Project
    mode: orientation | framing | exploration | risk_bounding | decision | post_decision

    frame: {
        focus: string                    // "Should we pivot?" or "What are the scalability risks?"
        focus_type: situation | question | decision | hypothesis
        scope?: string
        success_criteria?: string[]      // May be empty outside decision mode
        stakes: low | medium | high
    }

    subgraph_selector: {
        included_nodes: NodeRef[]        // References to project-level nodes
        inclusion_strategy: manual | agent_inferred | semantic_query
        query?: string                   // For re-evaluation as case evolves
    }

    case_nodes: Node[]                   // Case-specific: Options, Scenarios, case-level Assumptions
    case_edges: Edge[]                   // Edges between case nodes and/or project nodes

    governance: {
        readiness_active: boolean        // Derived from mode, overridable
        plan_active: boolean
        commitment_available: boolean
        section_locking: boolean
    }

    patches: DeltaEvent[]                // All mutations within this case
    snapshots: Snapshot[]                // For post-decision review

    status: active | resolved | committed | archived
}
```

### Why This Separation Matters

**1. It solves "dump first, decide later" cleanly.** With Projects, the entry point is "dump everything here, we'll orient first." No fake decision questions. No premature framing. When the founder is ready, they open a Case — the agent infers a mode, focuses a subset of the graph, and applies governance. This feels natural instead of forced.

**2. It prevents cognitive overload.** Without Projects, every Case carries all context. With Projects, the project graph can be massive — each Case shows only a relevant slice. Progressive disclosure stays intact. The ~7 node constraint applies to what's visible in a case, not to the total knowledge base.

**3. It matches how real work evolves.** Founders don't make one decision and close the book. They circle a domain for months — revisiting the same facts under different questions, learning, revising, reinterpreting. Projects give continuity. Cases give focus.

### How Knowledge Flows Between Levels

```
PROJECT LEVEL                          CASE LEVEL
─────────────                          ──────────
Documents ──────────────────────────→  Referenced (never duplicated)
Evidence ───────────────────────────→  Referenced; new evidence promotes UP
Claims ─────────────────────────────→  Referenced
Assumptions ────────────────────────→  Referenced; confirmations/refutations promote UP
Tensions (surfaced) ────────────────→  Referenced; resolutions promote UP
                                       Options ← Case-specific (stay DOWN)
                                       Scenarios ← Case-specific (stay DOWN)
                                       Implementation intentions ← Case-specific (stay DOWN)
```

**Clear rules:**

| Node Type | Ownership | Promotion Rule |
|-----------|-----------|---------------|
| Documents | Project always | Never duplicated. Cases interpret. |
| Evidence | Project | New evidence from case investigation promotes to project. Other cases benefit. |
| Claims | Project | Extracted from documents at project level. |
| Assumptions | Project (canonical) | Cases can reference or create case-level variants. Confirmations/refutations flow back to project. |
| Tensions | Project (surfaced) | Resolution recorded at case level, then project tension status updates. |
| Options | Case only | Specific to a decision. Don't belong in the permanent knowledge map. |
| Scenarios | Case only | Specific to risk bounding or evaluation. |
| Implementation | Case only | Specific to commitment. |

The project gets smarter over time — not just bigger. Every case that confirms an assumption or resolves a tension improves the project's knowledge base for future cases.

### How Cases Spawn

Three ways a case gets created:

**1. From a tension in the project graph.** User clicks a tension ("Pitch deck says no competitors, research says 3") → "Investigate this?" → Creates a case with that tension as the starting point, relevant nodes auto-selected.

**2. From the agent's suggestion.** After orientation, the agent says: "I see three possible directions here. Want to open a case to evaluate them?" → Creates a case with inferred options and mode.

**3. From the user directly.** User says "I need to figure out whether to raise now or bootstrap" → Creates a case in decision mode, agent infers relevant project nodes.

In all three paths, the agent infers the relevant subgraph — the user never manually selects nodes. The agent proposes: "I've pulled in 12 nodes from your project — 4 architecture claims, 3 assumptions about enterprise requirements, 2 tensions, and 3 evidence items. Does this look right?" The user confirms or adjusts. The selector can expand as the case progresses.

### UX: Hiding the Hierarchy Initially

The Project/Case distinction is real architecturally but should be **subtle in the UI**. When someone first dumps docs, they're just "in Episteme" looking at their map. The concept of a "project" doesn't need a name yet.

When they click "investigate this tension" and a case opens, it feels like **zooming in**, not navigating to a new container. The agent says: "I'm opening an investigation into this tension. Your documents are still available — I'll pull in the relevant evidence."

The user discovers the hierarchy naturally. They don't need to understand it to use it.

---

## The Unified Graph Model

Both Project and Case graphs use the same data model: **nodes and typed edges.**

```
Node {
    id: uuid
    type: Focus | Option | Assumption | Evidence | Tension | Uncertainty | Scenario | Claim
    content: string
    status: varies by type (see below)
    properties: {                    // Type-specific metadata
        load_bearing?: boolean       // Assumptions
        credibility?: 0.0–1.0       // Evidence
        severity?: string            // Scenarios
        source?: string              // Evidence provenance
        ...
    }
    scope: project | case            // Where this node lives
    case_id?: uuid                   // If scope=case, which case owns it
}

Edge {
    id: uuid
    type: supports | contradicts | depends_on | leads_to | scopes | implies | risks
    source: Node
    target: Node
    strength?: 0.0–1.0
    provenance?: string              // Why this edge exists
}
```

Everything is a node. Everything connects via typed edges. Mode determines which subgraph is highlighted and what governance is active. This prevents schema fragmentation — adding a new cognitive mode never requires a migration.

### Node Types and Their Statuses

| Node Type | Statuses | Cognitive Role |
|-----------|----------|----------------|
| **Focus** | active | The root of a case. Always exactly one per case. Orients the graph. |
| **Option** | active · eliminated · chosen · hypothetical | Possible paths forward. Case-level only. May not exist (orientation mode). |
| **Assumption** | untested · confirmed · challenged · refuted | The hidden bets. Bridges evidence to conclusions. Highest-leverage node type. |
| **Evidence** | confirmed · uncertain · disputed | Facts, data, observations. Grounds reasoning in reality. |
| **Tension** | surfaced · acknowledged · resolved | Contradictions, tradeoffs, conflicts. Prevents premature convergence. |
| **Uncertainty** | open · investigating · resolved | Open questions. What we don't know yet. |
| **Scenario** | plausible · unlikely · materialized | Future states. "If assumption X fails, then..." Case-level only. |
| **Claim** | supported · contested · unsubstantiated | Assertions from documents or conversation. Primary node type in orientation. |

### The Focus Node

The root of every case graph is a **Focus** — not necessarily a decision.

```
Focus {
    content: string                  // "Should we enter Japan?" or "What are the scalability risks?"
    focus_type: situation | question | decision | hypothesis
    scope?: string
    success_criteria?: string[]      // May be empty outside decision mode
    stakes: low | medium | high
}
```

A case doesn't require a decision to be valuable. Someone bounding risk (focus_type: `hypothesis`) or framing a problem (focus_type: `question`) gets value from the same engine as someone making a decision (focus_type: `decision`).

### Options as a Phase Transition

Options are not always present. In orientation mode, assumptions and evidence attach to claims and to each other. The graph is a knowledge map.

**The moment options appear, the graph reorganizes.** Assumptions attach to options. Evidence flows through assumptions to support or undermine specific paths. Tensions become tradeoffs between paths rather than just contradictions.

This is a **structural event**, not just a UI change:

> "I'm seeing alternatives emerge in your thinking. Should I restructure this as a decision?"

The transition from "understanding" to "evaluating" happens naturally. Nobody is forced to declare a decision prematurely.

---

## Cognitive Modes

The graph schema is **mode-agnostic**. Mode is a **rendering and policy layer**, not a data model change.

### The Six Modes

| Mode | Focus Type | What the User Feels | Governance Active |
|------|-----------|---------------------|-------------------|
| **Orientation** | situation | "What's going on here?" | None. No commitment expected. |
| **Problem Framing** | question | "What is the real problem?" | None. Multiple frames may coexist. |
| **Exploration** | hypothesis | "What are the possibilities?" | None. Options are `hypothetical`. |
| **Risk Bounding** | decision | "What could go wrong?" | Partial. Load-bearing paths highlighted. |
| **Decision** | decision | "What should I do?" | Full. Readiness gating, plan, commitment. |
| **Post-Decision Review** | decision | "Did we do the right thing?" | Retrospective. Graph frozen, outcome overlay. |

### Mode as Rendering + Policy

Mode changes three things. It does **not** change the schema.

**1. UI emphasis** — which node types are visually prominent, which are faded

**2. Governance rules** — whether readiness gating is active, whether the plan generates blockers, whether commitment is available

**3. Agent behavior** — what the assistant suggests, how it challenges, what questions it asks

| Mode | Graph Shows | Readiness Shows | Plan Shows | Brief Produces |
|------|------------|----------------|-----------|----------------|
| **Orientation** | Claim clusters, evidence, tensions. Focus as root. | Coverage: "3 themes mapped, 2 gaps, 1 contested" | Optional: "Areas to investigate" | Landscape summary |
| **Problem Framing** | Competing frames, how each changes what matters | Frame clarity: "2 competing frames, assumptions diverge on X" | Not shown | Frame comparison |
| **Exploration** | Hypothetical options, speculative assumptions | Not shown | Not shown | Possibility map |
| **Risk Bounding** | Load-bearing paths highlighted, failure scenarios | Downside bounded: "2 of 4 load-bearing assumptions stress-tested" | "Assumptions to stress-test" | Risk assessment |
| **Decision** | Full layered DAG: Focus → Options → Assumptions → Evidence | Full structural readiness rules | Blocker-derived investigation plan | Decision brief with rationale |
| **Post-Decision** | Frozen graph with held/failed/materialized overlay | Outcome coverage: "3 of 5 key assumptions assessed" | "What to learn / change" | Postmortem |

### Mode Detection

Modes are **inferred by the agent**, not selected from a dropdown.

| Signal | Inferred Mode |
|--------|--------------|
| User uploads docs, asks "what's in here?" | Orientation |
| User challenges the frame or asks "what's the real problem?" | Problem Framing |
| User says "what are the possibilities?" without convergence intent | Exploration |
| User says "what could go wrong?" or "what am I missing?" | Risk Bounding |
| User states alternatives ("should I do X or Y?") | Decision |
| User references a past committed case | Post-Decision Review |

Transitions are fluid. A session might flow: Orientation → Problem Framing → Decision → Risk Bounding → Decision → Commit → (later) Post-Decision Review.

### Mode Transitions as Patches

Mode transitions are **structural mutations**, not UI toggles. Implemented as versioned patches, like every other state change.

**Example: Orientation → Decision**

```
Patch {
    trigger: mode_transition
    changes: [
        { case.mode: "orientation" → "decision" },
        { frame.focus_type: "situation" → "decision" },
        { frame.focus: "SE Asian fintech landscape" → "Should we enter the SE Asian fintech market?" },
        { create: Option("Enter via partnership"), Option("Enter directly"), Option("Don't enter") },
        { reattach: Assumption[1..4].edges: Claim → Option (inferred linkage) },
        { governance.readiness_active: true },
        { governance.plan_active: true },
        { governance.commitment_available: true },
    ]
    narrative: "Decision mode activated. I created 3 options from themes in your map
                and reorganized 4 assumptions to attach to the options they're most
                relevant to. Readiness tracking is now active."
}
```

This gives you: explainability, reversibility, versioning, and trust.

### The Rule for Schema Changes

> Every schema change must be justified by Decision Mode v1. If it's only needed for a future mode, postpone.

Orientation mode is mostly Decision mode with governance *subtracted*. The mode-agnostic graph means future modes are enabled by the flexible Focus, optional Options, and unified Node/Edge model — not by new tables or fields.

---

## The Four Lenses

Each lens serves a distinct cognitive job. If a lens isn't performing its job, it doesn't earn its place.

### Lens 1: The Graph → Orientation

**Cognitive job:** Reduce working memory overload. Make relationships visible. Answer: "What's going on here?"

The graph renders the state as a layered directed acyclic graph (DAG). **Always single-rooted** — the Focus node is always the root. This preserves consistent layout, consistent navigation, and a simpler mental model.

**Layout in Decision Mode:**

```
Layer 1 (top):     Focus (decision frame + success criteria)
Layer 2:           Options (branching horizontally)
Layer 3:           Assumptions + Evidence (clustered under options they support)
Layer 4 (bottom):  Tensions + Scenarios
```

**Layout in Orientation Mode:**

```
Layer 1 (top):     Focus (situation/topic)
Layer 2:           Claim clusters
Layer 3:           Evidence + Assumptions (attached to claims)
Layer 4 (bottom):  Tensions + Gaps
```

Same layout algorithm (Sugiyama). Same visual grammar. Different node types emphasized.

**Visual grammar (node types):**

| Node | Visual | Cognitive Role |
|------|--------|----------------|
| Focus | Large rectangle, bold border, top position | The root. Orients attention, defines scope. |
| Option | Rounded rectangle, branching from Focus | Generates possibility space. |
| Assumption | **Dashed border**, amber/yellow | The hidden bet — bridges evidence to conclusions. |
| Evidence | Circle/oval, green (confirmed) or yellow (uncertain) | Grounds reasoning in reality. |
| Tension | Diamond, red/orange | Prevents premature convergence. |
| Claim | Solid border, neutral gray | Assertions from sources. Primary in orientation mode. |
| Scenario | Rounded diamond, blue | Future states and "what if" projections. |
| Uncertainty | Circle with "?", gray | Open questions. Prompts investigation. |

**Visual grammar (edge types):**

| Edge | Visual | Meaning |
|------|--------|---------|
| Supports | Solid green, arrow toward target | Evidence or reasoning favoring a node |
| Contradicts | Solid red, arrow toward target | Evidence or reasoning opposing a node |
| Depends-on | Dashed gray, arrow toward dependency | Requires this to hold |
| Leads-to | Solid blue, arrow toward outcome | Results in; produces |
| Scopes | Dotted gray | Defines boundaries or limits |
| Implies | Dashed blue, arrow toward implication | Logically entails |
| Risks | Dashed red, arrow toward scenario | Could trigger this failure mode |

**Critical design rules:**

- **Single root always.** The Focus node anchors the graph.
- **Maximum ~7 visible nodes at any interaction level.** Cognitive overload pushes System 2 offline.
- **Orphan assumptions glow amber.** No evidence connections = unexamined beliefs driving reasoning.
- **Ghost nodes** (semi-transparent placeholders) show where evidence *should* exist but doesn't.
- **Auto-layout only.** Users edit through conversation; the graph re-renders.

**What the graph does NOT do:**
- Declare readiness (emergent from structure)
- Recommend options (user's job)
- Hide contradictions behind smooth summaries

### Lens 2: Readiness → Permission

**Cognitive job:** Prevent premature commitment without inducing paralysis. Answer: "Am I actually ready?"

Readiness is a **computed diagnostic** — a function of graph structure and mode. Never self-reported, never declared by the system.

```
readiness = f(graph.structure, case.mode)
```

**In Decision Mode — structural commitment gating:**

| Condition | If Missing |
|-----------|-----------|
| Frame has explicit scope and success criteria | Decision is unanchored |
| ≥2 options connected to Focus | False dilemma / binary thinking |
| Every load-bearing assumption has ≥1 evidence link | Unexamined beliefs driving the decision |
| No unresolved tensions of type `contradiction` | Internal inconsistency |
| At least one option has no show-stopping refuted assumptions | No viable path exists |
| Implementation intentions exist for leading option | Deliberation incomplete |

Readiness surfaces as **specific gaps**, not scores: "3 load-bearing assumptions have no evidence" — not "readiness: 40%."

**In non-decision modes — soft structural diagnostics** (same machinery, different language):

| Mode | Diagnostic Label | Example |
|------|-----------------|---------|
| Orientation | Coverage | "3 themes mapped, 2 gaps, 1 contested cluster" |
| Risk Bounding | Downside bounded | "2 of 4 load-bearing assumptions stress-tested" |
| Problem Framing | Frame clarity | "2 competing frames identified, assumptions diverge on X" |
| Post-Decision Review | Outcome coverage | "3 of 5 key assumptions assessed: 2 held, 1 failed" |

**At the Project level — map health:**

The project orientation graph has its own diagnostic: "4 themes mapped, 6 tensions, 3 gaps, 9 untested assumptions." This is permanent and grows with every document. It's the long-term signal of how well the founder understands their domain.

**Self-reported confidence** (0–100) is captured but used as a *comparison*, not a readiness signal. "Your gut says 80% but three load-bearing assumptions have zero evidence" is a diagnostic. The tension between felt confidence and structural evidence is itself a finding.

### Lens 3: The Plan → Momentum

**Cognitive job:** Convert ambiguity into directed investigation. Answer: "What do I do next to unblock myself?"

The plan is **generated from blockers in the graph**, not authored independently.

Every plan item answers: **"Which unresolved node or tension does this reduce?"**

```
Plan items derive from:
├── Load-bearing assumptions with status=untested → "Investigate: [assumption]"
├── Tensions with status=surfaced → "Resolve: [tension]"
├── Uncertainties with status=open, criticality=blocking → "Answer: [question]"
├── Options with many unlinked assumptions → "Stress-test: [option]"
└── Orphan claims with no evidence → "Validate: [claim]"
```

When a blocker resolves, the corresponding plan item completes automatically. The plan reflects current state — it doesn't need to be "checked off."

**What makes this different from a task list:** A task list says "Research Japanese market regulations." The plan says "Investigate assumption: 'Regulatory approval takes <12 months' — this is load-bearing for Option A and currently has zero evidence. If refuted, Option A becomes non-viable." Intelligent because structural, not managerial.

**Adapts per mode:** In orientation, items are "areas to investigate." In risk bounding, "assumptions to stress-test." Same derivation logic, different language.

### Lens 4: The Brief → Memory

**Cognitive job:** Lock in meaning. Enable communication. Answer: "How do I explain this — to myself or others?"

The brief is a **linear projection of the graph at a moment in time.** Always downstream of the structure — it renders what the graph contains, never generates new reasoning.

The research warns: writing yourself into confidence is dangerous. The brief must be downstream.

**What the brief produces per mode:**

| Mode | Brief Format | Content |
|------|-------------|---------|
| Orientation | Landscape summary | What's known, unknown, contested |
| Problem Framing | Frame comparison | How different frames change what matters |
| Decision | Decision brief | Full rationale with evidence trail |
| Risk Bounding | Risk assessment | Bounded downsides, accepted risks |
| Post-Decision Review | Postmortem | What held, what failed, what to learn |

**Output skills** determine the serialization format: slide deck, ADR, memo, business plan. Different rendering of the same state projection.

---

## The Interaction Model: Conversational State Editing

Users never directly manipulate the graph, fill out forms, or drag nodes. They **converse with an agent that understands the graph**, and the agent makes structural edits.

### The Cursor/Claude Code Analogy

In Cursor, a developer says "refactor this function to use async" and the agent edits the code. In Episteme, a user says:

> "Actually, the real risk isn't regulatory — it's that our distribution partner might not renew."

And the agent:
1. Creates a new Assumption node: "Distribution partner will renew" (status: untested, load_bearing: true)
2. Creates edges: `depends_on` from relevant Options to the new Assumption
3. Adjusts the regulatory assumption's load_bearing flag if appropriate
4. All four lenses update automatically
5. Produces a delta explaining the structural change

One sentence. Structural edit. All lenses update.

### Interaction Patterns

**Natural language → structural edits:**

| User Says | Agent Edits Graph |
|-----------|------------------|
| "I'm choosing between X and Y" | Creates Option nodes, edges from Focus |
| "I think the market will grow 20%" | Creates Assumption (untested), infers option linkage |
| "This report says retention is only 30%" | Creates Evidence, `supports`/`contradicts` edges to relevant Assumptions |
| "These two things can't both be true" | Creates Tension node, edges to conflicting nodes |
| "Actually, forget about Option B" | Sets Option B status to `eliminated`, records reason |
| "What am I missing?" | Runs graph analysis: surfaces orphan assumptions, evidence deserts, ghost nodes |
| "I'm going with Option A" | Initiates commitment flow |

**Document upload → automated structural edits:**

1. Extract claims from document → create Claim or Evidence nodes (at project level)
2. Match claims against existing Assumptions (embedding similarity)
3. Create typed edges (supports/contradicts)
4. Recompute Assumption statuses (cascade)
5. Surface new Tensions if evidence conflicts
6. Detect implied Assumptions not yet in the graph
7. Produce delta explaining what changed
8. Propagate changes to all cases that reference affected nodes

**The "dump and discover" flow:**

User uploads docs into a Project. The system:
1. Builds the project orientation graph (Claims, Evidence, Assumptions, Tensions)
2. Renders the landscape: claim clusters, agreements, contradictions, gaps
3. Shows map health: "14 claims, 9 assumptions, 6 tensions, 3 gaps"
4. Surfaces the reveal: "Your pitch deck contradicts your own competitor research. Your 28% growth claim has no source. Nothing addresses unit economics."

From there, the user can open a Case — from a tension, from the agent's suggestion, or from their own question. Every case starts with momentum because the project already has context.

### What the Agent Understands

The agent has **structural awareness** of the graph:

- Which Assumptions are load-bearing and untested
- Which Options depend on which Assumptions (via `depends_on` edges)
- Where Evidence conflicts exist
- What the graph *should* have but doesn't (ghost nodes / absence detection)
- The current mode and what structural conditions are unmet
- What project-level nodes are relevant but not yet in the case's subgraph

Its questions are graph-informed. Its challenges are structurally motivated. Its suggestions are the plan items with highest structural impact.

### Skill System Integration

Domain skills configure how the agent interprets and edits the graph:

| Skill Layer | What It Configures |
|-------------|-------------------|
| Domain knowledge | What assumptions to look for, what evidence sources matter |
| Evidence standards | Minimum credibility thresholds, triangulation requirements |
| Structural rules | Which assumptions are typically load-bearing in this domain |
| Output formatting | How the brief renders (memo, ADR, slide deck, business plan) |

The skill doesn't change the graph schema. It changes how the agent *populates and validates* it.

---

## The Delta Engine

Every mutation to the graph produces a delta: **what changed, and why it matters.**

### Delta Structure

```
DeltaEvent {
    timestamp: datetime
    trigger: document_upload | user_message | research_loop | cascade | mode_transition
    scope: project | case
    patch: [
        { action: "create", node: Node },
        { action: "create", edge: Edge },
        { action: "update", node_id, field: "status", from: "untested", to: "challenged" },
        { action: "delete", edge_id, reason: "..." },
        { action: "promote", node_id, from: "case", to: "project" }
    ]
    narrative: string                // Human-readable: what changed and why it matters
    impact: {
        readiness_change: progressed | regressed | unchanged
        nodes_affected: Node[]
        new_blockers: integer
        resolved_blockers: integer
        cases_affected: Case[]       // For project-level changes that propagate
    }
    reversible: boolean
    state_version: integer           // Monotonically increasing
}
```

### Delta Propagation

When a project-level node changes (new document uploaded, evidence updated), deltas propagate to every case whose subgraph_selector includes that node:

```
New document uploaded to Project
    → Project graph updates (new Evidence, Claims, Tensions)
    → Delta generated at project level
    → For each Case referencing affected nodes:
        → Case-level delta generated
        → Case readiness/coverage recomputed
        → "New document in your project challenged an assumption relevant to
           Case: 'Should we pivot?' — one load-bearing assumption just weakened."
```

### Why Deltas Matter

| Trigger | Delta Says |
|---------|-----------|
| Document uploaded to project | "This document confirmed 2 assumptions, challenged 1. 2 cases affected." |
| Case investigation produces evidence | "New evidence promotes to project. Case 'Risk Analysis' also benefits." |
| User changes an assumption in a case | "Marking this confirmed updates the project. Removes a blocker in 2 cases." |
| Mode transition | "Decision mode activated. 3 options created, 4 assumptions reorganized." |
| User returns after time away | "Nothing changed. Your 3 blockers are still unresolved." |

The most powerful delta: **"This document made you LESS ready to decide."** No other tool says that.

---

## Progressive Disclosure: The Five Levels

The graph contains everything. The user sees it progressively, never all at once.

| Level | What's Visible | Entry Trigger |
|-------|---------------|---------------|
| **1. Frame** | Focus + Options (if any) | Case creation |
| **2. Ground** | + Assumptions + Evidence + Claims | Documents processed or assumptions surfaced |
| **3. Stress-test** | + Tensions + Contradictions | First contradiction detected or user challenges |
| **4. Evaluate** | + Success criteria + Scenarios | User compares options systematically |
| **5. Commit** | + Implementation intentions + Brief lock | Structural readiness conditions met |

**Hard constraint:** Never more than ~7 nodes visible at any interaction level. Cognitive overload pushes System 2 offline — a tool that shows too much makes decisions *worse*.

Deeper nodes expand on interaction. Collapsed by default. Ghost nodes visible as faded placeholders.

---

## The Commitment Moment

When structural readiness conditions are met and the user chooses an option:

1. **Prompt implementation intentions**: "When will you act? What's the trigger? Who needs to know?"
2. **Lock the deliberation graph**: Options become historical. Chosen option elevated.
3. **Visual state change**: Exploratory → committed. Color change, layout shift, eliminated options fade.
4. **Generate the brief**: Linear projection of the final state, with full provenance.
5. **Record "what would change my mind"**: Captured for future review.
6. **Produce final delta**: "Decision committed. Chosen: [Option]. Accepted risks: [Tensions]. Open monitors: [Uncertainties]."
7. **Promote learnings to project**: Confirmed assumptions, resolved tensions flow back to the project graph.

The Rubicon moment should feel consequential. Research shows clarity about commitment paradoxically reduces anxiety.

---

## How This Maps to Existing Architecture

| Concept | Current Implementation | Gap / Change |
|---------|----------------------|-------------|
| Project | Not modeled | New container model with document ownership and orientation graph |
| Case.Focus | `Case.decision_question` | Rename to `focus`, add `focus_type` field |
| Case.mode | Not modeled | Add `mode` field |
| Unified graph | Separate models (Signal, Evidence, Annotation) | Unified graph interface over existing models (v1) |
| Options | Not explicitly modeled | New model (highest priority gap) |
| Assumptions | `Signal` (type=Assumption) | Add `load_bearing`, explicit option linkage |
| Evidence | `Evidence` model | Add typed edges to assumptions/options |
| Tensions | `Annotation` (type=tension) | Elevate to first-class with resolution tracking |
| Uncertainties | `Inquiry` model | Add `criticality`, link to assumptions |
| Subgraph selector | Not modeled | New: lightweight selector for case → project node references |
| Implementation | Not modeled | New lightweight model (defer until commitment flow) |
| Provenance | Event store (67 event types) | Extend with delta narratives, patches, and project→case propagation |

### Implementation Strategy

**Option A (Pure):** Single `Node` and `Edge` table for everything. Maximum flexibility. Requires reworking existing models.

**Option B (Pragmatic — recommended for v1):** Keep existing models (Signal, Evidence, Inquiry) but expose them through a **unified graph interface**. New concepts (Project, Option, Tension, Scenario) use the unified model. Existing concepts conform to the graph interface. Migrate to Option A later if needed.

Option B preserves existing cascade logic while establishing the graph abstraction.

### The Cascade IS the State Synchronization

The existing three-way cascade (auto_reasoning → assumption_cascade → brief_grounding) already keeps the state consistent. What changes is the mental model:

**Before:** "Three systems that feed each other"
**After:** "One state that re-derives its projections when mutated"

Same code. Different conceptual frame. The frame matters for every future design decision.

---

## Design Principles (Inherited + New)

All existing principles from `DESIGN_PRINCIPLES.md` apply. This architecture adds:

### 7. State Over Artifacts

**The graph is the product. Everything else is a view.**

Never build a feature that edits an artifact directly. If the brief needs to change, the graph needs to change, and the brief re-renders. This eliminates sync problems, preserves provenance, and ensures all four lenses always agree.

### 8. Conversational Editing Over Direct Manipulation

**Users talk to an agent. The agent edits the state.**

No forms. No drag-and-drop. No manual node creation. The user thinks out loud, the agent translates to structural changes. The agent understands the graph — not just the words.

### 9. Show Shape, Not Score

**Readiness is visible in the graph's structure, not in a number.**

Sparse graphs look sparse. Thorough graphs look thorough. Ghost nodes show what's missing. Orphan assumptions glow. In non-decision modes, the same computation surfaces as coverage/gaps rather than commitment-gating.

### 10. Deltas Over Summaries

**Tell the user what changed, not what exists.**

"This document challenged a load-bearing assumption" beats "here's a summary of your document." Deltas drive attention, build trust, and make the system feel alive.

### 11. Mode Is a Lens, Not a Schema

**The graph is mode-agnostic. Mode determines rendering, governance, and agent behavior — never data structure.**

Adding a new mode requires: defining emphasis, governance rules, and agent behavior. Never a new table or migration.

### 12. Transitions Are Patches

**Every state change — including mode transitions — is a versioned, explainable, reversible patch.**

The user always understands what changed and why. The system can always roll back.

### 13. Cases Interpret, Projects Accumulate

**Documents and evidence belong to the project. Cases reference and interpret them. Knowledge flows back.**

Cases never duplicate project data. Evidence discovered in a case promotes to the project. Assumptions confirmed or refuted in a case update the project. The project gets smarter with every case. Options, scenarios, and implementation intentions stay at case level — they're episodic, not permanent knowledge.
