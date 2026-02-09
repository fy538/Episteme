# User Personas

## [V1 SCOPE] Primary Persona: The Solo Founder

**Launch focus.** V1 targets solo founders making high-stakes decisions with limited resources and no team to challenge assumptions.

---

## The Solo Founder

> "I'm making a bet that could sink my company. I don't have a team to pressure-test my thinking. I need a rigorous thinking partner, not a yes-machine."

### Profile

| Attribute | Details |
|-----------|---------|
| **Role** | Solo founder, early-stage CEO, independent operator |
| **Context** | High-stakes decisions with limited resources and no team to challenge assumptions |
| **Team size** | Solo (1) or tiny founding team (2-3) |
| **Decision stakes** | Existential — wrong call can mean company failure |
| **Time horizon** | Days to weeks, but decision impact spans months/years |

### Jobs To Be Done

1. **Rigorous self-challenge** — Overcome the isolation problem where nobody pushes back on your ideas
2. **Market entry analysis** — Evaluate regulatory landscape, competitive dynamics, go-to-market strategy with limited budget
3. **Cost-optimized research** — Get consulting-quality analysis without consulting-scale spend
4. **Confidence calibration** — Know when you're truly ready to commit vs. when you're just tired of deliberating

### Pain Points

| Pain Point | How Episteme Addresses It |
|-----------|--------------------------|
| ChatGPT agrees with everything — "The Agreeable Companion" problem | Contradiction detection surfaces where documents fight; graph shows ungrounded assumptions |
| No team to debate ideas with | Conversational editing where you can challenge assumptions; system surfaces what's missing |
| Research produces scattered documents that never get integrated | Evidence map shows what docs agree on, where they conflict, what they assume without proof |
| Don't know when to stop researching and decide | Explicit readiness indicator: which load-bearing assumptions are grounded, which aren't |
| Can't afford expensive research or consultants | Dump & Discover entry point requires no expertise; conversational interface is natural |

### Aha Moments

1. Evidence map reveals 4 ungrounded assumptions in what felt like a well-researched position
2. Upload a new document — system shows it *contradicts* your earlier thinking; you'd have missed this with a summary
3. Structured graph shows exactly which assumptions are blocking your decision vs. which are resolved
4. Conversational editing: talk through a concern, agent refines the assumption map in real-time

### Feature Mapping [V1 SCOPE]

| Feature | Value |
|---------|-------|
| Dump & Discover | Zero-friction entry; see agreement/contradiction/gaps at a glance |
| Graph visualization | See structure of your thinking: assumptions, evidence, contradictions |
| Contradiction detection | System surfaces where documents or assumptions fight each other |
| Assumption extraction & tracking | Track what you believe vs. what you've proven |
| Conversational editing | Talk to the agent; it refines the graph without forms |
| Delta view on document upload | "This document changes X about your decision" — not just a summary |

---

## Expansion Personas (Post-V1)

After v1 validation with founders, Episteme expands to serve consultants and technical leaders. These personas are not implemented in v1 but inform roadmap direction.

---

#### When Consultant Persona Comes (Post-V1)

> "I need consulting-grade research with triangulated evidence, not a ChatGPT summary I'd be embarrassed to show a client."

**Key differentiation:** Output flexibility — briefs, decks, memos, all derived from the same investigation engine. Not for v1.

---

### Persona B: The Technical Decision-Maker

#### When Tech Lead Persona Comes (Post-V1)

> "We're debating PostgreSQL vs. BigQuery and everyone has opinions. I need to separate assumptions from evidence before we commit."

**Key differentiation:** Team-oriented assumptions, stakeholder tracking, decision record persistence. Foundation laid in v1 (graph structure, contradiction detection), but team features post-v1.

---

## Cross-Persona Patterns (V1 Focused)

### What Solo Founder (V1) Persona Needs

1. **No team to pressure-test ideas** — Must surface blind spots autonomously
2. **Unstructured thinking as input** — Can't require pre-structured forms or expertise
3. **Quick iteration** — Founder moves fast; tool must keep up
4. **Evidence grounding** — Can't afford to bet on untested assumptions
5. **Visible assumptions** — Needs to know what's actually proven vs. what's hoped

### V1 Feature Utilization (Solo Founder Only)

| Feature | Value to Founder |
|---------|-----------------|
| Dump & Discover | Zero friction entry; see landscape immediately |
| Graph visualization | Mental model made visible; can spot gaps |
| Contradiction detection | System catches what you'd miss alone |
| Assumption extraction | See what you're betting on without proof |
| Conversational editing | No forms; natural language interface |
| Delta view | New document? See exactly what changed |

### Decision Types (Solo Founder, V1)

| Example Decisions |
|---|
| "Should we pivot to B2B?" |
| "Which market to enter first?" |
| "Raise now or bootstrap?" |
| "Is this pivot-or-die or optional optimization?" |
| "What would actually falsify this assumption?" |

---

## Implied Non-Personas (Who Episteme V1 Is Not For)

| User Type | Why Not (V1) |
|-----------|---------|
| Casual chatbot user | Doesn't need structured investigation; ChatGPT is fine |
| Academic researcher | Needs citation management, peer review — different tool category |
| Large enterprise team | Needs multi-player, permissions, SSO — post-v1 features |
| Creative writer | Decision rigor is the opposite of creative freedom |
| Data analyst | Needs SQL, dashboards, data pipelines — not decision investigation |
