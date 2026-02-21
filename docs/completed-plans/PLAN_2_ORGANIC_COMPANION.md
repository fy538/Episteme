# Plan 2: Organic Companion + Agentic Chat

## Context & Strategic Decisions

This plan emerges from a series of product architecture decisions made during a deep design session. Here is the full context you need:

### The Problem We're Solving

Chat is a terrible medium for exploratory thinking. When users explore a topic they don't fully understand, the linear chat format causes:

1. **Lost context branches.** The conversation has a tree shape, but chat collapses it into a line. Dead branches (eliminated options) stay as noise.
2. **Invisible mental model mismatches.** The AI assumes context the user hasn't provided. The user reveals constraints piece by piece, causing backtracking.
3. **Lost signals.** Questions asked but not answered, assumptions made but not tested, tensions that emerge but aren't tracked — all buried in the scroll.
4. **No accumulation.** The conversation produces insights, but they evaporate. There's no artifact, no structure, nothing reusable.

A real example: A user asked Claude about Sigma's write-back feature. Over 15+ messages, they revealed constraints one by one ("we don't have dbt," "we use a read replica," "shared tables with tenant_id"). Each constraint invalidated previous AI explanations. By the end, both the user and AI had lost track of what was established, what was open, and what the actual decision was.

### The Solution: The Organic Companion

A companion that lives alongside the chat and does three things:

1. **Tracks conversation structure** — not as a transcript or summary, but as a flexible, organic sketch that fits the topic. Could be a decision tree, a checklist, a flow, a comparison table — whatever shape makes sense for what's being discussed.

2. **Feeds back into chat context** — the companion state becomes part of the AI's context, so it knows what's been established, what's open, what's been eliminated. This is the "clarifying loop." The AI stops going down dead branches.

3. **Does background work** — when the companion detects unresolved factual questions, a background agent researches them. Results surface in the companion or the conversation. The user gets clarity without leaving the chat.

### Key Design Principles

**The companion is NOT the graph.** The graph (Claims, Evidence, Assumptions, Tensions) is a case-level reasoning tool. The companion is flexible and organic. It doesn't impose a schema on the conversation. The LLM decides what structure fits.

**The companion is NOT a sidebar you have to manage.** It's ambient. It updates itself. The user can ignore it (casual users) or engage with it (power users). Progressive disclosure: minimal by default, expandable on demand.

**The companion feeds forward.** When the user opens a case, the companion state transfers. Constraints become Evidence. Open questions become untested Assumptions. The companion's organic structure crystallizes into graph nodes at transition moments — not before.

**The companion is agentic.** It doesn't just observe. It acts. It researches. It challenges assumptions. It suggests opening a case when the conversation reaches a decision shape. It knows what to do organically.

### The Three Aha Moments of Chat

- **2a: "This chat understands me."** The AI doesn't repeat mistakes, remembers constraints, asks the right follow-ups.
- **2b: "I can see my thinking."** The companion shows the shape of exploration — what's established, what's open, what's been eliminated.
- **2c: "It's doing work for me."** Open questions get researched in the background. The user didn't have to go search.
- **2d: "My conversation became something."** The chat led to a case, pre-populated with structure. Nothing was lost.

### Multiple Entry Points

The companion works from different starting points:
- **Blank chat** → structure emerges from scratch (concept exploration, brainstorming)
- **Within a project** → chat enriches understanding of existing documents, companion can reference project themes
- **Within a case** → chat refines a decision, companion tracks progress toward resolution

---

## Current Architecture (What Exists Today)

### Backend Chat System

**ChatThread model** (`backend/apps/chat/models.py`):
- `title`, `user` FK, `thread_type` (general|research|inquiry|document)
- `primary_case` FK (nullable), `project` FK (nullable)
- Signal extraction batching: `last_extraction_at`, `chars_since_extraction`, `turns_since_extraction`
- Agent routing: `last_agent_check_at`, `turns_since_agent_check`, `last_suggested_agent`
- `metadata` JSONField — flexible agent state storage

**Message model:**
- `thread` FK, `role` (user|assistant|system), `content` text
- `content_type`: text | card_signal_extraction | card_case_suggestion | card_structure_preview | ...
- `structured_content` JSONField for rich card messages
- `event_id` UUID (dual-write to event store)
- `metadata` JSONField

**ChatService** (`backend/apps/chat/services.py`):
- `create_thread()`, `create_user_message()`, `create_assistant_message()`
- `generate_assistant_response(thread_id, user_message_id)`:
  - Gets last 6 messages as context
  - Injects project summary if `thread.project_id` is set
  - Calls LLM with pydantic-ai Agent
  - Returns assistant Message
- `create_rich_message()` — creates card messages with structured data

**Chat Prompts** (`backend/apps/chat/prompts.py`):
- `get_assistant_response_prompt()` — builds prompt with conversation context + project summary
- `format_summary_for_chat()` — strips citations, caps 5 themes, ~200-400 tokens
- System prompt role: "ask clarifying questions, surface assumptions, challenge weak reasoning, suggest alternative perspectives"

### Frontend Chat System

**Chat Components** (`frontend/src/components/chat/`):
- `ChatPanel.tsx` — wrapper combining MessageList + MessageInput with streaming
- `MessageList.tsx` — dual variant (default=sidebar, full=Claude-style)
- `MessageInput.tsx` — multi-variant (hero, default, full) with mode dropdown
- `ChatModeHeader.tsx` — header showing thread info
- Card renderers in `cards/`: CaseCreationPromptCard, CasePreviewCard, InquiryResolutionPromptCard, etc.

**Streaming:**
- Backend returns SSE: response chunks, reflection, action hints, graph edits, title updates
- `useStreamingChat()` hook manages parsing + callbacks

### Existing Companion System

**CompanionPanel** (`frontend/src/components/companion/CompanionPanel.tsx`):
- Already exists as a right-side panel
- Props: `thinking`, `mode`, `position` (sidebar|bottom|hidden), `actionHints`, `status`, `sessionReceipts`, `caseState`, `rankedSections`, `pinnedSection`
- Slot system: 3 slots in sidebar mode, 2 in bottom
- Sections: ThinkingSection, StatusSection, SessionReceiptsSection, CaseStateSection
- Mode indicator dot: cyan=casual, amber=case, accent=inquiry, teal=graph

**The existing companion shows AI thinking, background task status, and case state. We are extending it to show conversation structure and agentic capabilities.**

### Key Frontend Patterns
- React Query v5.28 for data fetching
- Tailwind CSS 3.4 + Framer Motion 12.29
- `useConversationState()` hook — thread state + companion combined
- `useCompanionState()` hook — companion section ranking + pinning
- Context providers: NavigationProvider, CaseWorkspaceProvider

---

## Implementation Plan

### Phase 1: Conversation Structure Extraction (Backend)

#### 1.1 Create ConversationStructure Model

**File:** `backend/apps/chat/models.py` (add to existing)

This stores the companion's organic structure — the flexible sketch that represents the conversation's shape.

```python
class ConversationStructure(models.Model):
    """The organic companion structure for a chat thread.
    Updated by LLM as conversation progresses.
    Not a graph — flexible structure that fits the conversation topic."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='structures')
    version = models.IntegerField(default=1)  # Incremented on each update

    # The organic structure — shape is determined by LLM, not by us
    # Could be a decision tree, checklist, comparison table, concept map, etc.
    structure_type = models.CharField(max_length=30)
    # e.g.: 'decision_tree', 'checklist', 'comparison', 'concept_map',
    #        'flow', 'constraint_list', 'exploration_map', 'pros_cons'

    # The actual structure content — flexible JSON, schema depends on structure_type
    content = models.JSONField()
    # Examples:
    # decision_tree: {question, branches: [{label, detail, status, children}]}
    # checklist: {title, items: [{text, status, detail}]}
    # exploration_map: {center, areas: [{label, summary, open_questions, status}]}

    # Conversation state tracking
    established = models.JSONField(default=list)
    # List of things confirmed: ["No dbt", "PostgreSQL read replica", "Multi-tenant shared tables"]

    open_questions = models.JSONField(default=list)
    # List of unresolved questions: ["Is query performance a problem?", "Do they need Input Tables?"]

    eliminated = models.JSONField(default=list)
    # List of eliminated options/branches: ["Schema-per-tenant approach", "dbt-based pipeline"]

    # Summary for chat context injection
    context_summary = models.TextField(default='')
    # Compact text version of the structure for injecting into chat prompt

    # Metadata
    last_message_id = models.UUIDField(null=True)  # Last message processed
    metadata = models.JSONField(default=dict)  # {model, tokens, latency}
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['thread', '-version']),
        ]
```

#### 1.2 Create CompanionService

**File:** `backend/apps/chat/companion_service.py` (new)

This is the core engine. It takes a conversation, decides what structure fits, generates/updates it, and produces context for the chat prompt.

```python
class CompanionService:

    async def update_structure(
        self,
        thread_id: uuid.UUID,
        new_message_id: uuid.UUID,
    ) -> ConversationStructure:
        """Called after each user+assistant message pair.
        Reads recent conversation, updates the organic structure."""

        thread = ChatThread.objects.get(id=thread_id)
        messages = Message.objects.filter(thread=thread).order_by('created_at')
        current_structure = ConversationStructure.objects.filter(
            thread=thread
        ).order_by('-version').first()

        # Build prompt for structure update
        prompt = self._build_structure_prompt(messages, current_structure)

        # LLM call — single pass to update or create structure
        result = await self._call_llm(prompt)

        # Parse result into ConversationStructure fields
        structure = ConversationStructure.objects.create(
            thread=thread,
            version=(current_structure.version + 1) if current_structure else 1,
            structure_type=result['structure_type'],
            content=result['content'],
            established=result['established'],
            open_questions=result['open_questions'],
            eliminated=result['eliminated'],
            context_summary=result['context_summary'],
            last_message_id=new_message_id,
        )
        return structure

    def _build_structure_prompt(
        self,
        messages: QuerySet,
        current_structure: Optional[ConversationStructure],
    ) -> str:
        """Build the prompt for structure generation/update."""
        # See section 1.3 for the full prompt design

    def get_chat_context(self, thread_id: uuid.UUID) -> str:
        """Returns the context_summary for injection into chat prompt.
        This is the clarifying loop — the companion feeds back into the AI."""
        structure = ConversationStructure.objects.filter(
            thread_id=thread_id
        ).order_by('-version').first()
        if not structure:
            return ''
        return structure.context_summary

    async def detect_case_signal(
        self,
        thread_id: uuid.UUID,
    ) -> Optional[dict]:
        """Check if the conversation has reached a 'decision shape' —
        multiple options + tensions + enough constraints to scope a decision.
        Returns case suggestion data or None."""
        structure = ConversationStructure.objects.filter(
            thread_id=thread_id
        ).order_by('-version').first()
        if not structure:
            return None

        # Heuristic: suggest case when there are:
        # - 2+ established constraints
        # - 2+ open questions
        # - Structure type is decision_tree, comparison, or pros_cons
        # Then do a lightweight LLM check to formulate the decision question
        ...

    async def detect_research_needs(
        self,
        thread_id: uuid.UUID,
    ) -> list[dict]:
        """Identify factual questions that could be researched in the background.
        Returns list of {question, search_query, priority}."""
        structure = ConversationStructure.objects.filter(
            thread_id=thread_id
        ).order_by('-version').first()
        if not structure:
            return []

        # Look at open_questions for factual queries (not opinion/decision questions)
        # LLM classifies: is this researchable? what would you search for?
        ...
```

#### 1.3 Structure Generation Prompt Design

**File:** `backend/apps/chat/companion_prompts.py` (new)

This is the most critical design decision. The prompt must:
- Read the full conversation
- Decide what structure type fits (or keep the existing type)
- Generate/update the organic content
- Track established facts, open questions, eliminated options
- Produce a compact context summary for the chat prompt

```python
def build_structure_update_prompt(
    messages: list[dict],
    current_structure: Optional[dict],
    project_context: Optional[str] = None,
) -> str:
    """
    The prompt instructs the LLM to:

    1. Read the conversation and understand the topic being explored
    2. Choose a structure type that fits (or keep current if still appropriate):
       - decision_tree: when comparing options / making a choice
       - checklist: when there's a list of things to do/verify/check
       - comparison: when evaluating alternatives side by side
       - exploration_map: when exploring a broad topic area
       - flow: when understanding a process or sequence
       - constraint_list: when accumulating constraints/requirements
       - pros_cons: when weighing advantages vs disadvantages
       - concept_map: when understanding how concepts relate

    3. Generate the structure content as JSON matching the type
    4. Extract:
       - established: confirmed facts/constraints from the conversation
       - open_questions: unresolved questions (both explicit and implicit)
       - eliminated: options/approaches that have been ruled out and why
    5. Write context_summary: a compact (~200 token) text that the AI can
       use to stay on track in subsequent responses

    If updating an existing structure:
    - Preserve what hasn't changed
    - Update what the new messages affect
    - Add newly established facts
    - Resolve questions that got answered
    - Eliminate options that got ruled out
    - Change structure type if the conversation has shifted
    """
```

**Structure type schemas (examples):**

```python
STRUCTURE_SCHEMAS = {
    'decision_tree': {
        'question': str,  # The main decision
        'branches': [{
            'label': str,  # Option name
            'detail': str,  # Explanation
            'status': str,  # 'viable' | 'eliminated' | 'preferred' | 'exploring'
            'reason': str,  # Why this status (especially for eliminated)
            'children': [...]  # Sub-branches
        }]
    },
    'checklist': {
        'title': str,
        'items': [{
            'text': str,
            'status': str,  # 'pending' | 'done' | 'blocked' | 'not_applicable'
            'detail': str,
            'notes': str,
        }]
    },
    'comparison': {
        'comparing': str,  # What we're comparing
        'options': [str],  # Column headers
        'criteria': [{
            'criterion': str,
            'values': {option: str},  # Per-option assessment
            'winner': str | None,
        }]
    },
    'exploration_map': {
        'center': str,  # Main topic
        'areas': [{
            'label': str,
            'summary': str,
            'status': str,  # 'explored' | 'partially_explored' | 'unexplored'
            'open_questions': [str],
        }]
    },
}
```

#### 1.4 Wire Companion into Chat Flow

**File:** `backend/apps/chat/services.py` (modify)

After generating an assistant response, trigger companion update:

```python
async def generate_assistant_response(self, thread_id, user_message_id):
    # ... existing logic ...

    # EXISTING: Get context messages, project summary
    context = self._get_context_messages(thread, limit=6)
    project_summary_context = ...

    # NEW: Get companion context for clarifying loop
    companion_context = companion_service.get_chat_context(thread_id)

    # MODIFIED: Include companion context in prompt
    prompt = get_assistant_response_prompt(
        user_message=user_message.content,
        conversation_context=self._format_conversation_context(context),
        project_summary_context=project_summary_context,
        companion_context=companion_context,  # NEW
    )

    # ... call LLM, create assistant message ...

    # NEW: After response, update companion structure (async, non-blocking)
    # This runs in background so it doesn't slow down chat response
    schedule_async(companion_service.update_structure(thread_id, assistant_message.id))

    # NEW: Check for research needs (async, non-blocking)
    schedule_async(companion_service.detect_research_needs(thread_id))

    # NEW: Check for case signal (every N turns)
    if thread.turns_since_agent_check >= 3:
        schedule_async(companion_service.detect_case_signal(thread_id))
        thread.turns_since_agent_check = 0
        thread.save(update_fields=['turns_since_agent_check'])

    return assistant_message
```

#### 1.5 Update Chat Prompt with Companion Context

**File:** `backend/apps/chat/prompts.py` (modify)

```python
def get_assistant_response_prompt(
    user_message: str,
    conversation_context: str = '',
    project_summary_context: str = '',
    companion_context: str = '',  # NEW
) -> str:
    prompt_parts = []

    # ... existing parts ...

    # NEW: Companion context (the clarifying loop)
    if companion_context:
        prompt_parts.append(f"""
CONVERSATION STATE (tracked by companion):
{companion_context}

IMPORTANT: Use this state to guide your response:
- Do NOT suggest or explain things that have been ELIMINATED
- Do NOT ask about things that are already ESTABLISHED
- Address OPEN QUESTIONS when relevant
- Stay focused on the current exploration direction
""")

    # ... rest of prompt ...
```

### Phase 2: Background Research Agent (Backend)

#### 2.1 Create ResearchAgent

**File:** `backend/apps/chat/research_agent.py` (new)

When the companion detects factual open questions, this agent researches them in the background.

```python
class ResearchAgent:

    async def research_question(
        self,
        thread_id: uuid.UUID,
        question: str,
        search_query: str,
    ) -> ResearchResult:
        """Research a single factual question.
        Returns structured findings."""

        # 1. Search (web search, or project documents, or both)
        # 2. Synthesize findings
        # 3. Store as a ResearchResult
        # 4. Notify companion / inject into conversation

    async def research_from_project(
        self,
        thread_id: uuid.UUID,
        question: str,
        project_id: uuid.UUID,
    ) -> ResearchResult:
        """Search within project documents for an answer.
        Uses chunk embeddings for semantic search."""
        # Embed the question
        # Find most relevant chunks
        # Synthesize answer from chunks
        # Return with source citations
```

#### 2.2 Create ResearchResult Model

**File:** `backend/apps/chat/models.py` (add)

```python
class ResearchResult(models.Model):
    """Background research finding from the companion agent."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='research_results')
    question = models.TextField()  # The question being researched
    answer = models.TextField()  # Synthesized answer
    sources = models.JSONField(default=list)
    # [{type: 'web'|'project_chunk', url?, chunk_id?, title, snippet}]
    status = models.CharField(max_length=20)  # researching | complete | failed
    surfaced = models.BooleanField(default=False)  # Has it been shown to user?
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['thread', '-created_at']),
            models.Index(fields=['thread', 'status']),
        ]
```

#### 2.3 Surface Research Results

Research results can be surfaced in two ways:

1. **In the companion:** The structure updates to show resolved questions with findings
2. **In the chat:** A system message or rich card appears: "I looked into [question] and found: [answer]"

Use the existing `create_rich_message()` method with a new content_type:

```python
# New content_type for Message
'card_research_finding'

# structured_content shape:
{
    'question': 'Does Sigma support RLS with PostgreSQL?',
    'answer': 'Yes, Sigma supports PostgreSQL RLS policies...',
    'sources': [...],
    'confidence': 0.85,
}
```

### Phase 3: Chat → Case Bridge (Backend)

#### 3.1 Case Signal Detection

**File:** `backend/apps/chat/companion_service.py` (extend)

When the conversation reaches a "decision shape," the companion suggests opening a case. This integrates with the existing `CaseCreationPromptCard` system.

```python
async def detect_case_signal(self, thread_id: uuid.UUID) -> Optional[dict]:
    structure = self._get_current_structure(thread_id)
    if not structure:
        return None

    # Heuristic pre-check (avoid unnecessary LLM calls):
    has_enough_context = (
        len(structure.established) >= 2 and
        len(structure.open_questions) >= 1 and
        structure.structure_type in ('decision_tree', 'comparison', 'pros_cons', 'exploration_map')
    )

    if not has_enough_context:
        return None

    # LLM check: is there a clear decision question emerging?
    result = await self._call_llm(self._build_case_detection_prompt(structure))

    if result.get('should_suggest'):
        # Use existing CaseCreationPromptCard mechanism
        thread = ChatThread.objects.get(id=thread_id)
        await ChatService().create_rich_message(
            thread_id=thread_id,
            content_type='card_case_suggestion',
            structured_content={
                'suggested_title': result['title'],
                'decision_question': result['decision_question'],
                'ai_reason': result['reason'],
                # NEW: companion state to transfer
                'companion_state': {
                    'established': structure.established,
                    'open_questions': structure.open_questions,
                    'eliminated': structure.eliminated,
                    'structure_snapshot': structure.content,
                },
            },
            fallback_text=f"It seems like you're working toward a decision: {result['decision_question']}. Want to open a case?",
        )
        return result
    return None
```

#### 3.2 Transfer Companion State to Case

**File:** `backend/apps/cases/services.py` (modify `create_case_from_analysis`)

When a case is created from a chat with companion state, transfer:
- `established` → These become context for case-level extraction (constraints/evidence)
- `open_questions` → These inform the investigation plan
- `research_results` → These become case-scoped documents or evidence
- `structure_snapshot` → Stored in case metadata for reference

```python
async def create_case_from_analysis(self, user, analysis, thread_id, correlation_id, user_edits=None):
    # ... existing case creation logic ...

    # NEW: Transfer companion state
    companion_state = analysis.get('companion_state')
    if companion_state:
        case.metadata['companion_origin'] = companion_state
        case.save(update_fields=['metadata'])

        # Transfer research results as case documents
        research_results = ResearchResult.objects.filter(
            thread_id=thread_id,
            status='complete',
        )
        for result in research_results:
            WorkingDocumentService().create_working_document(
                case=case,
                document_type='research',
                title=f"Research: {result.question}",
                content_markdown=self._format_research_as_markdown(result),
                generated_by_ai=True,
                agent_type='research',
            )

    return case, brief, inquiries, plan
```

### Phase 4: Companion Frontend

#### 4.1 Create ConversationStructureView

**File:** `frontend/src/components/companion/ConversationStructureView.tsx` (new)

This renders the organic structure from the companion. It must handle multiple structure types.

```typescript
interface ConversationStructureViewProps {
  structure: ConversationStructure;
  isUpdating: boolean;
  onOpenCase?: (context: CompanionCaseContext) => void;
}

// Renders different visualizations based on structure_type:
// - decision_tree → nested expandable tree with status badges
// - checklist → checkbox list with status colors
// - comparison → table with criteria rows and option columns
// - exploration_map → expandable areas with status indicators
// - flow → vertical flow with arrows
// - constraint_list → grouped list of confirmed/open/eliminated items
// - pros_cons → two-column layout
// - concept_map → simple node layout (not the full graph)
```

**Sub-components by structure type:**

```
ConversationStructureView
├── DecisionTreeView (expandable branches with viable/eliminated/preferred status)
├── ChecklistView (items with status toggles)
├── ComparisonView (table layout)
├── ExplorationMapView (expandable areas)
├── FlowView (vertical steps with arrows)
├── ConstraintListView (grouped: established / open / eliminated)
├── ProsConsView (two-column)
└── ConceptMapView (simple labeled nodes with connections)
```

Each sub-component uses:
- Tailwind for layout
- Framer Motion for expand/collapse animations
- Color coding: green=established, amber=open, gray=eliminated, blue=exploring
- Compact by default, expandable for detail

#### 4.2 Create ConversationStateBar

**File:** `frontend/src/components/companion/ConversationStateBar.tsx` (new)

This is the minimal "pulse" — always visible, shows conversation state at a glance.

```typescript
interface ConversationStateBarProps {
  established: string[];
  openQuestions: string[];
  eliminated: string[];
  structureType: string;
  isResearching: boolean;  // Background research in progress
  onClick: () => void;  // Expand to full structure view
}

// Renders as a compact bar:
// ✓ 3 established · ? 2 open · ✗ 1 eliminated · 🔍 Researching...
// Click to expand into full ConversationStructureView
```

But per our discussion, raw counts like "3 established · 2 open" aren't helpful enough. The bar should show **the most important current state item**:

```
Exploring: "Should we use Sigma write-back?"
├ 3 constraints known · 2 open questions · 🔍 Researching RLS support...
```

The bar rotates through showing: the current focus (structure title/question), then key stats, then active research status.

#### 4.3 Create ResearchFindingCard

**File:** `frontend/src/components/chat/cards/ResearchFindingCard.tsx` (new)

Renders background research results inline in the chat.

```typescript
interface ResearchFindingCardProps {
  question: string;
  answer: string;
  sources: Array<{type: string; title: string; snippet: string; url?: string}>;
  confidence: number;
}

// Renders as a card with:
// 🔍 Research Finding
// Q: "Does Sigma support RLS with PostgreSQL?"
// A: "Yes, Sigma supports..."
// Sources: [links/citations]
```

#### 4.4 Extend CompanionPanel

**File:** `frontend/src/components/companion/CompanionPanel.tsx` (modify)

Add the conversation structure as a new section in the companion panel:

```typescript
// New section to add to rankedSections:
'conversation_structure'

// In the slot system, ConversationStructureView gets priority
// when it has content. ThinkingSection and StatusSection remain.

// New section component:
<ConversationStructureSection
  structure={conversationStructure}
  isUpdating={isStructureUpdating}
  researchResults={pendingResearch}
  onOpenCase={handleOpenCase}
/>
```

The companion panel's existing slot system (3 slots in sidebar mode, 2 in bottom) works well. The conversation structure section can take one or two slots depending on how much content it has.

#### 4.5 TypeScript Types

**File:** `frontend/src/lib/types/companion.ts` (extend existing)

```typescript
interface ConversationStructure {
  id: string;
  thread_id: string;
  version: number;
  structure_type: StructureType;
  content: Record<string, any>;  // Shape depends on structure_type
  established: string[];
  open_questions: string[];
  eliminated: string[];
  context_summary: string;
  updated_at: string;
}

type StructureType =
  | 'decision_tree'
  | 'checklist'
  | 'comparison'
  | 'exploration_map'
  | 'flow'
  | 'constraint_list'
  | 'pros_cons'
  | 'concept_map';

interface ResearchResult {
  id: string;
  question: string;
  answer: string;
  sources: Array<{
    type: 'web' | 'project_chunk';
    title: string;
    snippet: string;
    url?: string;
    chunk_id?: string;
  }>;
  status: 'researching' | 'complete' | 'failed';
  surfaced: boolean;
}

interface CompanionCaseContext {
  suggested_title: string;
  decision_question: string;
  established: string[];
  open_questions: string[];
  eliminated: string[];
  research_results: ResearchResult[];
  structure_snapshot: Record<string, any>;
}
```

#### 4.6 API Endpoints

**File:** `backend/apps/chat/views.py` (add endpoints)

```
GET /api/threads/{thread_id}/structure/
  → Returns current ConversationStructure (latest version)

GET /api/threads/{thread_id}/research/
  → Returns ResearchResult records for thread
  → Filter by status, surfaced

POST /api/threads/{thread_id}/research/{result_id}/acknowledge/
  → Mark research result as surfaced/acknowledged
```

**File:** `frontend/src/lib/api/chat.ts` (add methods)

```typescript
chatAPI.getConversationStructure(threadId: string): Promise<ConversationStructure | null>
chatAPI.getResearchResults(threadId: string): Promise<ResearchResult[]>
chatAPI.acknowledgeResearch(threadId: string, resultId: string): Promise<void>
```

#### 4.7 Real-Time Updates via Streaming

The companion structure updates should stream to the frontend in real-time, using the existing SSE streaming infrastructure.

**File:** `backend/apps/chat/services.py` (modify streaming)

Add new SSE event types:
```python
# During stream:
yield {'type': 'companion_structure', 'data': structure.to_dict()}
yield {'type': 'research_started', 'data': {'question': '...', 'id': '...'}}
yield {'type': 'research_complete', 'data': research_result.to_dict()}
```

**File:** `frontend/src/hooks/useStreamingChat.ts` (modify)

Handle new event types:
```typescript
case 'companion_structure':
  setConversationStructure(event.data);
  break;
case 'research_started':
  addPendingResearch(event.data);
  break;
case 'research_complete':
  resolveResearch(event.data);
  break;
```

### Phase 5: Integration Points

#### 5.1 Project Context in Companion

When chatting within a project, the companion can reference the project's hierarchical cluster themes (from Plan 1). The chat prompt includes both project summary context AND companion context.

```python
# In generate_assistant_response:
if thread.project_id:
    project_context = format_hierarchy_for_chat(thread.project_id)  # From Plan 1
    companion_context = companion_service.get_chat_context(thread_id)
    # Both are injected into the prompt
```

#### 5.2 Case Context in Companion

When chatting within a case, the companion has access to the case's decision question, graph health, and investigation plan. It can track progress toward resolution, not just general exploration.

```python
# If thread.primary_case is set:
case_context = format_case_for_companion(thread.primary_case_id)
# The companion prompt includes case context
# Structure type might default to constraint_list or decision_tree
```

---

## Key Design Decisions

### When Does the Companion Update?

After every assistant response. The update runs in the background (non-blocking) so it doesn't slow down the chat. The frontend shows the previous structure while the new one is being generated, then transitions smoothly.

For the first few messages (< 3 turns), the companion might not have enough signal to create meaningful structure. It should stay quiet until there's something worth showing. The LLM can return `null` structure if the conversation is too early or too simple.

### How Much Context Does the Structure Prompt Get?

The full conversation (all messages), plus the current structure (if updating). This is the only place where we need the full conversation — the chat prompt itself only gets the last 6 messages + companion context summary.

This means the companion effectively gives the AI "long-term memory" of the conversation, even though the chat prompt window is limited.

### How Does Background Research Trigger?

After each companion update, `detect_research_needs()` checks if any open questions are factual and researchable. It uses a lightweight LLM classification:

- "Does Sigma support RLS?" → Researchable (factual)
- "Should we use write-back?" → Not researchable (decision)
- "Is our performance actually a problem?" → Not researchable (requires user-specific data)

Research runs for web-searchable questions and for questions answerable from project documents.

### Latency Budget

- Chat response: existing latency (no change)
- Companion update: runs async after response, ~2-3s, frontend shows "updating..."
- Research: runs fully in background, can take 5-15s, results appear when ready
- Case signal detection: runs every 3 turns, ~1s, appears as card

---

## Dependencies

- **Plan 1 (Hierarchy)**: For project context in companion. Not blocking — companion works without it.
- **Plan 3 (Case Extraction)**: The companion's case bridge feeds into case creation. Plan 3 handles what happens after the case opens.

---

## Definition of Done

1. Chatting produces an organic structure in the companion (decision tree, checklist, etc.)
2. Structure updates after each assistant response (async, non-blocking)
3. Companion context feeds back into chat prompt (clarifying loop works)
4. AI demonstrably avoids repeating eliminated options and remembers established constraints
5. Background research triggers for factual open questions and surfaces results
6. Case suggestion appears when conversation reaches decision shape
7. Companion state transfers to case on creation
8. All structure types render correctly in the companion panel
9. Real-time updates via SSE streaming
10. Works from blank chat, project chat, and case chat entry points
