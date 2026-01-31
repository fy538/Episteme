# Product Vision & UX Design - Episteme

## What We're Building

**Not another ChatGPT clone.**  
**A workspace for rigorous, high-stakes decision-making.**

Episteme helps you:
- Come prepared for important decisions
- Structure your thinking over time
- Consider multiple perspectives systematically
- Build evidence-based arguments
- Track trade-offs and reconcile conflicts
- Keep all research connected and useful (nothing goes to trash)

## Core Philosophy

### Different from ChatGPT

| ChatGPT | Episteme |
|---------|----------|
| Thinks FOR you | Helps YOU think better |
| One-off conversations | Persistent reasoning workspace |
| Gives answers | Structures questions |
| No accountability | Traceable reasoning |
| Research disappears | Research contributes |
| Single perspective | Multiple perspectives |

### Like Cursor + Notion + Roam

- **Like Cursor**: Background agents, inline suggestions, non-invasive
- **Like Notion**: Document editing first-class, low friction
- **Like Roam**: Bidirectional links, knowledge graph

## User Experience: Chat + Document Workspace

### The Hybrid Model

**Chat (Primary Interface)**
- Natural conversation
- Think out loud
- Ask for research
- Request debates
- Structure emerges

**Documents (Persistent Workspace)**
- Briefs you write (synthesis)
- Research AI generates
- Debates AI runs
- Critiques AI provides
- Sources you upload

**Background Agents ("Your Army")**
- Extract signals from chat
- Generate research on-demand
- Create debates when useful
- Run critiques periodically
- Suggest citations
- Detect contradictions
- Queue suggestions (non-invasive)

## Information Architecture

```
PROJECT: "Company Data Architecture"
│
└─ CASE: "PostgreSQL vs BigQuery"
   │
   ├─ CASE BRIEF (your main synthesis)
   │  └─ Aggregates all inquiries
   │     └─ Final recommendation
   │
   ├─ INQUIRIES (focused investigations)
   │  │
   │  ├─ Inquiry 1: "Is PostgreSQL fast enough?"
   │  │  ├─ Inquiry Brief (your synthesis)
   │  │  ├─ Research: "PostgreSQL Performance" (AI, 6k words)
   │  │  ├─ Research: "Latency Analysis" (AI, 4k words)
   │  │  ├─ Debate: "Speed vs Cost" (AI personas)
   │  │  └─ Critique: "Performance Assumptions" (AI devil's advocate)
   │  │
   │  ├─ Inquiry 2: "Cost comparison"
   │  │  ├─ Inquiry Brief
   │  │  └─ Research: "Cost Analysis" (AI)
   │  │
   │  └─ Inquiry 3: "Team readiness"
   │     ├─ Inquiry Brief
   │     └─ [No research yet]
   │
   ├─ SOURCE DOCUMENTS (uploaded)
   │  ├─ benchmark.pdf (chunked, searchable)
   │  └─ pricing.pdf (chunked, searchable)
   │
   ├─ CHAT THREADS
   │  └─ Main discussion (ongoing)
   │
   └─ SIGNALS (extracted from chat)
      └─ 42 floating signals
```

## Edit Friction Levels (Intentional Design)

### LOW Friction: Your Briefs
```
Case Brief, Inquiry Briefs

User Experience:
✓ Click anywhere → start typing
✓ Auto-save (no save button)
✓ Markdown shortcuts (⌘B, ⌘I, ⌘K)
✓ AI suggestions inline (Tab to accept)
✓ Full editing control

Why: This is YOUR synthesis. Refine constantly.
```

### HIGH Friction: AI Documents
```
Research, Debates, Critiques

User Experience:
✗ Can't edit AI text directly
✓ Can annotate (highlight, comment)
✓ Can cite in your brief
✓ Can accept/reject suggestions

Why: 
- Preserve AI reasoning (provenance)
- Force you to synthesize (not just tweak)
- Clear what's AI vs your thinking
```

### READ-ONLY: Uploaded Sources
```
PDFs, Papers, Documents

User Experience:
✗ Can't edit
✓ Can annotate
✓ Can search and cite chunks
✓ Can highlight and comment

Why: These are reference materials, not your work.
```

## Core Workflows

### Workflow 1: Starting a Case

```
1. Chat: "Help me decide between PostgreSQL and BigQuery"

2. Agent: "Create case 'Database Choice'?"
   [Yes, create]

3. Case created with:
   └─ Blank Case Brief (AI outline provided)

4. Agent: "What are your main concerns?"

5. You: "Performance, cost, team capability"

6. Agent: "I've identified 3 inquiries. Create with research?"
   [Yes, create + research]

7. Background:
   ├─ Create 3 inquiries
   ├─ Create 3 inquiry briefs (AI outlines)
   ├─ Generate 3 research docs (concurrent)
   └─ Extract findings → create suggestions

8. You see:
   ✓ Case structured (3 inquiries)
   ✓ Research complete (18k words)
   ✓ 47 suggestions ready
   
   [Open workspace] [Continue chat]
```

### Workflow 2: Editing Brief with AI Assistance

```
1. Open Inquiry Brief (blank AI outline)

2. Start writing:
   "Performance analysis shows..."
   
3. Inline suggestion appears:
   "[[Research: Performance#latency]]"
   [Tab to insert]

4. Citation inserted, continue writing

5. As you write, sidebar shows:
   Suggestions (3)
   • Create objection about peak capacity
   • Consider cost in your analysis
   • Cite debate for perspective
   
   [Review when ready]

6. You finish paragraph, review suggestions

7. Accept 2, reject 1

8. Brief evolves with citations, structure emerges
```

### Workflow 3: Requesting Debate

```
1. In workspace, feel need for perspectives

2. ⌘K → "Debate: Engineering vs Finance"

3. Agent generates in background (2-3 min)

4. Debate doc appears:
   ├─ Engineering position (5 arguments)
   ├─ Finance position (5 arguments)
   └─ Synthesis

5. Suggestions appear:
   □ Add Finance position to comparison
   □ Cite cost argument in brief
   □ Create objection from engineering view
   
6. You review debate, accept suggestions

7. Brief now includes both perspectives
```

### Workflow 4: Addressing Critique

```
1. Morning: Open case

2. Notification: "New critique available"
   [Review]

3. Critique shows:
   Unexamined Assumptions (4)
   • "Latency is critical" - no validation
   • "Current benchmarks apply" - different scale
   ...

4. Suggestions:
   □ Create objection for each assumption
   □ Add validation todos to brief
   
5. You approve:
   ├─ 2 objections created
   ├─ 3 todos added to brief
   └─ Brief shows what needs validation

6. You address in brief:
   "The critique raises valid concern about latency.
    Scheduling user test..."
```

## UI Components

### Chat Interface

```
┌──────────────────────────────────────────────────────────────┐
│  Chat: Database Choice                     ⌘K  •  Settings   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Context: [Case: Database Choice ▼] [Inquiry: None ▼]       │
│                                                               │
│  ─────────────────────────────────────────────────────────   │
│                                                               │
│  [Chat messages flow naturally]                              │
│  [Signals extracted silently]                                │
│  [Structure emerges in sidebar]                              │
│  [Suggestions appear contextually]                           │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Workspace View

```
┌──────────────────────────────────────────────────────────────┐
│  Database Choice                            ⌘K  •  Share     │
├──────────────────────────────────────────────────────────────┤
│                   │                              │            │
│  CASE STRUCTURE   │  EDITOR                      │  CONTEXT   │
│                   │                              │            │
│  📝 Case Brief    │  # Database Choice           │ Suggestions│
│                   │                              │            │
│  📋 Inquiries (3) │  ## Recommendation           │ □ Cite    │
│  ├─ Performance   │  After analyzing...          │   finding │
│  │   └─ 📄 4 docs │  [[Inquiry: Performance]]... │            │
│  ├─ Cost          │                              │ □ Create  │
│  │   └─ 📄 1 doc  │  [You're editing...]         │   objection│
│  └─ Team          │                              │            │
│      └─ 📄 0 docs │                              │ [Review]   │
│                   │                              │            │
│  📚 Sources (2)   │                              │ Documents  │
│  └─ 2 PDFs        │                              │ • Research │
│                   │                              │ • Debate   │
│  [+ Research]     │                              │ • Critique │
│  [+ Debate]       │                              │            │
│  [+ Critique]     │                              │ [Search]   │
│                   │                              │            │
└───────────────────┴──────────────────────────────┴────────────┘
```

### Suggestion Queue (Sidebar)

```
┌────────────────────────────────────┐
│  Suggestions (5)                   │
├────────────────────────────────────┤
│                                    │
│  From: Research (Performance)      │
│  💡 Cite latency finding           │
│     "Research shows 45ms..."       │
│     Target: Inquiry Brief          │
│     [Apply] [Skip]                 │
│                                    │
│  From: Critique                    │
│  ⚡ Create objection                │
│     "Latency importance unvalidated"│
│     Target: Performance inquiry    │
│     [Apply] [Skip]                 │
│                                    │
│  From: Debate                      │
│  👥 Add Finance position            │
│     "Choose BigQuery for cost"     │
│     Target: Case Brief             │
│     [Apply] [Skip]                 │
│                                    │
│  [Apply all (3)] [Review each]     │
│                                    │
└────────────────────────────────────┘
```

## Technical Architecture

### Flexible Document Structure

```python
# NOT rigid schemas for every doc type
# INSTEAD: Flexible JSON extraction

class CaseDocument(models.Model):
    case = FK(Case)
    inquiry = FK(Inquiry, null=True)
    document_type = CharField()
    content_markdown = TextField()
    
    # Flexible structure (varies by type)
    ai_structure = JSONField()
    # Research: {findings, sources, recommendations}
    # Debate: {personas, arguments, synthesis}
    # Critique: {assumptions, gaps, issues}
    # Custom: {whatever makes sense}
    
    # Pending suggestions
    suggestions = JSONField()


class Suggestion(models.Model):
    """Agent suggestions (like Cursor)"""
    case = FK(Case)
    source_document = FK(CaseDocument, null=True)
    
    suggestion_type = CharField()  # citation, objection, edit, etc.
    suggestion_data = JSONField()  # Flexible structure
    
    status = CharField()  # pending, approved, rejected
    confidence = FloatField()
```

### Background Agent System

```python
class CaseAgentOrchestrator:
    """Coordinates agents working on case"""
    
    agents = {
        'research': ResearchAgent(),
        'citation': CitationAgent(),
        'critic': CriticAgent(),
        'debater': DebateAgent(),
        'contradiction': ContradictionAgent(),
    }
    
    async def run_background():
        # Agents work concurrently
        # Queue suggestions
        # Non-blocking
        # User approves when ready
```

### Chat with Context

```python
class ChatMessage(models.Model):
    thread = FK(ChatThread)
    
    # NEW: Context awareness
    active_case = FK(Case, null=True)
    active_inquiry = FK(Inquiry, null=True)
    
    # Agent knows what user is working on
    # Provides relevant suggestions
    # Generates appropriate research
```

## Key Innovations

### 1. Research That Persists and Contributes
```
OLD: Research → Long report → Forgotten
NEW: Research → Structured doc → Cited in briefs → Evidence created → Contributes to decision
```

### 2. Multiple Perspectives Built-In
```
Not just your thinking
└─ Your position
└─ Counterpart positions
└─ Debates between personas
└─ Critiques challenging assumptions
```

### 3. Flexible Structure, Not Rigid Forms
```
Not: Fill out Evidence form
Instead: Write naturally, cite research, structure emerges
```

### 4. Background Agents, Not Chatbot
```
Not: Ask AI questions, get answers
Instead: Agents work in background, suggest contributions
```

### 5. Edit Friction as Design Choice
```
Low friction: Your briefs (think and type)
High friction: AI docs (annotate, cite, synthesize)
Read-only: Uploaded sources (reference)
```

## The Aha Moments

**"My research is actually contributing"**
- Generate research on PostgreSQL
- System suggests citations
- You approve
- Research findings become evidence in your brief
- Research shows "Cited 5 times, contributed 3 evidence items"

**"I can see all perspectives"**
- Your position: PostgreSQL for performance
- Tech Lead: BigQuery for cost
- Finance: BigQuery for budget
- Customer: Either, just fast
- All structured, comparable, with evidence

**"My assumptions are being challenged"**
- You assume latency is critical
- Critique agent surfaces: "No evidence for this assumption"
- Creates objection automatically
- You realize you need user testing

**"I have a complete brief, not just chat history"**
- Walk into meeting with:
  - Case Brief (polished)
  - All research (organized)
  - Multiple perspectives (analyzed)
  - Trade-offs (clear)
  - Evidence (cited)
  - Next steps (defined)

**"Everything is connected"**
- Research cites sources
- Brief cites research
- Evidence links to inquiries
- Inquiries roll up to case
- Nothing is lost

## UX Principles

### 1. Progress Must Be Visible
```
Not: Just chat scrollback
Instead: 
- Signals: 8 extracted
- Inquiries: 3 created
- Research: 5 docs (18k words)
- Briefs: 60% complete
- Suggestions: 12 pending
```

### 2. Structure Emerges, Not Imposed
```
Not: "Fill out the inquiry form"
Instead: Chat naturally → system detects inquiry → suggests creation
```

### 3. Suggestions, Not Interruptions
```
Not: Popups demanding attention
Instead: Sidebar queue, review when ready
```

### 4. High Stakes, Professional Tone
```
Not: Cards, badges, gamification
Instead: Clean text, tables, professional design
```

### 5. Everything Citable
```
Not: AI chat disappears
Instead: 
- Research is document
- Debate is document
- Critique is document
- All citable
- All persistent
```

## Implementation Priorities

### Phase 1 (Foundation) ✓ COMPLETE
- ✓ Signals from chat
- ✓ Inquiries (promoted signals)
- ✓ Documents (chunked, searchable)
- ✓ Evidence and Objections

### Phase 2 (Multi-Document System) ← NEXT
- [ ] CaseDocument model (flexible structure)
- [ ] Case Brief and Inquiry Brief (auto-created)
- [ ] AI-generated outlines for briefs
- [ ] Document citations (bidirectional links)
- [ ] Annotation system (for AI docs)
- [ ] Edit friction implementation

### Phase 3 (Background Agents)
- [ ] Research Agent (monitor + generate)
- [ ] Citation Agent (suggest inline)
- [ ] Critic Agent (periodic review)
- [ ] Debate Agent (generate perspectives)
- [ ] Contradiction Agent (detect conflicts)
- [ ] Suggestion queue system

### Phase 4 (Flexible Extraction)
- [ ] Flexible JSON schemas per doc type
- [ ] Auto-extraction from AI docs
- [ ] Suggestion generation
- [ ] User approval flow
- [ ] Contribution tracking

### Phase 5 (Positions & Synthesis)
- [ ] InquiryPosition model
- [ ] Position comparison views
- [ ] Synthesis generation
- [ ] Multi-perspective UI

### Phase 6 (Chat Context)
- [ ] Context selection (case/inquiry)
- [ ] Context-aware agent responses
- [ ] Flexible chat (not tied to structure)
- [ ] Inline actions from chat

## Technical Stack

**Backend:**
- Django (structured data)
- Celery (background tasks)
- Pinecone (vector search)
- LLM APIs (research, debates, critiques)

**Frontend:**
- Document editor (rich text/markdown)
- Chat interface
- Suggestion system
- Context selector
- Multi-view workspace

**Agents:**
- Research generation
- Debate simulation
- Critique generation
- Citation suggestions
- Contradiction detection

## Success Metrics

**User feels:**
- ✓ Progress (structure growing, not just chatting)
- ✓ Prepared (comprehensive brief, not scattered notes)
- ✓ Confident (evidence-based, multiple perspectives)
- ✓ Efficient (research persists, AI helps, nothing wasted)

**System provides:**
- ✓ Persistent research (docs don't disappear)
- ✓ Multiple perspectives (not just user's view)
- ✓ Structured reasoning (not just conversation)
- ✓ Evidence-based (citations, sources, validation)
- ✓ Non-invasive help (suggestions, not interruptions)

## What Makes This Special

### 1. Research Doesn't Go to Trash
Every research session:
- Creates persistent document
- Contributes to decision
- Citable in briefs
- Searchable later
- Builds knowledge base

### 2. Thinking Is Visible and Traceable
Your reasoning:
- Captured in signals
- Organized in inquiries
- Synthesized in briefs
- Challenged by critiques
- Evidence-supported

### 3. Multiple Perspectives Built-In
Not just you thinking:
- Your position
- Counterpart positions
- AI debates
- Devil's advocate
- Customer view

### 4. Background Help, Not Intrusive
Agents work while you think:
- Generate research
- Suggest citations
- Detect issues
- Create critiques
- Queue suggestions (you approve when ready)

### 5. Flexible Yet Structured
Not rigid forms:
- Write naturally
- Structure emerges
- Cite inline
- Connections automatic

## Next Steps: Implementation Roadmap

**Immediate (Phase 2):**
1. Implement CaseDocument model with flexible structure
2. Auto-create briefs with AI outlines
3. Citation system (markdown links → evidence)
4. Annotation system for AI docs
5. Edit friction controls

**Soon (Phase 3):**
1. Basic background agents (research, citation)
2. Suggestion queue system
3. Auto-extraction from AI docs
4. Gentle notification system

**Later (Phase 4-6):**
1. Debate and critique agents
2. Position tracking and comparison
3. Synthesis generation
4. Full multi-perspective UI

## The Complete Vision

**You open Episteme when:**
- Facing high-stakes decision
- Need to come prepared
- Multiple perspectives to consider
- Research to consolidate
- Arguments to build

**You work by:**
- Chatting to think
- Generating research
- Editing briefs
- Reviewing suggestions
- Addressing critiques

**You walk away with:**
- Complete brief
- All research organized
- Multiple perspectives considered
- Evidence cited
- Trade-offs clear
- Next steps defined
- Confidence in decision

**Not ChatGPT thinking for you.**  
**Your thinking, structured, challenged, and validated.**

---

This is the vision. Ready to build.
