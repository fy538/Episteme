# Chat Streaming Architecture

Every user message flows through a unified streaming pipeline that produces a chat response, meta-cognitive reflection, extracted signals, and action hints — all from a **single LLM call** using sectioned XML markers.

## End-to-End Flow

```
User types message → sendMessage()
    ↓
Optimistic messages created (local-user-*, local-assistant-*)
    ↓
POST /api/chat/threads/{id}/unified-stream/
    ↓
Backend: JWT auth → save user message → build prompts
    ↓
LLM streams sectioned output: <response> <reflection> <signals> <action_hints>
    ↓
SectionedStreamParser routes chunks by section
    ↓
SSE events sent to frontend (response_chunk, reflection_chunk, signals, done)
    ↓
Frontend appends tokens to optimistic assistant message
    ↓
On done: replace temp ID with real ID, save reflection + signals to DB
    ↓
Async: generate signal embeddings (Celery)
```

---

## Backend

### Streaming Endpoint

```
POST /api/chat/threads/{id}/unified-stream/
Content-Type: application/json
Accept: text/event-stream

Body: {
  "content": "User message",
  "context": { "mode": "case", "caseId": "uuid", "inquiryId": "uuid" }
}
```

- JWT auth handled async (outside DRF) via `_authenticate_jwt()`
- Creates user message in DB before streaming
- Returns `StreamingHttpResponse` with `text/event-stream`
- Headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no` (disables nginx buffering)

### UnifiedAnalysisEngine (`intelligence/engine.py`)

`analyze_simple(thread, user_message, conversation_context)`:

1. Fetches last 10 non-dismissed signals for context
2. Gets patterns from companion `GraphAnalyzer`
3. Builds system + user prompts via `UnifiedPromptConfig`
4. Streams from LLM provider (`max_tokens=2048`)
5. Parses output through `SectionedStreamParser`
6. Yields `StreamEvent` objects

### LLM Output Format

The LLM returns structured XML sections in a single response:

```xml
<response>
[2-4 paragraphs of conversational response]
</response>

<reflection>
[2-3 sentence meta-cognitive observation]
</reflection>

<signals>
[{"type": "Assumption", "text": "...", "confidence": 0.8}, ...]
</signals>

<action_hints>
[{"type": "suggest_case", "reason": "...", "data": {...}}]
</action_hints>
```

### SectionedStreamParser (`intelligence/parser.py`)

Handles the complexity of streaming XML markers that may split across token boundaries:

| Section | Behavior | Why |
|---------|----------|-----|
| `<response>` | Streamed immediately as chunks | User sees tokens appear in real-time |
| `<reflection>` | Streamed immediately as chunks | Companion panel updates live |
| `<signals>` | Buffered until `</signals>` | Must be valid JSON to parse |
| `<action_hints>` | Buffered until `</action_hints>` | Must be valid JSON to parse |

Max marker length: 17 chars (`</action_hints>`). Buffer retains potential partial markers.

### SSE Event Types

| Event | Data | When |
|-------|------|------|
| `response_chunk` | `{ delta: string }` | Each token of chat response |
| `reflection_chunk` | `{ delta: string }` | Each token of reflection |
| `signals` | `{ signals: Signal[] }` | After `</signals>` parsed |
| `action_hints` | `{ action_hints: ActionHint[] }` | After `</action_hints>` parsed |
| `done` | `{ message_id, reflection_id, signals_count }` | Stream complete |
| `error` | `{ message: string }` | On failure |

### Post-Processing (`intelligence/handlers.py`)

`UnifiedAnalysisHandler.handle_completion()` runs after the stream ends:

1. **Save assistant message** to DB
2. **Save reflection** to DB (non-fatal if fails)
3. **Parse signals JSON** → deduplicate via `SHA256(type:text.lower())` → create `Signal` records
4. **Emit** `WORKFLOW_COMPLETED` event
5. **Trigger async** embedding generation (Celery task)
6. **Update thread extraction state** for next-turn decisions

### Extraction Rules (`intelligence/extraction_rules.py`)

Decides per-turn whether to include signal extraction in the prompt:

| Condition | Extract? |
|-----------|----------|
| First message in thread | Always |
| Contains trigger phrases ("I assume", "not sure", "should we") | Yes |
| ≥2 turns AND ≥200 chars since last extraction | Yes |
| ≥5 turns without any extraction | Forced |
| Otherwise | No (saves cost) |

---

## Frontend

### API Client (`lib/api/client.ts`)

`apiClient.stream(endpoint, data, onEvent, signal)`:

- POST with `Accept: text/event-stream`
- Reads response body via `ReadableStream` + `TextDecoder`
- Splits buffer on `\n\n` (SSE delimiter)
- Parses `event:` and `data:` lines per SSE spec
- JSON-parses data, invokes `onEvent({ event, data })` callback
- Passes `AbortSignal` to `fetch()` for cancellation

### useStreamingChat Hook (`hooks/useStreamingChat.ts`)

Core streaming state machine shared by all chat consumers.

**State:**
- `messages`, `isLoading`, `isStreaming`, `isWaitingForResponse`
- `ttft` (time-to-first-token in ms), `error`, `lastFailedMessage`

**Optimistic Rendering:**
```
1. Create local-user-{ts} and local-assistant-{ts} messages
2. Add both to messages array immediately
3. On response_chunk: append delta to local-assistant content
4. On done: replace local-assistant ID with real server ID
5. On error: remove local-assistant, store message for retry
```

**Dual Timeout Strategy:**
- **TTFT timeout (30s):** If no first token arrives within 30 seconds, abort. Likely a connection or server issue.
- **Total stream timeout (60s):** If entire stream exceeds 60 seconds, abort. Prevents hung connections.
- First token received → clears TTFT timeout (server is responsive).

**AbortController:**
- Created per message send
- User can click "stop" to cancel mid-stream
- Timeouts trigger `controller.abort()`
- On abort: clean up optimistic messages, clear loading states

**Retry:**
- On error, stores `lastFailedMessage`
- `handleRetry()` clears state and re-sends the stored message

### useChatPanelState Hook (`hooks/useChatPanelState.ts`)

Adds domain logic on top of `useStreamingChat`:

- **Signals:** Loads existing signals on thread change; deduplicates streaming signals into local state
- **Action hints → Cards:** Converts `suggest_case` hints to `InlineActionCard` positioned after the relevant assistant message
- **Message tracking:** Tracks `latestAssistantMessageId` for card placement

### Mode-Aware System Prompts

Frontend sends `context: { mode, caseId, inquiryId }` with each message. Backend selects the appropriate system prompt:

| Mode | System Prompt |
|------|--------------|
| `scaffolding` | Injects active skill domain knowledge |
| `inquiry_focus` | Emphasizes investigation for specific inquiry |
| `case` | Stage-aware guidance (exploring → investigating → synthesizing → ready) |
| Default | General decision-thinking assistant |

---

## Key Constants

| Constant | Value | Location |
|----------|-------|----------|
| TTFT timeout | 30,000ms | `frontend/src/lib/constants.ts` |
| Total stream timeout | 60,000ms | `frontend/src/lib/constants.ts` |
| LLM max_tokens | 2,048 | `intelligence/engine.py` |
| Signal context window | Last 10 non-dismissed | `intelligence/engine.py` |
| Message context window | Last 10 messages | `intelligence/engine.py` |
| Max marker buffer | 17 chars | `intelligence/parser.py` |

---

## Key Files

```
backend/
├── apps/chat/views.py              # unified_stream() endpoint
├── apps/intelligence/
│   ├── engine.py                   # UnifiedAnalysisEngine
│   ├── parser.py                   # SectionedStreamParser
│   ├── prompts.py                  # System/user prompt construction
│   ├── handlers.py                 # Post-stream processing
│   └── extraction_rules.py         # When to extract signals
│
frontend/
├── src/lib/api/client.ts           # SSE streaming client
├── src/lib/api/chat.ts             # sendUnifiedStream()
├── src/hooks/useStreamingChat.ts   # Core streaming hook
├── src/hooks/useChatPanelState.ts  # Domain-specific chat state
├── src/lib/types/streaming.ts      # StreamingCallbacks type
├── src/lib/types/chat.ts           # Message, ActionHint types
└── src/lib/constants.ts            # Timeout values
```
