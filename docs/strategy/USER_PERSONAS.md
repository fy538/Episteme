# User Personas

Three primary personas derived from Episteme's skill templates, scaffold prompts, UI copy, and codified decision workflows. Each represents a real use pattern implied by the product's architecture.

---

## Persona 1: The Strategic Consultant

> "I need consulting-grade research with triangulated evidence, not a ChatGPT summary I'd be embarrassed to show a client."

### Profile

| Attribute | Details |
|-----------|---------|
| **Role** | Management consultant, strategy analyst, advisory professional |
| **Context** | Client-facing engagements with deliverable expectations |
| **Team size** | Solo practitioner or small team (2-5) |
| **Decision stakes** | High — advice drives client investment decisions |
| **Time horizon** | Days to weeks per engagement |

### Jobs To Be Done

1. **Research synthesis** — Gather market data from IBISWorld, Gartner, SEC filings, then synthesize into a defensible thesis
2. **Evidence triangulation** — Cross-reference claims across 3+ independent sources before presenting to clients
3. **Deliverable generation** — Produce structured briefs with executive summary, key findings, contrary evidence, methodology notes
4. **Assumption auditing** — Track which claims are well-evidenced vs. which are educated guesses

### Pain Points

| Pain Point | How Episteme Addresses It |
|-----------|--------------------------|
| ChatGPT produces plausible-sounding but uncitable claims | Evidence linking traces every claim to source documents |
| Research dumps go unused — too long, no structure | Brief sections with grounding status show what's supported vs. speculative |
| Confirmation bias toward client's preferred outcome | Auto-reasoning detects contradictions; companion surfaces blind spots |
| No methodology trail for how conclusions were reached | Event sourcing provides full provenance; plan versioning shows how thinking evolved |

### Aha Moments

1. Brief grounding shows a "strong" recommendation section backed by 5 evidence items — ready for client delivery
2. Auto-reasoning catches a contradiction between two market size estimates from different sources
3. Skill system injects consulting research standards (source hierarchy, triangulation requirements) into every research loop

### Feature Mapping

| Feature | Value |
|---------|-------|
| Consulting Research Standards skill | Enforces 3+ source triangulation, methodology documentation |
| Evidence credibility ratings | Distinguish primary sources (filings) from secondary analysis |
| Brief export with provenance | Client-ready deliverable with source trail |
| Contradiction detection | Prevents embarrassing inconsistencies in client-facing work |

---

## Persona 2: The Technical Decision-Maker

> "We're debating PostgreSQL vs. BigQuery and everyone has opinions. I need to separate assumptions from evidence before we commit."

### Profile

| Attribute | Details |
|-----------|---------|
| **Role** | Engineering lead, architect, VP of Engineering, CTO |
| **Context** | Technology decisions with organizational impact |
| **Team size** | Leading a team (5-50) with diverse stakeholders |
| **Decision stakes** | Medium-high — architecture choices compound over years |
| **Time horizon** | Hours to days per decision |

### Jobs To Be Done

1. **Stakeholder alignment** — Surface the real disagreements (often hidden assumptions) before committing to a direction
2. **Build vs. buy analysis** — Evaluate trade-offs with budget constraints, timeline pressure, and technical debt
3. **Assumption testing** — Identify what the team believes vs. what's actually validated (load estimates, cost projections)
4. **Decision documentation** — Record why a choice was made so future team members understand the reasoning

### Pain Points

| Pain Point | How Episteme Addresses It |
|-----------|--------------------------|
| Team debates are opinion-driven, not evidence-driven | Inquiry system forces each uncertainty to be investigated independently |
| Architecture decisions are made and forgotten — no record of why | Event-sourced audit trail + plan versioning = permanent decision record |
| "We assumed the traffic would be X" — nobody tracks assumptions | Assumption lifecycle (untested → confirmed/challenged/refuted) with evidence linking |
| Everyone agrees too quickly (groupthink) | Premortem prompt + objection system + Socratic companion challenge premature closure |

### Aha Moments

1. Scaffold service extracts 4 key uncertainties from a messy Slack-like conversation and creates investigation threads
2. Assumption tracker shows 3 of 5 assumptions still untested — team realizes they're about to decide based on hope
3. "What would change your mind?" gets resurfaced during synthesis, forcing reassessment

### Feature Mapping

| Feature | Value |
|---------|-------|
| Scaffold from chat (3 modes) | Transforms debate transcript into structured case |
| Stakeholder tracking | Records who cares, how much influence they have |
| Assumption cascade | Real-time status propagation as evidence arrives |
| Plan versioning | Full history of how the decision framework evolved |
| Product Decision Framework skill | RICE scoring, user impact analysis, technical feasibility |

---

## Persona 3: The Solo Founder

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
| ChatGPT agrees with everything — "The Agreeable Companion" problem | Socratic companion challenges assumptions; graph analyzer surfaces ungrounded beliefs |
| No team to debate ideas with | Objection system + contradiction detection simulate adversarial reasoning |
| Research produces PDFs that go unread — "The Research Dump" problem | Evidence integrates directly into brief sections with grounding status |
| Don't know when to stop researching and decide | Stage progression (exploring → investigating → synthesizing → ready) with unlock gates |
| Can't afford bad decisions or expensive consultants | Solo Founder AI Strategy optimizes model costs; skill system encodes domain expertise |

### Aha Moments

1. Graph analyzer reveals 4 ungrounded assumptions in what felt like a well-researched position
2. Recommendation section stays locked — reveals that "gut feeling ready" and "evidence ready" are different things
3. Premortem forces articulation of failure scenario that was previously just anxiety
4. Confidence tracking shows 20% → 65% → 45% → 72% — the dip reveals evidence that almost changed the decision

### Feature Mapping

| Feature | Value |
|---------|-------|
| Socratic reflection | AI thinking partner that asks hard questions |
| Market Entry Assessment skill | Regulatory, competitive, and GTM analysis framework |
| High-Stakes Decision Quality skill | Elevated evidence thresholds, mandatory confidence updates |
| Progressive section unlocking | Prevents premature commitment |
| Cost-optimized model selection | Claude Haiku for fast tasks, Opus for deep reasoning |

---

## Cross-Persona Patterns

### What All Personas Share

1. **Distrust of unstructured AI chat** — They've all experienced ChatGPT's limitations
2. **Need for epistemic rigor** — Want to know what's evidence vs. assumption vs. inference
3. **Value transparent reasoning** — Want to trace how conclusions were reached
4. **Make decisions with consequences** — Not trivial choices; real stakes
5. **Work alone or in small teams** — Don't have large organizations to pressure-test ideas

### Persona-Specific Feature Utilization

| Feature | Consultant | Tech Lead | Founder |
|---------|-----------|-----------|---------|
| Skill system | Consulting Standards | Product Framework | Market Entry + High-Stakes |
| Research agent | Primary workflow | Occasional deep-dives | Primary workflow |
| Brief export | Client deliverable | Architecture doc | Investor memo |
| Contradiction detection | Source validation | Stakeholder alignment | Self-challenge |
| Plan versioning | Methodology trail | Decision record | Thinking evolution |
| Confidence tracking | Client calibration | Team alignment | Self-awareness |
| Premortem | Risk section | Failure modes | "What kills us" |

### Decision Types by Persona

| Persona | Example Decisions |
|---------|------------------|
| Consultant | "Should client acquire CompanyX?", "Which market to enter?", "Competitive positioning strategy" |
| Tech Lead | "PostgreSQL vs. BigQuery", "Build vs. buy auth system", "Monolith vs. microservices migration" |
| Founder | "Should we pivot to B2B?", "Which market to enter first?", "Raise now or bootstrap?", "Hire for X or Y?" |

---

## Implied Non-Personas (Who Episteme Is Not For)

| User Type | Why Not |
|-----------|---------|
| Casual chatbot user | Doesn't need structured investigation; ChatGPT is fine |
| Academic researcher | Needs citation management, peer review — different tool category |
| Large enterprise team | Needs permissions, approval workflows, SSO at scale (future feature) |
| Creative writer | Decision rigor is the opposite of creative freedom |
| Data analyst | Needs SQL, dashboards, data pipelines — not decision investigation |
