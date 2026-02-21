# Product Funnel

## The Core Insight: Structure + Visibility = Clarity

Episteme's value isn't the output. It's seeing the state of your thinking made visible.

When someone faces a difficult decision with scattered research:
- Multiple documents with contradictory claims
- Assumptions they've never tested
- Gaps they don't know exist
- No clear way to organize or challenge what they're thinking

**Episteme solves this** through a five-stage journey that matches natural cognitive progression: orient yourself in a domain, explore your thinking with a companion, investigate specific decisions with rigor, capture what you decided and why, and learn from the outcomes.

---

## The Five-Stage Journey

```
PROJECT (Orient)          "What's the landscape?"
    │                     Upload docs → hierarchical theme map
    ▼
CHAT (Explore)            "What should I be thinking about?"
    │                     Companion builds structure from conversation
    ▼
CASE (Investigate)        "Let me get this specific decision right."
    │                     CEAT extraction → assumption tracking → blind spots
    ▼
DECISION (Capture)        "Here's what I decided, and why."
    │                     DecisionRecord → rationale → confidence → caveats
    ▼
OUTCOME (Learn)           "How did it turn out? What did I learn?"
                          30/60/90 day check-ins → personal decision intelligence
```

Each stage adds a layer of rigor. Users can enter at any stage, but the full journey from confusion to grounded confidence follows this natural progression.

---

## Stage 1: Orient — Project Landscape

**Goal:** Overcome "I can't see the forest for the trees."

**User experience:**
- Create a project for a domain of concern ("Go-to-market exploration," "Fundraising prep")
- Upload documents (PDFs, notes, links) — no structure required
- System builds a **hierarchical theme map** using RAPTOR-style recursive clustering with LLM summaries
- The landscape view reveals: what your documents cover deeply, where they skim the surface, and what they never address

**What the hierarchy shows:**

```
Project: "Go-to-Market Exploration"
├── Market Dynamics
│   ├── Market sizing (4 documents, strong coverage)
│   ├── Competitive landscape (3 documents, some contradictions)
│   └── Customer segments (2 documents, surface-level)
├── Distribution Strategy
│   ├── Channel options (3 documents)
│   └── Partnership models (1 document, thin)
└── [GAP] Unit Economics
    └── No documents address this topic
```

**Why this hits different than AI summaries:**

| AI Summary (ChatGPT, NotebookLM) | Hierarchical Theme Map (Episteme) |
|----------------------------------|----------------------------------|
| Blends everything into smooth narrative | Shows distinct themes and their depth of coverage |
| Tells you what's in your documents | Shows what's *missing* from your documents |
| Static output you read once | Interactive structure you navigate and explore |
| No persistence | Accumulates knowledge over time — add docs next week, hierarchy updates |

**The key differentiator: detecting absence.** Claude can tell you what's *in* your documents. It's structurally bad at telling you what's *not* there, because absence isn't in the context window. Episteme detects gaps by comparing what's present against what *should* be present.

**Conversion to exploration:** The landscape view surfaces themes and gaps. Users naturally start asking questions: "What do my docs actually say about competitive threats?" → opens a chat thread within the project.

---

## Stage 2: Explore — Companion Conversation

**Goal:** Think through your situation with a partner that builds structure, not just answers.

**User experience:**
- Chat within a project context — the companion has access to all project documents
- The organic companion detects your **thinking mode** and adapts:
  - Making a decision → builds a decision tree
  - Comparing options → creates a comparison framework
  - Bounding risk → surfaces failure scenarios and assumptions
  - Just exploring → clarifying loop with probing questions
- Structure **emerges** from your conversation — you don't fill out templates

**The companion's structural awareness:**

```
User: "I think we should focus on enterprise sales first..."

Companion detects: decision mode (choosing between go-to-market strategies)
Companion builds: decision tree with three options
  Option A: Enterprise-first
  Option B: PLG/self-serve
  Option C: Hybrid approach

Each option linked to:
  - Assumptions it requires (untested)
  - Evidence from project documents
  - Tensions between options
```

**What makes this different from chat:**

| Regular AI Chat | Episteme Companion |
|----------------|-------------------|
| Agrees with you or generates generic critique | Detects your thinking mode and builds appropriate structure |
| Linear conversation, lost when you close the tab | Structure persists — come back tomorrow, it's all there |
| You have to ask for a framework | Framework emerges automatically from your words |
| No connection to your documents | Grounded in your project's document hierarchy |

**Conversion to investigation:** When the companion detects a decision point with enough complexity, it suggests creating a case: "It sounds like you're wrestling with whether to go enterprise-first. Want me to set up an investigation case for that decision?" → creates a case with pre-loaded context from the conversation.

---

## Stage 3: Investigate — Case Analysis

**Goal:** Get a specific decision right with rigor.

**User experience:**
- Case created from companion conversation (or manually)
- System applies CEAT extraction: Claims, Evidence, Assumptions, Tensions
- The **decision question** serves as a focusing lens — everything is evaluated through it
- Assumption lifecycle tracking: untested → confirmed/challenged/refuted
- Blind spot detection: what haven't you considered?
- Readiness tracking: are you actually ready to decide, or just tired of thinking about it?

**The CEAT framework in action:**

```
Case: "Should we focus on enterprise sales first?"

CLAIMS
├── "Enterprise deals average $50K ACV" (Source: competitor analysis)
├── "Sales cycle is 6-9 months" (Source: industry report)
└── "Enterprise requires SOC2 compliance" (Source: prospect feedback)

EVIDENCE
├── 3 competitor case studies showing enterprise-first success
├── 1 report showing PLG companies growing faster
└── 2 customer interviews supporting enterprise demand

ASSUMPTIONS (tracked)
├── ⚠ "We can close enterprise deals without a sales team" (UNTESTED)
├── ⚠ "Our product is enterprise-ready" (UNTESTED)
├── ✓ "Market is large enough for enterprise focus" (CONFIRMED — 3 sources)
└── ✗ "Competitors won't match our pricing" (CHALLENGED — 1 source contradicts)

TENSIONS
├── ⚡ Enterprise sales cycle (6-9 mo) vs. runway (12 mo) — timing risk
└── ⚡ PLG report says self-serve grows faster, but our docs assume enterprise
```

**Conversion to decision:** When the case reaches sufficient readiness — key assumptions tested, critical tensions acknowledged, blind spots addressed — the system prompts: "You've tested 5 of 7 assumptions. Two tensions are acknowledged. Ready to record your decision?"

---

## Stage 4: Capture — Decision Record

**Goal:** Record what you decided and why, while the reasoning is fresh.

**User experience:**
- Record a DecisionRecord: what you decided, your key reasons, confidence level (0-100), caveats
- The system links the decision to the specific assumptions you're betting on
- Set an outcome check date: 30, 60, or 90 days
- The case status moves to "decided"

**The DecisionRecord:**

```
DECISION: Focus on enterprise sales first

KEY REASONS:
1. Market is large enough (confirmed by 3 sources)
2. Enterprise ACV justifies the sales cycle investment
3. SOC2 compliance is achievable within timeline

CONFIDENCE: 65%

CAVEATS:
- Assuming we can close without a dedicated sales team (still untested)
- Timing risk: 6-9 month cycle vs. 12 month runway is tight

BETTING ON:
- "We can close enterprise deals without a sales team" (untested assumption)
- "Our product is enterprise-ready" (untested assumption)

OUTCOME CHECK: April 15, 2026
```

**Why this matters:** Most tools help you *make* decisions. Nothing captures the decision formally so you can learn from it. The DecisionRecord is the bridge between investigation and learning.

---

## Stage 5: Learn — Outcome Tracking

**Goal:** Come back later and see how it turned out. Become a better thinker over time.

**User experience:**
- System reminds you at the outcome check date
- Record what actually happened — which assumptions were right, which were wrong
- See your confidence calibration over time: "When I'm 65% confident, I'm right about 60% of the time"
- Build a personal decision journal that reveals patterns

**The outcome check:**

```
OUTCOME CHECK — April 15, 2026

ORIGINAL DECISION: Focus on enterprise sales first (65% confidence)

WHAT HAPPENED:
- ✓ Market was indeed large enough
- ✗ Could NOT close without a sales team — hired SDR in month 3
- ✗ Enterprise sales cycle was actually 9-12 months, not 6-9
- ~ Product was "mostly" enterprise-ready — needed 6 weeks of compliance work

OVERALL: Decision was directionally right, but timeline assumptions were wrong.
Adjusted confidence for similar decisions: Lower from 65% to 50% when
timing is a critical variable.
```

**Over time, patterns emerge:**
- "I'm consistently overconfident about timelines"
- "My market sizing assumptions are usually right"
- "When competitors are a factor, I underestimate their speed"

**This is the feature no competitor is building.** It transforms Episteme from a one-time investigation tool into a personal decision intelligence system.

---

## The Funnel as Retention Loop

```
Orient → "My docs cover X but miss Y — let me explore that"
  → Explore → "The companion surfaced assumptions I hadn't tested"
    → Investigate → "I can see what I'm betting on without proof"
      → Decide → "I recorded my decision and why"
        → Learn → "I was wrong about timelines — I'll weight that differently next time"
          → Next decision → "I'll use Episteme again — it knows my patterns"
```

Retention comes from **accumulated value**:
- Projects accumulate knowledge over time
- Cases build investigation history
- Decisions create a personal journal
- Outcomes reveal calibration patterns

**The system gets more valuable the longer you use it.** That's the retention loop.

---

## The Core UX Primitive: Document Delta Analysis

The most powerful interaction happens during an active investigation: the user uploads a new document and the system shows **what it changes about their decision**.

### Why "What Changed" Beats "What's In Here"

Every other tool answers: "What's in this document?"
Episteme answers: "What does this document change about your decision?"

That's the question the user actually has. Nobody uploads a Gartner report into their case about entering Japan and thinks "summarize this." They think "does this change my plan?"

### The Delta View

When a document is uploaded into an active case, the system produces a delta analysis:

- **CONFIRMS** — which assumptions just got validated, with status change (e.g., untested → confirmed)
- **CONTRADICTS** — which assumptions are now challenged, cross-referenced with other sources
- **NEW INFORMATION** — things the document raises that no existing inquiry covers
- **GAPS THAT REMAIN** — what's *still* missing even after adding this document
- **READINESS IMPACT** — did this document move you closer to or *farther from* being ready to decide?

The most powerful moment: **"This document made you LESS ready to decide. Was: 2 blockers. Now: 3 blockers."** No other tool will tell you that.

### The Delta View as Universal Output

The same delta format works for every trigger:

| Trigger | Delta View Says |
|---------|----------------|
| User uploads a document | "Here's what this document changes about your decision" |
| Research agent completes a loop | "Here's what I found and how it shifts your case" |
| User adds evidence manually | "Here's how this evidence updates your assumptions" |
| User returns after time away | "Since you were last here, nothing changed. Your 3 blockers are still unresolved." |

**The delta view is the universal answer to "what happened?"** It's the heartbeat of the product — the thing that makes every upload dramatic, every research loop consequential, and every return to the case informative.

---

## Competitive Framing

| Competitor | What They Do | What Episteme Does Differently |
|-----------|-------------|-------------------------------|
| ChatGPT / Claude project | Read docs, answer questions, summarize | Three-level architecture: orient → explore → investigate → decide → learn |
| Perplexity | Fast research with citations | Research is a pipeline stage, not the end product |
| NotebookLM | Summarize and synthesize across documents | Diagnose the landscape (contradictions, gaps, assumptions); investigate decisions; track outcomes |
| Spreadsheets/Google Docs | Manual organization | Automatic CEAT extraction + decision lifecycle |

**The one-line differentiator:** Other tools help you make decisions. Episteme helps you make decisions *and learn from them*.

---

## Kill Criteria

This strategy fails if:

- Users complete investigations but never record decisions
- Users record decisions but never return for outcome checks
- The companion's organic structure detection doesn't feel natural
- The hierarchical theme map isn't more useful than a ChatGPT summary
- Users don't see contradictions in their own research that matter to their decision

Define metrics. Measure honestly. If it's not working, the problem isn't the feature list — it's the core insight. Back up and test why.
