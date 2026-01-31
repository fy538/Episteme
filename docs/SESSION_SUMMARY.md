# Session Summary - Product Vision Design

## What We Accomplished

We had a comprehensive brainstorming session that evolved from technical architecture to complete product vision. Here's the journey:

### Starting Point
- Events and signals (backend only)
- No user-facing features
- Question: How do users get aha moments?

### Key Insights Developed

1. **Signals vs Documents**
   - Signals: User's thinking from chat (extract)
   - Documents: Knowledge sources (chunk, search, cite)
   - Different purposes, different treatment

2. **Inquiries as Reasoning Units**
   - Elevated signals worthy of investigation
   - Container for evidence, objections, synthesis
   - Right level for structured reasoning

3. **Edit Friction as Design**
   - LOW friction: User briefs (think and type)
   - HIGH friction: AI docs (annotate, cite, don't edit)
   - Intentional design choice, not accident

4. **Research That Persists**
   - Biggest problem: Research goes to trash
   - Solution: Research → Documents → Citations → Evidence
   - Everything contributes, nothing lost

5. **Background Agents**
   - Not chatbot, but army working for you
   - Generate research, debates, critiques
   - Suggest contributions (like Cursor)
   - Non-invasive, user approves

6. **Professional, Not Gamified**
   - Document-editing first
   - Text-focused, minimal chrome
   - Like Notion + Cursor + Roam
   - Serious tool for high-stakes decisions

## The Vision (Final)

**Product:** Workspace for rigorous decision-making

**Not:** ChatGPT that thinks for you  
**Is:** Structure that helps you think better

**Core loop:**
```
Chat (explore) 
  → Structure emerges (inquiries, briefs)
  → Agents generate (research, debates, critiques)
  → You synthesize (edit briefs, cite sources)
  → Suggestions help (auto-extract, you approve)
  → Brief complete (walk into meeting prepared)
```

**User value:**
- Come prepared to high-stakes decisions
- Multiple perspectives considered
- Evidence-based arguments
- Research organized and connected
- Critiques addressed
- Confidence in thinking

## What We Designed

### Information Architecture

```
Project
└─ Case
   ├─ Case Brief (main synthesis)
   ├─ Inquiries
   │  └─ For each:
   │     ├─ Inquiry Brief (focused synthesis)
   │     ├─ Research docs (AI-generated)
   │     ├─ Debate docs (AI personas)
   │     └─ Critique docs (AI challenges)
   ├─ Source Documents (uploaded)
   ├─ Chat Threads
   └─ Signals (from chat)
```

### Document Types & Edit Friction

1. **Case Brief** (LOW friction)
   - Main synthesis
   - User writes/edits freely
   - AI provides outline
   - Cites inquiry briefs

2. **Inquiry Briefs** (LOW friction)
   - Focused synthesis per inquiry
   - User writes/edits freely
   - AI provides outline
   - Cites research/debates/critiques

3. **Research Docs** (HIGH friction)
   - AI-generated deep research
   - Read-only with annotations
   - Citable in briefs
   - Flexible JSON structure

4. **Debate Docs** (HIGH friction)
   - AI-generated perspectives
   - Read-only with annotations
   - Multiple personas
   - Position extraction

5. **Critique Docs** (HIGH friction)
   - AI-generated challenges
   - Read-only with annotations
   - Surfaces assumptions
   - Creates objections

6. **Source Docs** (READ-ONLY)
   - Uploaded PDFs, papers
   - Chunked for search
   - Annotatable
   - Citable

### Background Agents

```
Research Agent:
└─ Monitors for research opportunities
└─ Generates comprehensive research
└─ Extracts findings → suggestions

Citation Agent:
└─ Watches user editing
└─ Suggests relevant citations inline
└─ Like Cursor autocomplete

Critic Agent:
└─ Reviews periodically (daily)
└─ Challenges assumptions
└─ Finds evidence gaps
└─ Creates critique docs

Debate Agent:
└─ Generates multi-perspective debates
└─ Simulates stakeholder views
└─ Extracts positions

Contradiction Agent:
└─ Detects conflicts in reasoning
└─ Surfaces gently
└─ Suggests resolution
```

### Suggestion System

```
AI doc generated
  ↓
Extract structure (flexible JSON)
  ↓
Generate suggestions:
├─ Citations to insert
├─ Objections to create
├─ Evidence to add
└─ Edits to propose
  ↓
Queue for user (sidebar)
  ↓
User reviews (batch or individual)
  ↓
Approve → Auto-applied
Reject → Dismissed
```

## Key Design Decisions

### 1. Flexible Structure, Not Rigid Schema
- ✅ JSON structures per doc type
- ✅ AI decides what to extract
- ❌ Not rigid Django models for every structure

### 2. Suggestions, Not Auto-Actions
- ✅ Agent suggests
- ✅ User approves
- ❌ Not automatic changes
- Like Cursor: You're in control

### 3. Chat Context, Not Rigid Flows
- ✅ Select case/inquiry context
- ✅ Switch freely
- ❌ Not locked to specific inquiry
- Chat is flexible exploration

### 4. Document-First, Not Form-First
- ✅ Write in briefs
- ✅ Structure from content
- ❌ Not forms and fields
- Like Notion: Natural editing

### 5. Professional, Not Gamified
- ✅ Text-focused
- ✅ Clean, minimal
- ❌ Not cards, badges, stars
- Serious tool for serious work

## Technical Decisions

### Backend
- Django (structured data)
- Flexible JSON (document structures)
- Celery (background agents)
- Pinecone (vector search)
- LLM APIs (research, debates, critiques)

### Frontend (Not built yet, but designed for)
- Document editor (rich text/markdown)
- Chat interface
- Context selector
- Suggestion queue
- Annotation system

### Data Models
- CaseDocument (flexible)
- Suggestion (pending actions)
- DocumentAnnotation (for AI docs)
- InquiryPosition (perspectives - future)

## What's Next

### Immediate: Phase 2A (Multi-Document Foundation)

**Build in order:**
1. CaseDocument model
2. Auto-create briefs with AI outlines
3. Citation parsing system
4. Document editor API
5. Basic UI for editing briefs

**This enables:**
- Cases with structure
- Briefs you can write
- Citations that work
- Foundation for everything else

### Soon: Phase 2B-3A (AI Docs + Suggestions)

**Then add:**
1. Research generation
2. Debate generation
3. Critique generation
4. Suggestion extraction
5. Approval flow

**This enables:**
- AI-generated research
- Suggestion system
- Contributions auto-extracted
- Real value from agents

### Later: Phase 3B-6 (Polish)

**Finally:**
1. Inline citation suggestions
2. Annotation system
3. Background orchestration
4. Chat context
5. Position tracking
6. Synthesis generation

**This makes it:**
- Smooth to use
- Professional feel
- Full-featured
- Production-ready

## Files Created This Session

**Documentation (9 files):**
1. `PRODUCT_VISION_AND_UX.md` - Complete vision
2. `IMPLEMENTATION_ROADMAP.md` - Build sequence
3. `SESSION_SUMMARY.md` - This file
4. `DOCUMENT_SYSTEM_IMPLEMENTATION.md` - Technical guide
5. `IMPLEMENTATION_SUMMARY.md` - What's built
6. `QUICKSTART_DOCUMENT_SYSTEM.md` - Setup guide
7. `COMPLETE_SYSTEM_ARCHITECTURE.md` - Full architecture
8. `INQUIRIES_IMPLEMENTATION.md` - Inquiry system
9. `INQUIRIES_ARCHITECTURE.md` - Inquiry design

**Code (24 files created/modified):**
- Models: Signal, Inquiry, Document, DocumentChunk, Evidence, Objection
- Services: Vector, Document processing, Inquiry management
- APIs: Search, Evidence, Objections
- Workflows: Document processing

## Key Takeaways

### 1. The Real Problem
Not "how to build a chatbot" but "how to help people come prepared for high-stakes decisions with research that persists and contributes."

### 2. The Solution
Hybrid system:
- Chat for thinking
- Documents for persistence
- Structure for organization
- Agents for assistance
- Suggestions for contribution

### 3. The Differentiation
**ChatGPT:** Ephemeral, thinks for you  
**Episteme:** Persistent, structures your thinking

### 4. The Design Philosophy
- Flexible structure (not rigid forms)
- Document-first (not feature-first)
- Suggestion-based (not automatic)
- Professional (not gamified)
- Non-invasive (not interrupting)

### 5. The Technical Approach
- Flexible JSON (not rigid schemas)
- Background agents (not blocking)
- Vector search (semantic retrieval)
- Multi-document (not single brief)
- Citation-based (connections)

## What We Learned

### Iteration 1: Over-Engineering
- Initially designed complex signal relationships
- Realized: Too granular, wrong abstraction level

### Iteration 2: Right Level  
- Signals are atomic (just collect)
- Inquiries are reasoning units (structure here)
- Case is meta-level (patterns across inquiries)

### Iteration 3: Document Insight
- Documents shouldn't be extracted into signals
- Keep full context, chunk and search
- Cite, don't extract

### Iteration 4: Multi-Perspective
- Not just user's thinking
- Need counterpart positions
- Debates, critiques, alternatives

### Iteration 5: Professional UX
- Not cards and gamification
- Document editing, text-first
- Like serious knowledge work tools

### Final: Complete Vision
- Chat + Documents + Agents
- Flexible structure
- Suggestions
- Professional UX
- Everything connects

## Next Session: Start Building Phase 2A

**Focus:**
1. CaseDocument model implementation
2. Brief auto-creation
3. Citation system
4. Basic editor API

**Goal:**
Get to a point where:
- Can create case with brief
- Can create inquiry with brief
- Can cite between documents
- Foundation ready for AI docs

## The Vision Is Clear

We know what we're building:
- **Not** another chat app
- **Is** a workspace for rigorous thinking

We know how it works:
- Chat + Documents + Agents
- Flexible + Structured
- Suggestions + Control

We know what makes it special:
- Research persists and contributes
- Multiple perspectives built-in
- Evidence-based reasoning
- Professional, serious tool

**Ready to build.**

---

End of session. Vision documented. Next: Implement Phase 2A.
