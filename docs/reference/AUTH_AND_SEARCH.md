# Authentication & Unified Search

## Part 1: Authentication System

Email-based JWT authentication with comprehensive user preferences.

### Login Flow

1. User submits `{email, password}` to `POST /api/auth/token/`
2. System looks up user by email → authenticates via username
3. Returns `{access, refresh}` JWT tokens

### Token Lifecycle

| Token | Lifetime | Usage |
|-------|----------|-------|
| Access | 5 minutes | `Authorization: Bearer {token}` on all API requests |
| Refresh | 24 hours | `POST /api/auth/token/refresh/` to get new access token |

### SSE Authentication Workaround

EventSource API cannot send custom headers, so a `QueryParamJWTAuthentication` class is defined that falls back to `?token=<jwt>` query parameter. Defined in `common/authentication.py` but SSE endpoints currently use a manual JWT auth helper instead.

### User Preferences (23+ settings)

Auto-created via Django signal when user is created.

**Workspace:**
- `default_case_view` — brief | dashboard | documents
- `auto_save_delay_ms` — Debounce delay (default 1000ms)
- `auto_create_inquiries` — Extract questions from conversation
- `auto_detect_assumptions` — Extract beliefs from conversation
- `auto_generate_titles` — Generate case/inquiry titles

**AI/Agent:**
- `chat_model` — Default LLM (default: `anthropic:claude-haiku-4-5`)
- `agent_check_interval` — Check for inflection every N turns (default 3)
- `agent_min_confidence` — Minimum to suggest agents (default 0.75)
- `agent_auto_run` — Auto-execute high-confidence suggestions (> 0.95)

**Structure Discovery:**
- `structure_auto_detect` — Suggest case creation for unstructured chats
- `structure_sensitivity` — 1-5, how proactive to suggest
- `structure_auto_create` — Auto-create vs. show suggestion

**Signal Highlighting:**
- `highlight_assumptions`, `highlight_evidence`, `highlight_questions` — Inline chat highlighting

**Evidence:**
- `evidence_min_credibility` — Minimum star rating to count (1-5, default 3)

**Appearance:**
- `theme` — light | dark | auto
- `font_size` — small | medium | large
- `density` — compact | comfortable | relaxed

**Notifications:**
- `email_notifications`, `notify_on_inquiry_resolved`, `notify_on_agent_complete`

**Debug:**
- `show_debug_info` — Display event IDs and correlation IDs
- `show_ai_prompts` — Show LLM prompts for transparency

### Auth API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/token/` | POST | Login (email + password → tokens) |
| `/api/auth/token/refresh/` | POST | Refresh access token |
| `/api/auth/me/` | GET | Current user profile + preferences |
| `/api/auth/preferences/` | GET/PATCH | Get or update preferences |

---

## Part 2: Unified Search Service

**File:** `backend/apps/common/unified_search.py` (~573 lines)

Semantic search across 5 content types with parallel execution, context-aware grouping, and vectorized similarity.

### Architecture

```
Query text
  → Generate embedding (384-dim, cached 300s TTL)
  → ThreadPoolExecutor (5 concurrent workers)
      ├── Search signals (top 500)
      ├── Search evidence (top 500)
      ├── Search inquiries (top 100, pre-computed embeddings)
      ├── Search cases (top 50, pre-computed embeddings)
      └── Search documents (top 500 chunks, deduped to documents)
  → Collect results
  → Sort by cosine similarity
  → Split: in_context (current case/project) vs. other
  → Return top_k per group
```

### Content Type Details

| Type | Limit | Embedding Source | Special Behavior |
|------|-------|-----------------|-----------------|
| Signals | 500 | Stored on signal | Type icon (assumption, question, etc.) |
| Evidence | 500 | Stored on evidence | Shows source document name |
| Inquiries | 100 | **Pre-computed** on model | Fallback: batch generate |
| Cases | 50 | **Pre-computed** on model | Fallback: batch generate |
| Documents | 500 chunks | Stored on chunk | Deduped to best chunk per document |

### Performance Optimizations

| Optimization | Impact |
|-------------|--------|
| **Parallel search** (5 workers) | ~40-50% faster than sequential |
| **Batch vectorized cosine similarity** | ~10x faster than loop (`numpy` matrix ops) |
| **Pre-computed embeddings** on Inquiry/Case models | Skip ~100ms generation |
| **Query cache** (LRU, 300s TTL, 100 capacity) | Save ~50ms on repeated queries |
| **Early limits** (500/100/50 per type) | Don't compute similarity on everything |

### Similarity Thresholds

| Context | Threshold |
|---------|-----------|
| Search (default) | 0.4 (broad recall) |
| Signal similar | 0.85 |
| Signal dedup | 0.90 |
| Strict search | 0.6-0.7 |

### Context-Aware Grouping

Results split into two lists:
- **`in_context`** — Results from current case or project (prioritized)
- **`other`** — Results from other cases

Both limited to `top_k` items.

### API

**`POST /api/search/`**

Request:
```json
{
  "query": "market assumptions",
  "context": { "case_id": "uuid", "project_id": "uuid" },
  "types": ["signal", "evidence"],
  "top_k": 20,
  "threshold": 0.4
}
```

Response:
```json
{
  "query": "market assumptions",
  "in_context": [
    {
      "id": "uuid", "type": "signal",
      "title": "Market size assumption...",
      "subtitle": "Assumption, Validated",
      "score": 0.892,
      "case_id": "uuid", "case_title": "Market Entry Decision",
      "metadata": { "signal_type": "Assumption", "confidence": 0.85 }
    }
  ],
  "other": [],
  "recent": [],
  "total_count": 42
}
```

Empty query returns recent items (5 cases, 3 inquiries if in case context).

---

## Key Files

```
backend/apps/
├── auth_app/
│   ├── views.py                # Login, refresh, me, preferences
│   ├── serializers.py          # EmailTokenObtainPairSerializer, UserPreferencesSerializer
│   └── models.py               # UserPreferences (auto-created on user creation)
├── common/
│   ├── authentication.py       # QueryParamJWTAuthentication
│   └── unified_search.py       # UnifiedSearchService
└── config/settings/base.py     # JWT defaults (SimpleJWT)
```
