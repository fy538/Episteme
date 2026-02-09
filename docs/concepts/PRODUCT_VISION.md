# Product Vision — Episteme

What we're building, why it matters, and how it works.

**[V1 SCOPE NOTE]** V1 implements the core orientation lens only (graph visualization + conversational editing). The full vision includes Projects/Cases distinction and four cognitive modes, but v1 focuses on making assumptions and contradictions visible. Future versions add readiness tracking, investigation planning, and expanded modes.

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

### Projects and Cases: Memory and Thinking

Episteme has two levels, matching how people actually work:

**Projects** are long-lived containers for a domain of concern. "Our startup's technical direction." "Go-to-market exploration." "Fundraising prep." You dump documents into a project. The system builds an orientation map — surfacing what your documents agree on, where they fight, what they assume without evidence, and what they never address. Projects accumulate knowledge over time. They never require a decision. They're where confusion is allowed to live.

**Cases** are focused cognitive episodes within a project. "Should we pivot to B2B?" "What are the scalability risks?" "Is our pricing defensible?" Each case takes a slice of the project's knowledge, applies a specific lens, and activates the appropriate level of structure. A case about bounding risk highlights load-bearing assumptions and failure scenarios. A case about making a decision activates readiness gating — the system tracks whether you've actually tested what needs testing before you commit.

Projects give you continuity. Cases give you focus. The project gets smarter with every case — assumptions confirmed in one case improve the knowledge base for the next.

### Cognitive Modes: Not Just Decisions

The biggest insight: **decisions are just one type of thinking episode.** Before you decide, you need to orient, frame, explore, and bound risk. Episteme serves all of these.

When you dump 8 documents into a project and say "I can't see the forest for the trees," you're not deciding — you're orienting. The system shows you the landscape: claim clusters, contradictions, gaps, hidden assumptions. No decision language. No pressure to commit.

When you notice a tension ("our pitch deck says no competitors, but our own research lists three") and click "investigate this," you enter a case. The agent infers what mode you're in from how you talk. Ask "what should we do?" and it activates decision mode with full readiness tracking. Ask "what could go wrong?" and it activates risk bounding, highlighting the assumptions your plans depend on. Ask "what is the real problem here?" and it surfaces competing frames — different ways of understanding the situation that lead to different actions.

The transitions are fluid. You might orient, then frame, then decide, then bound risk, then come back to the decision. The underlying state is always the same graph — mode just changes what's emphasized, what governance is active, and how the agent challenges you.

### Conversational Editing: Talk, Don't Click

You never fill out forms or drag nodes. You talk to the agent, and the agent edits the state.

"Actually, the real risk isn't regulatory — it's that our distribution partner might not renew."

The agent creates a new assumption (untested, load-bearing), links it to the options it affects, and tells you what changed: "New load-bearing assumption. Options A and B now depend on partner renewal. No evidence exists yet." All four views of your state update: the graph shows a new amber node, the readiness diagnostic adds a blocker, the plan generates an investigation item, the brief flags a gap.

Upload a document, and the system doesn't just summarize it. It tells you **what the document changes**: which assumptions got confirmed, which got challenged, what new information appeared that nothing in your case addresses yet, and whether this document moved you closer to or *farther from* being ready. "This document made you less ready to decide" is uncomfortable. It's also the most valuable thing any tool can tell you.

---

## The Aha Moments

The core value is a cognitive transformation: from scattered to structured, from vague to grounded, from "I talked about it" to "I worked through it."

**"I uploaded my docs and the system showed me where they fight."** You thought your research told a clear story. The evidence map shows your market sizing report and your competitor analysis contradict each other on growth rate. Your pitch deck claims no competitors; your own research lists three. Your financial projections assume continued growth — and zero documents provide evidence for it. What was invisible becomes visible.

**"I can see what I'm assuming without evidence."** You've been operating on beliefs you never tested. The graph shows them as amber nodes — dashed borders, no evidence connections, driving your reasoning anyway. Four load-bearing assumptions with zero evidence. You realize you were about to bet the company on untested beliefs.

**"I know exactly what I need to resolve."** Not a vague feeling of "I should do more research." A specific list: this assumption needs evidence, this tension needs resolution, this option hasn't been stress-tested. The path from uncertain to ready is concrete.

**"This new document changed everything — and I can see how."** You uploaded a new report. Two assumptions confirmed. One challenged. A new tension surfaced. Your readiness *decreased* — you were closer to deciding yesterday. That's the system working. You would have missed this with a summary.

**"I'm ready — and I can explain why."** Not "I feel ready" but "every load-bearing assumption has evidence, tensions are resolved or accepted, and I can trace my reasoning from evidence through assumptions to the option I'm choosing." Walk into a meeting with that, and the conversation is different.

---

## How It Feels

### You open Episteme when:

- You can't see the forest for the trees
- You're circling a decision and can't commit
- You need to integrate research from scattered sources
- You want to understand what you're missing before you act
- You want confidence you can trace back to reasons — not just a feeling

### You work by:

- **Dumping** documents into a project — the system builds a map of what's known, contested, assumed, and missing
- **Talking** to an agent that understands the structure of your thinking — not just your words
- **Investigating** specific tensions and uncertainties as focused cases
- **Watching** your understanding evolve — assumptions get tested, evidence accumulates, blind spots surface
- **Deciding** when the structure supports it — or seeing exactly what's left before you can

### You walk away with:

- **Clarity**: you know what questions matter and what's been addressed
- **Structure**: your thinking is organized, persistent, and traceable
- **Grounded confidence**: you can trace every conclusion back to evidence
- **Readiness**: you know you're prepared — or you know precisely what would make you ready

---

## The Transformation

```
BEFORE                                    WITH EPISTEME
───────────────────────────────────       ───────────────────────────────────
8 docs in a folder                        A map of what they agree on, where
                                          they fight, and what they never address

"ChatGPT agreed with me"                  "I can see 4 untested assumptions
                                          driving my reasoning"

"I have a lot of research"               "My research is linked to specific
                                          assumptions — I can see what it proves
                                          and what it doesn't"

"I feel ready"                            "Every load-bearing assumption has
                                          evidence. Two tensions accepted. One
                                          risk bounded. I'm ready — and I can
                                          show why."

"Why did we make that choice?"            Full graph: evidence, assumptions,
                                          tensions, what we accepted, what
                                          changed our mind, and when
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

---

## The Meta-Principle

**We help you think. We don't think for you.**

ChatGPT thinks for you and gives you output. Episteme helps you think and gives you clarity. That's the difference — and it's the entire product.
