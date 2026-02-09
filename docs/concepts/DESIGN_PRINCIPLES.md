# Episteme Design Principles

These principles guide every design decision. When stuck, debating features, or unsure how to present something — come back here.

These aren't generic ("be user-friendly"). They're opinionated. They reflect what makes Episteme different and help with hard tradeoffs.

**[V1 SCOPE]** V1 fully implements principles 1-6. Principles 7-8 (Readiness, Deltas) are foundation for post-v1 features but guide current architectural choices.

---

## 1. Structure Over Output

**We don't give you answers. We give you a graph of what you need to address.**

A summary is output. A graph with nodes (assumptions, evidence, claims), edges (relationships), and contradiction markers — that's structure.

Output feels productive but often isn't. Structure enables understanding.

**This principle helps us decide:**
- Should we generate more content or better visualize what exists? → Visualize.
- Should we show a summary or show the connections? → Show the connections.
- Should this feature produce something or clarify something? → Clarify.

---

## 2. Visible Reasoning

**If you can't see it, you can't trust it.**

Every claim links to evidence. Every tension is surfaced, not hidden. Every conclusion can be traced back to its source.

Hidden reasoning creates false confidence. Visible reasoning creates grounded confidence.

**This principle helps us decide:**
- Should we blend sources into a smooth summary or show where they conflict? → Show conflict.
- Should we explain how we reached a conclusion? → Always.
- Should we simplify by hiding complexity? → Only if the complexity isn't decision-relevant.

---

## 3. Grounded Confidence, Not False Confidence

**We never make you feel more certain than you should be.**

We show you what's addressed and what's missing. Readiness is measurable, not a vague feeling. Blind spots are surfaced, not papered over.

An agreeable AI creates false confidence. We create grounded confidence — confidence you can defend because you can trace it.

**This principle helps us decide:**
- Should we reassure the user or challenge them? → Challenge when appropriate.
- Should we show "90% complete" or "2 tensions unresolved"? → The specific gaps.
- Should we validate the user's thinking or surface what they missed? → Surface what they missed.

---

## 4. Emergence Over Imposition

**Structure emerges from your thinking — we don't force you to fill out forms.**

Chat naturally → inquiries surface → evidence links → structure crystallizes.

Imposed structure feels like bureaucracy. Emergent structure feels like clarity.

**This principle helps us decide:**
- Should we require structure upfront or let it develop? → Let it develop.
- Should we ask users to categorize or should we suggest categories? → Suggest.
- Should this be a form or a conversation? → Conversation first, structure emerges.

---

## 5. Integration Over Accumulation

**Research that doesn't connect to your graph is waste.**

Every document, every source, every piece of research should become nodes in the graph — extracting claims, linking to assumptions, showing contradictions. We don't let things pile up.

Accumulation feels productive. Integration actually is.

**This principle helps us decide:**
- Should we let users dump documents freely or encourage extraction? → Extract into graph.
- Should evidence exist standalone or connect to assumptions? → Connect with edges.
- Should we show "5 documents uploaded" or "3 contradictions detected"? → Show impact.

---

## 6. Conversational Editing Over Direct Manipulation

**You don't click and drag nodes. You talk naturally, and the graph updates.**

Conversation is how humans think. Forms and UI manipulation feel like bureaucracy. When you say "Actually, the risk is lower than I thought," the agent understands that affects your assumptions and updates the graph in place.

**This principle helps us decide:**
- Should users edit nodes directly or talk about changes? → Talk about changes.
- Should we show a form or a conversation? → Conversation first, structure emerges.
- Should chat be separate from the graph or an interface to it? → Conversation edits the graph.

---

## 7. State Over Artifacts [V1 FOUNDATION]

**The graph is the product. Everything else is a view of it.**

A brief is an artifact — read once, then archived. A graph is state — persistent, queryable, updatable. When you add a document or refine an assumption, the graph updates, and all views (brief, readiness indicator, plan) reflect the change automatically.

Artifacts can get out of sync with reality. State can't.

**This principle helps us decide:**
- Should we build a separate "export" system or derive outputs from the graph? → Derive from graph.
- What's the source of truth — the document or the structure? → The structure.
- When something changes, do we update the brief or the graph? → Always the graph; brief updates automatically.

**In V1:** The graph is fully implemented. Outputs (briefs, plans, readiness) are future views of it.

---

## 8. Deltas Over Summaries [V1 FOUNDATION]

**Show what changed, not just what exists.**

When you upload a document, the system doesn't summarize it. It compares the graph before/after and tells you: "This contradicts assumption X. That confirms assumption Y. Here's what new you learned that nothing addressed."

Deltas are how you know progress is real.

**This principle helps us decide:**
- Should we summarize the document or show its impact? → Show impact.
- What's the metric that matters? → Did this change anything about your thinking?
- How do users know they're making progress? → See the delta.

**In V1:** Foundation laid (cascade architecture supports this). Full delta view comes post-v1.

---

## Using These Principles

### When designing a feature, ask:

1. Does this create **structure** (a graph) or just output?
2. Is the reasoning **visible** as nodes and edges?
3. Does this create **grounded confidence** or false confidence?
4. Does structure **emerge** from conversation or is it imposed?
5. Does this **integrate** into the graph or just accumulate?
6. Is this **conversational** or do users have to click/drag?
7. Does this change the **graph** or just an artifact?
8. Does this show **what changed** or just what exists?

### When debating a decision:

Reference the principle by name. "I think we should show contradictions as visual edges on the graph — that's *Visible Reasoning* and *State Over Artifacts*." Creates shared vocabulary and faster decisions.

### When the principles conflict:

They shouldn't often, but when they do:
- **State Over Artifacts** usually wins — graph is truth
- **Structure Over Output** is foundational — if it doesn't create structure, question it
- **Visible Reasoning** is non-negotiable — if you're hiding something, it's wrong

---

## What These Principles Are Not

- They're not UI patterns (those come later)
- They're not feature specs (those reference these)
- They're not negotiable per-feature (they apply everywhere)

They're the DNA of how Episteme feels and works.

---

## The Meta-Principle

**We help you think, not think for you.**

Every principle above serves this. Structure helps you think. Visible reasoning helps you evaluate. Grounded confidence means *your* confidence, not ours. Emergence respects your process. Integration makes your research useful. Micro + macro gives you the right tool for the moment.

ChatGPT thinks for you. Episteme helps you think.

That's the difference.
