# Product Vision — Episteme

What we're building, why it matters, and how it works.

---

## The Problem: AI Chat Fails High-Stakes Thinking

You face a difficult decision. You open ChatGPT. An hour later, you've had a pleasant conversation and feel... okay? Maybe?

This is the failure mode of AI chat today:

**The Agreeable Companion.** You talk through a problem for 30 minutes. The AI validates your thinking, offers encouraging responses, and you leave feeling confident. But you've just had your existing beliefs reflected back at you. The blind spots you walked in with? Still there.

**The On-Demand Critic.** You realize the chat is too agreeable, so you ask it to critique your proposal. It generates an equally compelling counter-argument. Now you're more confused than when you started. How do you weigh these perspectives? Which concerns are real? The AI doesn't know either.

**The Research Dump.** You ask for deep research. ChatGPT produces a 6-page PDF report. It looks impressive. You read it once, maybe skim it again, and then it sits in your downloads folder forever. Did it actually change your decision? Did it address what *you* specifically needed to resolve?

**The RAG Black Box.** You upload your documents. The AI pulls chunks, generates responses. But you have no way to evaluate: What did it actually consider? What did it miss? Where is the reasoning strong vs. weak? When sources conflict, who's right?

**The common thread: these tools give you *output* without giving you *clarity*.** You get answers without understanding. Research without integration. Critique without structure. And at the end, you still don't know: *Am I ready? What am I missing? Can I trust this reasoning?*

---

## The Insight: Structure Enables Confidence

The problem isn't that AI is unhelpful. It's that **chat is the wrong interface for rigorous thinking.**

Chat is linear. Thinking is structured. Chat disappears. Sensemaking needs persistence. Chat gives answers. You need to understand *what questions matter*.

The solution is structure — not imposed on you (fill out this form), but structure that *emerges* from your thinking and makes your reasoning *visible*.

When you can see what's known vs. assumed, where sources agree vs. fight, what's been investigated vs. ignored, and what's still uncertain — then you can evaluate whether you're actually ready, or whether you're just tired of thinking about it.

**Structure transforms vague confidence into grounded confidence.**

---

## What We're Building

Episteme is where you go to make sense of things that matter.

Not another ChatGPT wrapper. Not a research tool that dumps PDFs. A system that helps you *think through* complex situations with structure, evidence, and grounded confidence — whether you're making a decision, bounding risk, exploring possibilities, or just trying to understand what's going on.

### The Core Idea

You talk to an agent that understands the *shape* of your thinking — not just your words.

When you say "I think the market will grow 20%," the agent doesn't just acknowledge the claim. It creates a structural object: an untested assumption. It links that assumption to the options it affects. It watches for evidence that supports or contradicts it. If you upload a report three days later that says growth is 8%, the system tells you what that *changes* — which assumptions just weakened, which options are affected, whether you're more or less ready than before.

One state. Always visible. Always updated. Every conversation, every document, every piece of evidence modifies the same underlying structure — and you can see the impact immediately.

### Three Levels of Thinking

Episteme has three levels, matching the natural cognitive progression from confusion to clarity:

```
PROJECT (Orientation)     "What's the landscape?"
    │
    ▼
CHAT (Exploration)        "What should I be thinking about?"
    │
    ▼
CASE (Investigation)      "Let me get this specific decision right."
    │
    ▼
DECISION (Capture)        "Here's what I decided, and why."
    │
    ▼
OUTCOME (Learning)        "How did it turn out? What did I learn?"
```

**Projects** are long-lived containers for a domain of concern. "Our startup's technical direction." "Go-to-market exploration." "Fundraising prep." You dump documents into a project. The system builds an orientation map — a hierarchical clustering of themes and topics that reveals what your documents cover, where they agree, and what they never address. Projects accumulate knowledge over time. They never require a decision. They're where confusion is allowed to live.

**Chat** is where exploration happens. An organic companion agent helps you think through your situation — not by agreeing with everything, but by actively building structure from your conversation. The companion detects when you're making a decision vs. comparing options vs. bounding risk, and adapts its behavior accordingly. It builds decision trees, checklists, comparison frameworks — whatever structure fits your thinking mode. When your conversation reaches a natural investigation point, the companion suggests creating a case.

**Cases** are focused investigation workspaces within a project. "Should we pivot to B2B?" "What are the scalability risks?" "Is our pricing defensible?" Each case takes a slice of the project's knowledge, applies a specific decision question as a lens, and activates full investigation structure: assumption tracking, evidence mapping, blind spot detection, and readiness gating. A case about bounding risk highlights load-bearing assumptions and failure scenarios. A case about making a decision tracks whether you've actually tested what needs testing before you commit.

Projects give you continuity. Chat gives you exploration. Cases give you rigor. The project gets smarter with every case — assumptions confirmed in one case improve the knowledge base for the next.

### The Investigation Framework

Inside a case, the system uses a structured reasoning framework called CEAT — Claims, Evidence, Assumptions, and Tensions — to extract and organize the landscape of your decision:

- **Claims**: What's being asserted, by whom, based on what
- **Evidence**: Facts and data points that ground or challenge claims
- **Assumptions**: Beliefs you're betting on without proof (tracked lifecycle: untested → confirmed/challenged/refuted)
- **Tensions**: Where claims, evidence, or assumptions contradict each other

This isn't a static extraction. The CEAT graph evolves as you investigate: new evidence shifts assumption status, resolved tensions change the readiness picture, blind spots get filled. The system actively detects what you haven't tested and what you might be missing.

### Decision Capture: Closing the Loop

When your investigation reaches the "ready" stage — assumptions tested, evidence gathered, tensions acknowledged — Episteme doesn't just let you walk away. It asks you to **record your decision**: what you decided, why, how confident you are, and what could go wrong.

This creates a **DecisionRecord** — a formal artifact that captures your rationale at the moment of decision. More importantly, it lets you set an **outcome check date**: "Come back in 30/60/90 days and see how this played out."

Over time, this creates a personal decision journal. You accumulate a track record:
- "I tend to be overconfident about market timing"
- "My assumptions about competitor response are usually wrong"
- "When I feel 60% confident, I'm usually right"

**This is the feature no competitor is building.** Most tools help you *make* decisions. Nothing helps you *learn from* them. Decision capture transforms Episteme from a one-time investigation tool into a **personal decision intelligence system**.

### Conversational Editing: Talk, Don't Click

You never fill out forms or drag nodes. You talk to the agent, and the agent edits the state.

"Actually, the real risk isn't regulatory — it's that our distribution partner might not renew."

The agent creates a new assumption (untested, load-bearing), links it to the options it affects, and tells you what changed. All views of your state update: the graph shows a new amber node, the readiness diagnostic adds a blocker, the plan generates an investigation item, the brief flags a gap.

Upload a document, and the system doesn't just summarize it. It tells you **what the document changes**: which assumptions got confirmed, which got challenged, what new information appeared that nothing in your case addresses yet, and whether this document moved you closer to or *farther from* being ready. "This document made you less ready to decide" is uncomfortable. It's also the most valuable thing any tool can tell you.

---

## The Aha Moments

The core value is a cognitive transformation: from scattered to structured, from vague to grounded, from "I talked about it" to "I worked through it."

**"I uploaded my docs and the system showed me the landscape."** Not a summary — a hierarchical map of themes and topics. You see immediately what your documents cover deeply, where they skim the surface, and what they never address.

**"The companion noticed I was making a decision, not just exploring."** You were chatting casually, and the agent built a decision tree from your reasoning. It surfaced three options you hadn't explicitly compared. You didn't fill out a template — the structure emerged from your words.

**"I can see what I'm assuming without evidence."** You've been operating on beliefs you never tested. The CEAT graph shows them as tracked assumptions — four load-bearing beliefs with zero evidence. You realize you were about to bet the company on untested beliefs.

**"The case told me I wasn't ready."** You felt done. The system showed two critical assumptions still untested, one unresolved tension, and a blind spot in your analysis. You weren't ready — you were just tired of thinking about it.

**"I recorded my decision and checked back 60 days later."** Your assumption about competitor response was wrong. The outcome note says "Competitor moved faster than expected — need to adjust timeline." Next time you face a similar decision, you'll weight that risk differently.

---

## How It Feels

### You open Episteme when:

- You can't see the forest for the trees
- You're circling a decision and can't commit
- You need to integrate research from scattered sources
- You want to understand what you're missing before you act
- You want confidence you can trace back to reasons — not just a feeling

### You work by:

- **Dumping** documents into a project — the system builds a hierarchical theme map
- **Chatting** with a companion that builds structure from your thinking — decision trees, checklists, comparison frameworks
- **Investigating** specific decisions as cases with tracked assumptions, evidence, and tensions
- **Watching** your understanding evolve — assumptions get tested, evidence accumulates, blind spots surface
- **Deciding** when the structure supports it — and recording *why* so you can learn from it

### You walk away with:

- **Clarity**: you know what questions matter and what's been addressed
- **Structure**: your thinking is organized, persistent, and traceable
- **Grounded confidence**: you can trace every conclusion back to evidence
- **Readiness**: you know you're prepared — or you know precisely what would make you ready
- **Learning**: over time, you build a personal track record of decision quality

---

## The Transformation

```
BEFORE                                    WITH EPISTEME
───────────────────────────────────       ───────────────────────────────────
8 docs in a folder                        A hierarchical theme map showing
                                          what they cover and what they miss

"ChatGPT agreed with me"                  A companion that built a decision
                                          tree from my reasoning and surfaced
                                          assumptions I hadn't tested

"I have a lot of research"               Research linked to specific
                                          assumptions — I can see what it
                                          proves and what it doesn't

"I feel ready"                            Every load-bearing assumption has
                                          evidence. Two tensions accepted. One
                                          risk bounded. I'm ready — and I can
                                          show why.

"Why did we make that choice?"            Full decision record: rationale,
                                          confidence, caveats, which
                                          assumptions were validated, and
                                          outcome notes from 30/60/90 days
                                          later
```

---

## Design Principles

**Structure over output.** We don't give you answers. We give you a map of what you need to address.

**Visible reasoning.** If you can't see it, you can't trust it. Every claim links to evidence. Every tension is surfaced.

**Grounded confidence, not false confidence.** We never make you feel more certain than you should be.

**Emergence over imposition.** Structure emerges from your thinking. We don't make you fill out forms.

**Deltas over summaries.** We tell you what changed — not just what exists. Every document upload, every research loop, every conversation produces a delta showing its impact.

**State over artifacts.** The graph is the product. Briefs, plans, and readiness are projections of that state — always consistent, always current.

**Conversational editing.** You talk to the agent. The agent edits the state. No forms. No direct manipulation. The agent understands the graph — not just the words.

**Decision accountability.** Record what you decided and why. Check back later. Learn from the results. Become a better thinker over time.

---

## The Meta-Principle

**We help you think. We don't think for you.**

ChatGPT thinks for you and gives you output. Episteme helps you think and gives you clarity. That's the difference — and it's the entire product.

---

## Implementation Status

The product is built in phases. Each plan implements a layer of the architecture:

### Foundation (Implemented)
- **Plan 1**: Hierarchical document clustering — RAPTOR-style recursive clustering with LLM summaries, project landscape view
- **Plan 2**: Organic companion — structure-aware agentic chat with decision trees, checklists, comparison frameworks, clarifying loop
- **Plan 3**: Case extraction — CEAT graph extraction using decision question as lens, blind spot analysis, assumption tracking

### Feature Polish (Designed, not yet implemented)
- **Plan 4**: RAG citations — source-grounded responses with numbered citation markers
- **Plan 5**: Case graph visualization — interactive CEAT graph with ReactFlow
- **Plan 6**: Hierarchy refresh + change detection — theme evolution tracking across rebuilds

### Product Completeness (Designed, not yet implemented)
- **Plan 7**: Project discovery + onboarding — project list page, first-run experience, NewProjectModal
- **Plan 8**: Case creation preview + companion bridge — editable CasePreviewCard, QuickCaseModal for manual creation
- **Plan 9**: Decision capture + outcome tracking — DecisionRecord model, outcome journal, check-in reminders
