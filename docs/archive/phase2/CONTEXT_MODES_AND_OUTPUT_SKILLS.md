# Context Modes & Output Skills

How Episteme's chat modes adapt across contexts, and how the skill system extends to power flexible output generation beyond briefs.

---

## Strategic Direction: Expand Outputs, Not Scope

Episteme's core value is **decision investigation with epistemic rigor**. Rather than diluting this into a general-purpose AI workspace, we expand what users can *produce* from their investigation context.

The investigation process creates rich, structured context:
- **Case scope**: Decision question, stakeholders, constraints, stakes
- **Inquiry scope**: Specific uncertainties, evidence, assumptions, objections
- **Brief scope**: Synthesized sections with grounding status, citations, confidence

This context is valuable beyond briefs. A consultant needs a slide deck. A founder needs a business plan. A tech lead needs an architecture decision record. The investigation is the same — the *output* is different.

**Principle: Investigation is the engine. Outputs are the vehicles.**

---

## Part 1: Chat Context Modes

### Current Mode Architecture

Chat modes control three things: **system prompt**, **UI chrome**, and **action card types**.

```
Frontend sends: { mode, caseId?, inquiryId?, source_type?, source_id? }
                         │
                         ▼
Backend selects system prompt override
                         │
                         ▼
LLM responds with mode-appropriate behavior
                         │
                         ▼
Frontend renders mode-specific UI + action cards
```

### Mode Inventory

| Mode | Trigger | System Prompt | UI Theme | Input Placeholder |
|------|---------|---------------|----------|-------------------|
| **Casual** | Default / no case context | Generic assistant | Neutral gray | "What would you like to explore?" |
| **Case** | User enters case context | Stage-aware guidance (exploring/investigating/synthesizing/ready) | Warning orange | "What's your next question about this case?" |
| **Inquiry Focus** | User focuses on inquiry | Inquiry-specific investigation emphasis | Accent blue | "Add evidence or thoughts about this inquiry..." |
| **Scaffolding** | Case creation flow | Skill-aware Socratic interviewer | Internal (no user-facing selector) | Default |

### What Each Mode Changes

#### Casual Mode
- **Purpose**: General exploration, no decision context yet
- **Behavior**: Signal extraction active, watches for decision-worthy conversations
- **Key affordance**: Action hints suggest case creation when structure detected
- **Limitation**: No skill injection, no stage awareness

#### Case Mode
- **Purpose**: Conversation within a decision investigation
- **Behavior**: Stage-adaptive guidance changes with investigation progression
- **Stage prompts**:
  - `exploring`: "Surface assumptions, identify blind spots, suggest areas to investigate"
  - `investigating`: "Help gather evidence, challenge beliefs, update assumption statuses"
  - `synthesizing`: "Help evaluate decision criteria, weigh trade-offs, refine position"
  - `ready`: "Help finalize the decision, ensure all criteria addressed"
- **Key affordance**: Plan diff proposals, inquiry focus suggestions
- **Integration**: "Chat About" buttons on assumptions, criteria, signals in workspace

#### Inquiry Focus Mode
- **Purpose**: Deep-dive into a single uncertainty
- **Behavior**: Narrowly scoped to evidence gathering and assumption validation
- **Key affordance**: Evidence suggestion cards, inquiry resolution prompts
- **Navigation**: Breadcrumb (Case > Inquiry) with exit-to-case action

#### Scaffolding Mode
- **Purpose**: Socratic interview to extract case structure from conversation
- **Behavior**: Only mode that currently injects skill context
- **Key difference**: Signal extraction disabled (extraction happens post-scaffold)
- **Output**: Creates Case + Inquiries + Brief + Investigation Plan

### Proposed Mode Improvements

#### 1. Skill-Aware Chat in All Modes (Priority: High)

**Current gap**: Skills only inject into scaffolding and agent workflows. Case and inquiry modes use generic prompts.

**Proposed**: Extend `build_skill_context()` injection to `unified_stream` for case and inquiry modes.

```
Case mode + "Consulting Research Standards" skill active:
  → System prompt gains: methodology requirements, source hierarchy, triangulation expectations
  → Assistant responses cite evidence standards: "We need at least 2 independent sources for this market size claim"

Inquiry focus + "Legal Due Diligence" skill active:
  → System prompt gains: regulatory checklist awareness, compliance flag patterns
  → Assistant focuses: "Have we verified the jurisdictional requirements for this structure?"
```

**Impact**: Chat becomes domain-expert-aware, not just stage-aware.

#### 2. Context-Rich Placeholders and Starter Prompts (Priority: Medium)

Replace generic placeholders with action-oriented, context-aware suggestions:

| Mode | Current | Proposed |
|------|---------|----------|
| Case (exploring) | "What's your next question about this case?" | "What assumptions haven't been tested yet?" |
| Case (investigating) | Same | "What evidence would change your mind about [top untested assumption]?" |
| Case (synthesizing) | Same | "Are there trade-offs we haven't considered?" |
| Inquiry focus | "Add evidence or thoughts about this inquiry..." | "What would confirm or refute: '[inquiry.title]'?" |

**Quick-action chips** below input:
- Case mode: "Test an assumption" · "Add evidence" · "Challenge a claim" · "Generate output"
- Inquiry mode: "Add supporting evidence" · "Add contradicting evidence" · "Resolve this inquiry"

#### 3. Output Mode (Priority: High — see Part 2)

New chat mode specifically for output generation:

| Mode | Trigger | System Prompt | UI Theme |
|------|---------|---------------|----------|
| **Output** | User requests deliverable from case context | Output-skill-aware formatting agent | Green/success theme |

Detailed design in Part 2 below.

#### 4. Mode Transition Awareness (Priority: Medium)

When stage changes (e.g., exploring → investigating), the system should:
- Surface a transition message: "Your investigation has moved to the investigating stage"
- Adjust suggestions immediately
- Offer stage-appropriate next actions

#### 5. Cross-Mode Intelligence (Priority: Low)

- LLM suggests mode switches: "This question would benefit from focusing on the [inquiry name] inquiry specifically"
- Mode badges on historical messages show which mode each message was sent in
- Mode history allows re-entering previous context

---

## Part 2: Output Skills Design

### The Output Skill Pattern

Output skills extend the existing skill system to define **how investigation context gets formatted into deliverables**. They reuse the same YAML frontmatter architecture but target a new `output` agent type.

### How It Fits the Existing Skill System

The skill system already has the primitives we need:

| Existing Primitive | Current Use | Output Skill Use |
|-------------------|-------------|-----------------|
| `applies_to_agents` | Routes skill to research/critique/brief | Routes skill to `output` agent |
| `artifact_template` | Defines brief section structure | Defines output format (slides, memo, ADR) |
| `evidence_standards` | Research quality thresholds | Output citation requirements |
| `research_config.output` | Research report structure | Output section structure |
| Skill markdown body | Domain knowledge for agents | Formatting guidance, templates, examples |

**Key insight**: An output skill IS a skill. It uses the same model, same versioning, same scope system (personal/team/org/public). It just targets a different agent.

### Output Skill Schema

```yaml
---
name: "Executive Slide Deck"
description: "Generate a presentation-ready slide deck from case investigation"
domain: consulting

episteme:
  applies_to_agents:
    - output           # New agent type

  output_config:       # New top-level config section
    format: slide_deck # slide_deck | memo | executive_summary | decision_record | custom

    structure:
      - section: "Decision Overview"
        content_type: hero
        sources:       # What case data to pull
          - case.position
          - case.stakes
          - case.stage

      - section: "Key Assumptions"
        content_type: grid
        sources:
          - plan.assumptions    # With status badges

      - section: "Evidence Summary"
        content_type: narrative
        sources:
          - inquiries.evidence  # Grouped by inquiry
          - brief.grounding     # Section quality

      - section: "Trade-offs"
        content_type: comparison
        sources:
          - brief.sections[type=tradeoffs]

      - section: "Recommendation"
        content_type: hero
        sources:
          - brief.sections[type=recommendation]
          - plan.confidence

    style:
      tone: formal | conversational | analytical
      length: executive | detailed | comprehensive
      audience: leadership | technical | stakeholders
      citation_style: inline | footnotes | appendix

    constraints:
      max_slides: 12       # Format-specific limits
      require_evidence: true  # Must cite evidence, not just claims
      min_grounding: moderate  # Only include well-grounded content
---

# Executive Slide Deck Skill

When generating slide decks from investigation context:

## Narrative Arc
Build a story: Problem → Investigation → Findings → Position → Next Steps.
Each slide should have ONE key message. Supporting details go in speaker notes.

## Evidence Standards
Every claim on a slide must link to at least one evidence item.
Flag any slide content that comes from assumptions rated "untested".
Use grounding indicators as visual cues (green/yellow/red dots).

## Visual Guidelines
- Maximum 6 bullet points per slide
- Data-heavy content should use comparison tables, not paragraphs
- Include source citations in small text at slide bottom
```

### Example Output Skills Library

| Skill Name | Format | Primary Persona | What It Produces |
|-----------|--------|----------------|-----------------|
| Executive Slide Deck | `slide_deck` | Consultant | 8-12 slide presentation with evidence citations |
| Decision Memo | `memo` | Tech Lead | Structured memo: context, analysis, recommendation, risks |
| Architecture Decision Record | `decision_record` | Tech Lead | ADR format: status, context, decision, consequences |
| Business Plan Section | `custom` | Founder | Business plan chapter with market evidence integration |
| Implementation Plan | `custom` | Tech Lead | Phased plan with assumptions, risks, dependencies |
| Investor Update | `memo` | Founder | Decision summary optimized for investor communication |
| Client Deliverable | `custom` | Consultant | Full client-facing report with methodology trail |
| Risk Assessment Matrix | `custom` | All | Structured risk matrix from case assumptions + evidence |

### The Output Agent

A new agent registered in `AgentRegistry` that consumes case context and produces formatted deliverables:

#### Execution Flow

```
User triggers output (from chat or case workspace)
  │
  ▼
Load output skill (from case.active_skills where applies_to_agents includes 'output')
  │
  ▼
Query case context via BriefExportService
  ├── Brief sections (with grounding status)
  ├── Evidence items (with credibility, source, direction)
  ├── Assumptions (with lifecycle status)
  ├── Investigation plan (stage, criteria, versions)
  ├── Inquiries (with resolution status)
  └── Confidence history
  │
  ▼
Build output prompt
  ├── Base: "Generate [format] from this investigation context"
  ├── Structure: output_config.structure (section definitions + data sources)
  ├── Style: output_config.style (tone, length, audience)
  ├── Constraints: output_config.constraints (limits, quality gates)
  └── Skill body: Domain-specific formatting guidance
  │
  ▼
LLM generates structured output
  │
  ▼
Create Artifact (type: 'output', format: skill.output_config.format)
  │
  ▼
Inject into chat / render in workspace
```

#### Context Provider: Reuse BriefExportService

The existing `BriefExportService.export()` already returns a rich intermediate representation (IR):

```python
BriefExportGraph {
    case_title, case_position, stakes,
    sections: [{
        heading, content, section_type, grounding_status,
        evidence_items: [{ title, source, credibility, direction, excerpts }],
        signals: [{ text, type, temperature }]
    }],
    assumptions: [{ text, status, linked_evidence_count }],
    criteria: [{ text, is_met }],
    generation_hints: {
        estimated_slides, narrative_arc, key_takeaways
    }
}
```

The output agent doesn't need a new context system — it consumes this IR and reformats it according to the skill template.

**Design decision**: The output agent's job is **formatting**, not **querying**. Context collection is handled by `BriefExportService`. This keeps the agent focused, fast, and consistent with existing export patterns.

### Output Triggering UX

#### From Chat (Output Mode)

User enters output mode or types a natural-language request:

```
User: "Generate a slide deck for this case"
  → System detects output intent
  → Loads active output skills
  → If one skill matches: generates immediately
  → If multiple match: shows skill picker card
  → If none match: offers default output formats

User: "Write this up as an implementation plan"
  → System detects output intent with format hint
  → Matches against output skills by format/description
  → Generates with matched skill or asks for clarification
```

#### From Case Workspace (Action Button)

```
Case Workspace
  ├── [Generate Output ▼]
  │     ├── Slide Deck (active skill: "Executive Slide Deck")
  │     ├── Decision Memo (active skill: "Decision Memo")
  │     ├── Custom... (browse output skills)
  │     └── Export Brief (existing functionality)
  │
  └── Renders output in chat thread or opens preview panel
```

#### Action Card Integration

The existing action hint system can suggest outputs:

```python
# New action hint type
{
    "type": "suggest_output",
    "data": {
        "format": "slide_deck",
        "reason": "Your investigation is in the 'ready' stage with strong grounding across all sections",
        "skill_id": "uuid-of-matched-skill"
    }
}
```

Rendered as inline card: "Your investigation looks ready. Generate a slide deck?"

---

## Part 3: Mode × Skill × Scope Interaction Model

### The Full Context Stack

Every chat message passes through a layered context stack:

```
┌─────────────────────────────────────────────┐
│  Layer 4: OUTPUT SKILL (if output mode)      │
│  Format template, structure, style, audience │
├─────────────────────────────────────────────┤
│  Layer 3: DOMAIN SKILL (if case has skills)  │
│  Domain knowledge, evidence standards,       │
│  custom signal types, research methodology   │
├─────────────────────────────────────────────┤
│  Layer 2: MODE CONTEXT                       │
│  Stage guidance (exploring/investigating/    │
│  synthesizing/ready) or inquiry focus        │
├─────────────────────────────────────────────┤
│  Layer 1: BASE SYSTEM PROMPT                 │
│  "You are Episteme, a thoughtful             │
│   decision-support assistant..."             │
└─────────────────────────────────────────────┘
```

Each layer adds context without replacing the ones below it.

### Scope × Mode × Skill Matrix

| Scope | Available Modes | Skill Injection | Output Available |
|-------|----------------|-----------------|-----------------|
| **No scope** (standalone) | Casual | None | No (no investigation context) |
| **Case scope** | Case, Scaffolding, Output | Domain skills + Output skills | Yes (full case context) |
| **Inquiry scope** | Inquiry Focus | Domain skills (filtered to inquiry) | Partial (inquiry context only) |

### Example Interactions

#### Consultant investigating a market entry decision

```
1. [Casual mode] "I'm thinking about whether my client should enter the US healthcare market"
   → Signal extraction detects decision-worthy conversation
   → Action card: "Structure this as a case?"

2. [Scaffolding mode] Socratic interview extracts structure
   → Skills active: "Market Entry Assessment", "Consulting Research Standards"
   → Creates case with 4 inquiries, 6 assumptions, brief skeleton

3. [Case mode, exploring stage] "What regulatory barriers should we look at?"
   → Stage prompt: "Surface assumptions, identify blind spots"
   → Skill prompt: "For market entry, identify federal, state, and local regulatory requirements"
   → Response includes skill-specific guidance on CFIUS, FDA, state licensing

4. [Inquiry focus] Focuses on "Regulatory landscape" inquiry
   → Inquiry prompt: narrow to regulatory evidence gathering
   → Skill prompt: primary sources preferred (Federal Register, agency websites)
   → Evidence suggestions cite regulatory-specific sources

5. [Case mode, ready stage] Investigation complete
   → Action hint: "Generate a client deliverable?"
   → [Output mode] Activates "Executive Slide Deck" skill
   → Generates 10-slide deck from BriefExportGraph with evidence citations
```

#### Tech lead making an architecture decision

```
1. [Case mode, investigating] PostgreSQL vs. BigQuery case
   → Skills active: "Product Decision Framework"
   → Stage prompt: "Help gather evidence, challenge beliefs"

2. [Inquiry focus] "Cost at scale" inquiry
   → Deep investigation of pricing models
   → Evidence from vendor docs, benchmarks, case studies

3. [Case mode, ready stage] Decision reached
   → [Output mode] Activates "Architecture Decision Record" skill
   → Generates ADR: Status, Context, Decision, Consequences
   → Format follows team's ADR template conventions
```

---

## Part 4: Implementation Phases

### Phase 1: Foundation (Skill-Aware Chat)
- Extend `build_skill_context()` injection to `unified_stream` for case and inquiry modes
- Add `output` to `applies_to_agents` enum validation
- Context-aware placeholder text based on stage

### Phase 2: Output Agent
- Register `output` agent in `AgentRegistry`
- Create `generate_output_artifact` Celery workflow
- Wire `BriefExportService` as context provider
- Build 3 default output skills: Slide Deck, Decision Memo, ADR

### Phase 3: Output UX
- "Generate Output" button in case workspace
- Output skill picker card in chat
- `suggest_output` action hint type
- Output preview/edit panel

### Phase 4: Enrichment
- Quick-action chips below input (mode-specific)
- Mode transition messages on stage changes
- Starter prompts for new conversations in each mode
- Cross-mode suggestions ("Focus on this inquiry?")

### Phase 5: Skill Marketplace
- Community output skill templates
- Skill forking and customization
- Organization-shared output skill libraries
- Skill analytics (which outputs are most generated)

---

## Design Principles

1. **Investigation first, output second** — The rigor of investigation gives outputs their value. Never shortcut investigation for faster output.

2. **Skills are the configuration layer** — Output formats, domain expertise, evidence standards — all configured through the same skill system. No separate "template" concept.

3. **Context flows down, never up** — Output generation consumes investigation context (via BriefExportService IR). Outputs never modify the investigation state.

4. **Modes compose, they don't replace** — Domain skill context layers on top of mode context, which layers on top of the base prompt. Each layer enriches without overriding.

5. **Progressive disclosure in outputs too** — Just as section locking prevents premature synthesis, output generation should respect grounding status. A slide deck from a weakly-grounded investigation should say so.
