# Plan 4: Chat Quality — RAG-Grounded Responses + Source Citations

## Goal
When the AI references project documents in chat, users should see **which sources were used** and be able to **click through to the source material**. This is the #1 trust differentiator for a reasoning product.

---

## Architecture Overview

```
User sends message
        ↓
retrieve_document_context()  ← currently returns plain text
        ↓                       CHANGE: return structured RetrievalResult
Inject into LLM prompt with citation instructions
        ↓
LLM responds with [1], [2] markers
        ↓
Stream response + NEW source_chunks SSE event
        ↓
Frontend renders citations as interactive badges
        ↓
Save source_chunks on Message for reload
```

---

## Current State

| Component | File | Status |
|-----------|------|--------|
| RAG retrieval | `backend/apps/chat/retrieval.py` | Returns plain text string, no chunk tracking |
| Prompt injection | `backend/apps/intelligence/prompts.py:261` | Says "cite when using" but no format spec |
| SSE streaming | `backend/apps/chat/views.py:746-782` | 10+ event types, no source tracking |
| Message model | `backend/apps/chat/models.py:257-300` | `metadata` JSONField, no source_chunks |
| Message rendering | `frontend/src/components/chat/MessageList.tsx` | Streamdown + remark-gfm markdown |
| Citation precedent | `frontend/src/components/workspace/project/CitationPopover.tsx` | Exists for graph nodes, reusable |
| Graph Node model | `backend/apps/graph/models.py:204-208` | Has `source_chunks` M2M — pattern to follow |

---

## Implementation Steps

### Step 1: Extend Message Model with Source Tracking

**File: `backend/apps/chat/models.py`**

Add M2M relationship to DocumentChunk on the Message model (mirrors the pattern from Node model):

```python
class Message(UUIDModel, TimestampedModel):
    # ... existing fields ...

    # Source tracking for RAG-grounded responses
    source_chunks = models.ManyToManyField(
        'projects.DocumentChunk',
        blank=True,
        related_name='cited_in_messages',
        help_text="Document chunks used as RAG context for this response"
    )
```

Create migration: `backend/apps/chat/migrations/XXXX_message_source_chunks.py`

This is a M2M field so it creates a join table, no changes to the Message table itself.

---

### Step 2: Make Retrieval Return Structured Data

**File: `backend/apps/chat/retrieval.py`**

Currently `retrieve_document_context()` returns a plain string. Change it to return both the formatted text (for the LLM prompt) and the structured chunk metadata (for citation tracking).

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class RetrievalChunk:
    """A retrieved chunk with metadata for citation tracking."""
    chunk_id: str
    document_id: str
    document_title: str
    chunk_index: int
    text: str           # Full chunk text
    excerpt: str         # First 200 chars for UI display
    similarity: float    # Cosine similarity score

@dataclass
class RetrievalResult:
    """Structured retrieval result with both LLM context and chunk metadata."""
    context_text: str                        # Formatted for LLM prompt (existing format)
    chunks: List[RetrievalChunk] = field(default_factory=list)

    @property
    def has_sources(self) -> bool:
        return len(self.chunks) > 0
```

Modify the existing `retrieve_document_context()` function:

1. Keep the existing similarity_search logic unchanged
2. Build `context_text` with numbered citations: `[1] [Doc: "Title" chunk 0]\n{text}`
3. Collect chunk metadata into `RetrievalChunk` objects
4. Return `RetrievalResult(context_text=..., chunks=[...])`

**Numbered citation format in prompt:**
```
[1] [Doc: "Performance Benchmark" chunk 0]
PostgreSQL handles 50,000 writes per second on standard hardware...

[2] [Doc: "Architecture Review" chunk 3]
Horizontal sharding introduces consistency challenges...
```

The numbers [1], [2] correspond to array indices in `result.chunks`, so the LLM can reference them and the frontend can map them back.

---

### Step 3: Update LLM Prompt with Citation Instructions

**File: `backend/apps/intelligence/prompts.py`**

In `build_unified_user_prompt()`, update the retrieval context section:

```python
if retrieval_context:
    parts.append(f"""The following passages are from the user's project documents. When you use information from these sources, cite them using the bracketed number (e.g. [1], [2]).

{retrieval_context}

Citation rules:
- Use [N] inline when referencing a source, e.g. "PostgreSQL handles 50k writes/sec [1]"
- Only cite when you're actually using information from that source
- You can cite multiple sources in one statement [1][3]
- If you're not using any source, don't cite anything
- Don't fabricate citations — only use numbers that appear above""")
```

This gives the LLM a clear, unambiguous format. The `[N]` markers are easy to parse on the frontend.

---

### Step 4: Stream Source Chunks via SSE

**File: `backend/apps/chat/views.py`** (in the `unified_stream` async generator)

After the response completes and before the final `done` event, emit a new `source_chunks` event:

```python
# After response streaming completes, before 'done' event:
if retrieval_result and retrieval_result.has_sources:
    source_payload = {
        'chunks': [
            {
                'index': i,  # Matches [N] in response text
                'chunk_id': chunk.chunk_id,
                'document_id': chunk.document_id,
                'document_title': chunk.document_title,
                'chunk_index': chunk.chunk_index,
                'excerpt': chunk.excerpt,
                'similarity': round(chunk.similarity, 3),
            }
            for i, chunk in enumerate(retrieval_result.chunks)
        ]
    }
    yield f"event: source_chunks\ndata: {json.dumps(source_payload)}\n\n"
```

The `index` field is the key — it maps `[1]` in the response to `chunks[0]` (1-indexed in text, 0-indexed in array).

**Also update the retrieval call site** (around line 581-593):

```python
# Before (plain string):
retrieval_context = await sync_to_async(retrieve_document_context)(query=content, ...)

# After (structured):
retrieval_result = await sync_to_async(retrieve_document_context)(query=content, ...)
retrieval_context = retrieval_result.context_text if retrieval_result else ''
```

---

### Step 5: Save Source Chunks on Message

**File: `backend/apps/intelligence/handlers.py`** (in `handle_completion()`)

After creating the assistant message, link the retrieved chunks:

```python
# After creating assistant_message:
if retrieval_result and retrieval_result.has_sources:
    chunk_ids = [chunk.chunk_id for chunk in retrieval_result.chunks]
    from apps.projects.models import DocumentChunk
    assistant_message.source_chunks.set(
        DocumentChunk.objects.filter(id__in=chunk_ids)
    )
```

This persists the source association so citations still work when messages are loaded from history (not just during streaming).

---

### Step 6: Extend Message Serializer

**File: `backend/apps/chat/serializers.py`**

Add source chunks to the message serializer so they're included when loading message history:

```python
class MessageSerializer(serializers.ModelSerializer):
    source_chunks = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [...existing..., 'source_chunks']

    def get_source_chunks(self, obj):
        """Return source chunks for RAG-grounded messages."""
        if obj.role != 'assistant':
            return []
        chunks = obj.source_chunks.select_related('document').all()
        if not chunks:
            return []
        return [
            {
                'index': i,
                'chunk_id': str(chunk.id),
                'document_id': str(chunk.document_id),
                'document_title': chunk.document.title if chunk.document else '',
                'chunk_index': chunk.chunk_index,
                'excerpt': chunk.chunk_text[:200],
            }
            for i, chunk in enumerate(chunks)
        ]
```

---

### Step 7: Frontend — Add SSE Handler

**File: `frontend/src/lib/api/chat.ts`**

Add `source_chunks` callback to `sendUnifiedStream()`:

```typescript
// In StreamingCallbacks type:
export interface StreamingCallbacks {
    // ... existing callbacks ...
    onSourceChunks?: (chunks: SourceChunk[]) => void;
}

// In the event switch:
case 'source_chunks':
    callbacks.onSourceChunks?.(data?.chunks || []);
    break;
```

**Add type definition** (`frontend/src/lib/types/chat.ts`):

```typescript
export interface SourceChunk {
    index: number;          // Matches [N] in response (0-indexed)
    chunk_id: string;
    document_id: string;
    document_title: string;
    chunk_index: number;
    excerpt: string;
    similarity?: number;
}
```

---

### Step 8: Frontend — Store Source Chunks in Message State

**File: `frontend/src/hooks/useStreamingChat.ts`** (or wherever messages state is managed)

When `onSourceChunks` fires, associate the chunks with the current assistant message:

```typescript
// In useStreamingChat or useConversationState:
const [messageSourceChunks, setMessageSourceChunks] = useState<Map<string, SourceChunk[]>>(new Map());

const handleSourceChunks = useCallback((chunks: SourceChunk[]) => {
    if (currentAssistantMessageId) {
        setMessageSourceChunks(prev => {
            const next = new Map(prev);
            next.set(currentAssistantMessageId, chunks);
            return next;
        });
    }
}, [currentAssistantMessageId]);
```

When loading message history (from the serializer), populate from `message.source_chunks`.

---

### Step 9: Frontend — Citation Badge Component

**File: `frontend/src/components/chat/CitationBadge.tsx`** (NEW)

A small inline badge that replaces `[1]` in rendered markdown:

```typescript
interface CitationBadgeProps {
    index: number;           // The citation number (1-indexed display)
    chunk: SourceChunk;
    isHighlighted?: boolean;
    onClick?: () => void;
}
```

**Visual design:**
- Small superscript pill: `[1]` in accent color
- Hover: tooltip with document title + excerpt preview
- Click: scrolls to/highlights the source in a citation panel
- Uses `@floating-ui/react` for positioning (already in deps, used by CitationPopover)

---

### Step 10: Frontend — Citation Footer on Messages

**File: `frontend/src/components/chat/MessageList.tsx`**

Add a collapsible citation footer below assistant messages that have sources:

```typescript
// After the Streamdown markdown render:
{sourceChunks.length > 0 && (
    <CitationFooter
        chunks={sourceChunks}
        highlightedIndex={highlightedCitation}
        onChunkClick={(chunk) => {
            // Navigate to document in project landscape
            router.push(`/projects/${projectId}?doc=${chunk.document_id}&chunk=${chunk.chunk_index}`);
        }}
    />
)}
```

**CitationFooter design:**
- Collapsed by default: shows "Sources: Doc A, Doc B" as one line
- Expanded: shows each source with excerpt, document title, similarity score
- Each source is clickable → navigates to document/chunk
- Grounding indicator: "Grounded in N sources" vs "General knowledge" badge

---

### Step 11: Frontend — Parse Citations in Markdown

**File: `frontend/src/components/chat/CitationRenderer.tsx`** (NEW)

A custom remark plugin or post-processing step that converts `[1]` text markers into interactive `CitationBadge` components:

```typescript
function parseCitations(
    text: string,
    sourceChunks: SourceChunk[]
): ReactNode {
    // Regex: match [N] where N is a number
    const parts = text.split(/\[(\d+)\]/g);
    return parts.map((part, i) => {
        if (i % 2 === 1) {
            // This is a citation number
            const citIndex = parseInt(part, 10) - 1; // Convert 1-indexed to 0-indexed
            const chunk = sourceChunks[citIndex];
            if (chunk) {
                return <CitationBadge key={i} index={citIndex + 1} chunk={chunk} />;
            }
        }
        return part;
    });
}
```

**Integration with Streamdown:** The citation parsing should run as a post-processing step AFTER markdown rendering, not as a remark plugin (since Streamdown handles incomplete markdown during streaming). Parse the rendered HTML/text for `[N]` patterns and replace with React components.

---

## Data Flow Summary

```
1. User sends message
2. Backend: retrieve_document_context() → RetrievalResult {context_text, chunks[]}
3. Backend: LLM prompt includes numbered sources + citation instructions
4. Backend: LLM responds with [1], [2] markers in text
5. Backend: Stream response_chunk events (response text with [N] markers)
6. Backend: Stream source_chunks event (chunk metadata array)
7. Backend: Save source_chunks M2M on assistant Message
8. Frontend: Receive source_chunks, store in state keyed by message ID
9. Frontend: Parse [N] markers in rendered markdown → CitationBadge components
10. Frontend: Show CitationFooter below message with source list
11. On page reload: Load source_chunks from Message serializer
```

---

## Key Files to Modify

| File | Change |
|------|--------|
| `backend/apps/chat/models.py` | Add `source_chunks` M2M on Message |
| `backend/apps/chat/migrations/XXXX_...` | Create migration |
| `backend/apps/chat/retrieval.py` | Return `RetrievalResult` instead of string |
| `backend/apps/intelligence/prompts.py` | Add citation format instructions |
| `backend/apps/chat/views.py` | Unpack RetrievalResult, emit `source_chunks` SSE event |
| `backend/apps/intelligence/handlers.py` | Save source_chunks on Message after creation |
| `backend/apps/chat/serializers.py` | Add `source_chunks` to MessageSerializer |
| `frontend/src/lib/types/chat.ts` | Add `SourceChunk` interface |
| `frontend/src/lib/api/chat.ts` | Add `onSourceChunks` callback |
| `frontend/src/hooks/useStreamingChat.ts` | Store source chunks per message |
| `frontend/src/components/chat/CitationBadge.tsx` | NEW — inline citation badge |
| `frontend/src/components/chat/CitationFooter.tsx` | NEW — source list below message |
| `frontend/src/components/chat/CitationRenderer.tsx` | NEW — parse [N] markers in markdown |
| `frontend/src/components/chat/MessageList.tsx` | Integrate CitationFooter + pass source chunks |

---

## Edge Cases

1. **No project documents:** `retrieve_document_context()` returns empty → no citations, no `source_chunks` event, messages render normally
2. **LLM doesn't cite:** Source chunks are still saved (they were used as context), CitationFooter shows "Sources used" even without inline markers
3. **LLM cites non-existent index:** `CitationRenderer` ignores `[N]` markers where N > chunks.length — renders as plain text
4. **Streaming in progress:** Source chunks arrive AFTER response completes — citations are rendered retroactively (markdown re-parses with chunks available)
5. **Message history reload:** Source chunks loaded from serializer, not from SSE — same rendering path
6. **Long documents with many chunks:** `RetrievalResult` already capped at `top_k=5` (configurable) — max 5 citations per message

---

## Testing

1. **Backend unit test:** `retrieve_document_context()` returns `RetrievalResult` with correct chunk metadata
2. **Backend unit test:** Message serializer includes `source_chunks` for assistant messages
3. **Backend integration test:** Unified stream emits `source_chunks` event with correct data
4. **Frontend unit test:** `CitationRenderer` correctly parses `[1]`, `[2]` markers
5. **Frontend unit test:** `CitationBadge` renders with correct document title on hover
6. **E2E test:** Upload doc → chat about it → see citations in response
