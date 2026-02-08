# Workflow & Value Map

The complete decision investigation workflow codified in Episteme, with feature-to-value mapping at every stage.

---

## The Journey: Chat → Confident Decision

```
USER STARTS CHATTING
  │
  ▼
┌─────────────────────────────────────────────────┐
│  SIGNAL EXTRACTION (automatic, every message)    │
│  Assumptions · Questions · Claims · Tensions     │
│  → Stored with temperature, embedding, dedup     │
└─────────────────┬───────────────────────────────┘
                  │  Structure suggestion appears
                  ▼
┌─────────────────────────────────────────────────┐
│  SCAFFOLDING (Socratic interview → structure)    │
│  LLM extracts: decision question, uncertainties, │
│  assumptions, constraints, stakeholders, stakes   │
│  → Creates Case + Inquiries + Brief + Plan       │
└─────────────────┬───────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
EXPLORING    INVESTIGATING   SYNTHESIZING    →   READY
(Phase 1)    (Phase 2)       (Phase 3)          (Phase 4)
```

---

## Phase 1: Exploring

**Goal:** See what's uncertain. Let structure emerge from conversation.

### User Experience
- Chat naturally about a decision
- Signals appear inline (highlighted assumptions, questions, claims)
- When enough structure detected, subtle prompt: "This looks like a decision worth structuring"
- Click to scaffold → LLM extracts structure from conversation

### Features Active

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| Signal extraction | Every message analyzed for assumptions, questions, claims, tensions, blind spots | Vague thinking → structured observations |
| Signal highlighting | Inline badges in chat messages | See your reasoning in real-time |
| Temperature tracking | Signals classified as hot/warm/cool | Focus attention on most uncertain areas |
| Structure detection | AI monitors for decision-worthy conversations | Gentle nudge to structure, never forced |
| Scaffold from chat | LLM extracts decision_question, uncertainties, assumptions, constraints, stakeholders | Conversation → investigation roadmap |

### What Gets Created

```
Case
├── Decision question (title)
├── Position statement (initial thesis)
├── Constraints [{type, description}]
├── Stakeholders [{name, interest, influence}]
├── Stakes level (low/medium/high)
│
├── Investigation Plan (v1)
│   ├── Phases [{title, inquiry_ids}]
│   ├── Assumptions [{text, status:untested, signal_id}]
│   └── Decision criteria [{text, is_met:false}]
│
├── Brief Sections
│   ├── Decision Frame (unlocked)
│   ├── [Inquiry Section 1] (linked to Inquiry)
│   ├── [Inquiry Section 2] (linked to Inquiry)
│   ├── Trade-offs (LOCKED)
│   └── Recommendation (LOCKED)
│
└── Inquiries (2-5, from key_uncertainties)
```

### Transformation

| Before | After |
|--------|-------|
| "I've been thinking about this..." | "I can see exactly what needs investigation" |
| Scattered thoughts across tools | Single case with linked structure |
| Unknown unknowns | Named uncertainties with investigation threads |

---

## Phase 2: Investigating

**Goal:** Test assumptions. Gather evidence. Watch grounding grow.

### User Experience
- Open inquiry → investigate with research, documents, conversations
- Assumption tracker shows status badges (untested/confirmed/challenged/refuted)
- Grounding indicators update as evidence arrives
- Annotations appear when tensions, blind spots, or evidence deserts detected
- Locked sections remind you what's not ready yet

### Features Active

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| Research agent | Multi-step investigation with checkpointing, context thinning | Consulting-grade research without manual search |
| Evidence ingestion | Universal pipeline: research findings, URLs, documents, manual input | Every evidence source feeds the same system |
| Auto-reasoning (Mechanism B) | New evidence → find similar signals → classify relationship → create M2M links | Evidence automatically connects to your assumptions |
| Assumption cascade (Mechanism A) | Evidence links → recompute status → sync plan → re-ground brief | Real-time feedback on what's validated vs. speculative |
| Brief grounding (Mechanism C) | Section status: empty → weak → moderate → strong → conflicted | Visual quality indicator for each part of your brief |
| Annotations | Tension, blind spot, evidence desert, ungrounded, well-grounded alerts | Problems surfaced before they become decision errors |
| Section locking | Trade-offs locked until any inquiry has evidence; Recommendation locked until all moderate+ | Prevents premature synthesis |
| Inquiry dependencies | blocked_by M2M with circular detection | Shows which questions must be answered first |
| Objection system | Challenges from AI, documents, or self | Adversarial reasoning strengthens conclusions |
| Confidence history | Track 20% → 45% → 65% → 72% over time | See your confidence evolution, not just current state |

### The Three-Way Cascade in Action

```
User adds research finding
  → Evidence ingestion creates records with provenance
    → Auto-reasoning finds similar assumption signal (cosine ≥ 0.82)
      → LLM classifies as SUPPORTS (confidence 0.85)
        → M2M link created: evidence.supports_signals.add(signal)
          → Django signal fires
            → Assumption cascade recomputes: untested → confirmed
              → Plan version updated (v3: assumption X now confirmed)
                → Brief grounding recalculated
                  → Section status: weak → moderate
                    → Annotation resolved: "ungrounded assumption" removed
                      → Readiness checklist item auto-completed
```

**All of this happens automatically.** The user sees: assumption badge turns green, section indicator improves, readiness item checks off.

### Unlock Gate: Trade-offs Section

Opens when: `any inquiry has evidence_count > 0`

This is deliberately low-bar — it unlocks early to encourage synthesis thinking alongside investigation.

### Transformation

| Before | After |
|--------|-------|
| "I think this is true" (gut feeling) | "3 evidence items support this, 1 contradicts" (grounded) |
| Assumptions hidden in thinking | Every assumption tracked with test status |
| Research dump gathering dust | Findings automatically linked to relevant assumptions |
| "Are we ready to decide?" (unclear) | Grounding status gives precise answer per section |

---

## Phase 3: Synthesizing

**Goal:** Integrate findings. Challenge your own conclusion. Prepare for commitment.

### User Experience
- Premortem prompt on entering this stage: "Imagine this decision failed. What's the most likely reason?"
- Decision criteria checklist with progress bar
- "What would change your mind?" resurfaced from earlier answer
- Judgment vs. evidence comparison shows where confidence exceeds evidence
- Remaining annotations highlight unresolved issues

### Features Active

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| Premortem | "Imagine failure — what caused it?" | Surfaces hidden doubts while commitment is still reversible |
| What-changed-mind resurface | Shows earlier "what would change my mind" answer | Accountability to your own epistemic commitments |
| Decision criteria | Checklist of success conditions | Systematic evaluation, no missed factors |
| Per-section confidence | 1-4 rating per brief section | Decomposed confidence reveals weak points |
| Judgment summary | Compares user ratings to evidence quality | Highlights confirmation bias |
| Companion reflection | Socratic questions informed by graph patterns | AI thinking partner challenges premature closure |

### Unlock Gate: Recommendation Section

Opens when:
- ALL inquiry sections have moderate or better grounding
- NO unresolved tensions (conflicted status)

This is deliberately high-bar — the system won't let you write a recommendation until evidence justifies it.

**Override available:** `investigation_preferences.disable_locks = True` for users who want full control.

### Transformation

| Before | After |
|--------|-------|
| "I feel ready" (emotional) | "All sections grounded, criteria checked, premortem addressed" (systematic) |
| Doubts suppressed | Premortem captures and externalizes doubt |
| Moving on without checking | Resurface mechanism forces accountability |

---

## Phase 4: Ready

**Goal:** Commit with calibrated confidence. Create shareable record.

### User Experience
- Confidence calibration: explicit 0-100 self-assessment
- "What would change my mind" captured for future reference
- Export decision memo: full brief, executive summary, or selected sections
- Event timeline shows complete decision journey

### Features Active

| Feature | What Happens | Value Delivered |
|---------|-------------|-----------------|
| Confidence calibration | User records 0-100 confidence | Explicit commitment with self-awareness |
| "What would change mind" | Captured for future review | Built-in decision review trigger |
| Brief export | Full, executive summary, or per-section | Stakeholder-ready deliverable |
| Provenance trail | Event-sourced timeline of all changes | "How did we get here?" always answerable |
| Plan version history | Every thinking evolution captured | Intellectual honesty about changed minds |

### Transformation

| Before | After |
|--------|-------|
| "I decided to go with X" (no record) | Decision memo with evidence, trade-offs, assumptions, and confidence |
| "Why did we make that choice?" (forgotten) | Full timeline from first conversation to final commitment |
| "I'm 90% sure" (uncalibrated) | Decomposed confidence: section-by-section, evidence-backed |

---

## Feature → Value → Persona Matrix

| Feature | Primary Value | Consultant | Tech Lead | Founder |
|---------|-------------|-----------|-----------|---------|
| Signal extraction | See reasoning in real-time | Medium | High | High |
| Scaffold from chat | Conversation → structure | High | High | High |
| Research agent | Automated investigation | Critical | Medium | Critical |
| Evidence ingestion | Universal evidence pipeline | High | Medium | High |
| Auto-reasoning cascade | Evidence ↔ assumption sync | High | High | High |
| Brief grounding | Quality indicator per section | Critical | High | High |
| Section locking | Prevent premature synthesis | Medium | High | Critical |
| Assumption tracking | Belief lifecycle management | High | Critical | Critical |
| Contradiction detection | Surface conflicts | Critical | High | High |
| Premortem | Externalize hidden doubts | Medium | Medium | Critical |
| Confidence calibration | Self-awareness | High | Medium | Critical |
| Plan versioning | Decision audit trail | Critical | High | Medium |
| Skill system | Domain expertise injection | Critical | Medium | High |
| Brief export | Shareable deliverable | Critical | High | Medium |
| Companion reflection | Thinking partner | Medium | Low | Critical |

---

## The Metacognitive Stack

What makes Episteme unique isn't any single feature — it's the layered metacognitive forcing functions:

1. **Signal extraction** — "Here's what you actually said" (observation)
2. **Scaffold service** — "Here's the structure of your decision" (framing)
3. **Assumption tracking** — "Here's what you believe vs. what you know" (epistemic awareness)
4. **Grounding indicators** — "Here's how well-evidenced each part is" (quality assessment)
5. **Section locking** — "You're not ready to synthesize yet" (pacing)
6. **Contradiction detection** — "These two things can't both be true" (logical consistency)
7. **Premortem** — "Imagine this failed — why?" (failure imagination)
8. **Resurface mechanism** — "You said X would change your mind — did it?" (accountability)
9. **Confidence calibration** — "How sure are you, really?" (self-assessment)
10. **Provenance trail** — "Here's how your thinking evolved" (intellectual honesty)

Each layer catches a different cognitive bias. Together, they create a decision process that's systematically more rigorous than unaided human reasoning or unstructured AI chat.
