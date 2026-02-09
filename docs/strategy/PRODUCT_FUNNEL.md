# Product Funnel [V1 SCOPE]

## The Core Insight: Structure + Visibility = Clarity

Episteme's value isn't the output. It's seeing the state of your thinking made visible.

When someone faces a difficult decision with scattered research:
- Multiple documents with contradictory claims
- Assumptions they've never tested
- Gaps they don't know exist
- No clear way to organize or challenge what they're thinking

**V1 Episteme solves this:** extract graph structure from your documents, show contradictions, surface assumptions, let you refine through conversation.

---

## Two Levels of Entry (V1)

```
INPUT                      ENGINE                      OUTPUT
─────                      ──────                      ──────
Documents          ─┐
                    ├→  Graph Extraction +  →  Evidence Map (orientation)
Conversation       ─┘    Visualization      →  Graph (interactive)
```

Both feed the same engine: extract claims, detect contradictions, surface assumptions, build navigable structure.

| Mode | User Intent | Who Drives | Entry Point |
|------|------------|------------|-------------|
| **Dump & Discover** | "Show me what's in here" | System analyzes | Upload documents |
| **Graph Exploration** | "Help me see this clearly" | User + system collaborate | Chat to refine |

### Infrastructure Shared (V1)

- Extraction works same for docs or conversation
- Contradiction detection runs on all evidence
- Grounding indicators show proof status
- Conversational editing refines same graph

---

## Layer 1: Dump & Discover (Acquisition)

**The hook.** Zero intent, zero onboarding friction, maximum time-to-value.

### User Experience

User uploads documents (PDFs, URLs, notes, whatever). No case creation, no scaffolding questions, no decision framing required. Just: "here's my stuff, what's in it?"

Within minutes, Episteme produces an **Evidence Map** — not a summary, but a *diagnosis*:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  15 documents analyzed · 47 claims extracted
  12 supported · 8 contradicted · 27 untested
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT YOUR DOCUMENTS AGREE ON
─────────────────────────────
◼ Market size is $2.3B–2.7B (4 sources agree)
◼ Regulatory approval takes 18–24 months (3 sources)
◼ Customer acquisition cost is rising (5 sources)

WHERE YOUR DOCUMENTS FIGHT
─────────────────────────────
⚡ Growth rate: Doc A says 12%, Doc B says 34%
   → Different methodologies, different time periods
⚡ Competitive threat: Report says "low",
   but investor memo says "existential"
   → Same data, opposite conclusions

WHAT NOTHING ADDRESSES
─────────────────────────────
◻ No document discusses unit economics
◻ Retention data mentioned once, never substantiated
◻ Technical feasibility assumed everywhere,
   validated nowhere

HIDDEN ASSUMPTIONS
─────────────────────────────
⚠ "The market will grow" — claimed in 6 docs,
   evidence in 0
⚠ "Customers will switch" — 3 docs assume this,
   1 doc contradicts it
⚠ "Regulation won't change" — implicit in every
   financial projection

               [Investigate a tension →]
```

### Why This Hits Different Than AI Summaries

The evidence map is not a summary. It's the thing summaries hide:

| AI Summary (ChatGPT, NotebookLM) | Evidence Map (Episteme) |
|----------------------------------|------------------------|
| Blends contradictions into smooth narrative | Surfaces contradictions explicitly |
| Tells you what's in your documents | Tells you what's *missing* from your documents |
| Treats all claims equally | Shows which claims are supported vs. assumed |
| Output you read once | Structure you investigate further |

**The key differentiator: detecting absence.** Claude can tell you what's *in* your documents. It's structurally bad at telling you what's *not* there, because absence isn't in the context window. Episteme detects gaps by comparing what's present against what *should* be present (from domain knowledge and the skill system).

### Conversion to Investigation

The map has one CTA per tension: **"Investigate this."**

Click → creates a case with that tension as the first inquiry, all documents pre-loaded as evidence, relevant signals pre-extracted. The user lands in the investigation workflow with momentum — not a blank page, but a pre-loaded case with a specific thing they want to dig into.

**The metric that matters:** Not "did they upload" but "did they click investigate?"

### What to Build

Minimal new infrastructure required:

1. Bulk upload endpoint → existing document chunking + evidence ingestion pipeline
2. Cross-document analysis agent → orchestrates existing contradiction detection, assumption extraction, gap analysis
3. Evidence map view → new frontend component rendering the four sections
4. "Investigate" bridge → one-click case creation pre-loaded from map findings

---

## Layer 2: Graph Exploration (Core V1 Product)

**The clarification.** User and system collaborate to see thinking made visible and refine it through conversation.

The workflow:
```
Upload Docs → Extract Graph → Visualize Structure → Converse to Refine
```

The key insight: **Structure itself is the value.** Users don't just want summaries; they want to see what contradicts, what's assumed, what's missing. Then they want to talk about it naturally.

### What Makes Graph Exploration Different From Chat

Chat gives you a conversation. Graph exploration gives you:

- **Persistence** — structure stays. Come back tomorrow, it's all there
- **Visibility** — see assumptions, evidence, contradictions as distinct entities
- **Interactivity** — explore the graph, not just read prose
- **Precision** — "contradiction detected between claim A and claim B" vs. "some disagreement"
- **Natural refinement** — talk naturally; system updates the graph in place

### The Behavior Change Test (V1)

Users come to Episteme because they have scattered research and can't see the forest. Success = they see the structure, understand what they're betting on, and can articulate next steps.

(Later: do they make better decisions? That's a post-v1 question.)

---

## [FUTURE SCOPE] Layer 3: Decision Agent (Post-V1)

**Future vision.** Autonomous agent governed by the same epistemic principles proven through v1 human usage.

**Not for v1.** Build only after proving the graph model and contradiction detection are genuinely valuable in human hands.

When it ships: The agent will inherit the same governance framework (assumption tracking, contradiction detection, evidence grounding) that made human investigation more rigorous. Users won't just get a report — they'll get a report with visible reasoning and explicit gaps.

---

## The Core UX Primitive: Document Delta Analysis

The evidence map (Dump & Discover) shows the landscape of a cold document set. But the more powerful interaction happens *during* an active investigation: the user uploads a new document and the system shows **what it changes about their decision**.

### Why "What Changed" Beats "What's In Here"

Every other tool answers: "What's in this document?"
Episteme answers: "What does this document change about your decision?"

That's the question the user actually has. Nobody uploads a Gartner report into their case about entering Japan and thinks "summarize this." They think "does this change my plan?"

### The Delta View

When a document is uploaded into an active case, the system produces a delta analysis:

- **CONFIRMS** — which assumptions just got validated, with status change (e.g., untested → confirmed) and brief grounding impact
- **CONTRADICTS** — which assumptions are now challenged, cross-referenced with other documents that also conflict, with brief sections moving to "conflicted"
- **NEW INFORMATION** — things the document raises that no existing inquiry covers, with a one-click "create inquiry" action
- **GAPS THAT REMAIN** — what's *still* missing even after adding this document, making absence more conspicuous with each upload
- **BRIEF STATUS AFTER** — the punchline: did this document move you closer to or *farther from* being ready to decide?

The most powerful moment: **"This document made you LESS ready to decide. Was: 2 blockers. Now: 3 blockers."** No other tool will tell you that.

### How It Works Under the Hood

The existing cascade architecture does exactly what it was designed to do:

```
Document uploaded
  → Evidence ingestion (chunks, embeddings, claim extraction)
    → Auto-reasoning (match claims to existing signals/assumptions)
      → Assumption cascade (status recomputation)
        → Brief grounding (section status recalculation)
          → Delta capture (diff before vs. after)
            → Render delta view
```

Almost everything here already exists. The only new piece is the **delta capture** — snapshotting case state before upload and diffing against state after the cascade completes. Roughly 200 lines of code on top of 3,000 lines of existing infrastructure.

### The Delta View as Universal Output

The same delta format works for every trigger:

| Trigger | Delta View Says |
|---------|----------------|
| User uploads a document | "Here's what this document changes about your decision" |
| Research agent completes a loop | "Here's what I found and how it shifts your case" |
| User adds evidence manually | "Here's how this evidence updates your assumptions" |
| Decision agent returns results | "Here's what I investigated and the current state of your decision" |
| User returns after time away | "Since you were last here, nothing changed. Your 3 blockers are still unresolved." |

**The delta view is the universal answer to "what happened?"** It's the heartbeat of the product — the thing that makes every upload dramatic, every research loop consequential, and every return to the case informative.

### Why This Is the Killer Feature

- **Makes every upload a plot twist.** Your assumption might get confirmed. Your core thesis might get challenged. A blind spot you didn't know existed might surface. That's *exciting*.
- **Makes the investigation feel alive.** The case reacts to new information — grounding bars move, assumption badges change color, lock status updates.
- **Makes progress and regress visible.** The system tells you when you moved backward. That's uncomfortable. That's valuable.
- **Creates the "analyst" feeling.** A great analyst reads new information against everything they already know and says "this changes X, confirms Y, raises Z." That's exactly what the delta view does.
- **Is the best marketing artifact.** A screenshot of "This document made you LESS ready to decide" is more compelling than any positioning statement.

---

## The Funnel as Retention Loop [V1]

```
Dump & Discover → "This contradiction is interesting, let me explore"
  → Graph Exploration → "I can see my thinking made visible"
    → Conversational Refinement → "I understand what I'm betting on"
      → Next question/document → "I'll use this again"
```

Retention comes from the fundamental value: **structure + visibility**. If the graph is useful, users return with new questions and documents. The system accumulates understanding over time.

---

## Competitive Framing [V1]

| Competitor | What They Do | What Episteme Does Differently |
|-----------|-------------|-------------------------------|
| ChatGPT / Claude project | Read docs, answer questions, summarize | Show where docs *fight*, what's *missing*, what's *assumed* |
| Perplexity | Fast research with citations | We structure what you have; we don't search |
| NotebookLM | Summarize and chat | We diagnose the landscape (contradictions, gaps); you navigate it |
| Spreadsheets/Google Docs | Manual organization | Automatic contradiction detection + graph structure |

**The one-line differentiator:** Other tools summarize your documents. Episteme shows you where they contradict.

---

## V1 Implementation Roadmap

### V1: Dump & Discover + Graph Exploration
- **Goal:** Validate that structure + visibility is valuable
- **Metric:** Do users upload docs? Do they explore the graph? Do they come back?
- **Minimal scope:** Evidence map, graph visualization, conversational refinement

### V1.1: Delta View
- Add "what changed" indicator when new docs uploaded
- Show impact on assumption status, contradiction markers

### Post-V1: Add Readiness + Governance
- Evidence sufficiency gates
- Confidence tracking
- Investigation planning

---

## Kill Criteria (V1)

This strategy fails if:

- Users upload docs, see the graph, and never return
- The graph isn't more useful than a summary
- Conversational refinement doesn't improve understanding
- Users don't see contradictions in their own research that matter to their decision

Define metrics. Measure honestly. If it's not working, the problem isn't the feature list — it's the core insight. Back up and test why.
