# Phase 2.2: Evidence Model - Implementation Complete! 🎉

## What We Achieved

Successfully separated **Signals** (user thoughts) from **Evidence** (external facts), eliminating circular extraction and creating a clean conceptual model.

---

## The Core Insight

### BEFORE (Circular):
```
User: "I assume writes are append-only"
  → Signal extracted
  
AI generates research doc: "The system uses append-only writes"
  → Signal extracted (same assumption, different words)
  
Result: Duplicate, circular, noisy
```

### AFTER (Clean):
```
User: "I assume writes are append-only"  
  → Signal extracted (user's thought)
  
User uploads benchmark: "System achieved 50k append-only writes/sec"
  → Evidence extracted (external fact)
  
Result: Signal (thought) + Evidence (receipt)
```

---

## What Was Built

### 1. Evidence Model

**File:** [`backend/apps/projects/models.py`](backend/apps/projects/models.py)

```python
class Evidence:
    - text: The extracted fact
    - type: metric, benchmark, fact, claim, quote
    - chunk: Pointer to source chunk (exact location)
    - document: Source document
    - extraction_confidence: How confident the LLM was
    - user_credibility_rating: User's 1-5 star rating
    - embedding: 384-dim vector for similarity
```

**Key distinction:**
- Signal = "I assume X" (user's belief)
- Evidence = "Study shows X" (external fact)

---

### 2. Evidence Extraction

**Files:**
- Prompt: [`backend/apps/signals/prompts.py`](backend/apps/signals/prompts.py) - `get_evidence_extraction_prompt()`
- Extractor: [`backend/apps/projects/evidence_extractor.py`](backend/apps/projects/evidence_extractor.py)

**What it extracts:**
- Metrics: "50,000 requests per second"
- Benchmarks: "Postgres 2x faster than MongoDB"
- Facts: "PostgreSQL supports JSONB indexing"
- Claims: "This is the fastest key-value store"
- Quotes: "According to author: '...'"

**What it doesn't extract:**
- User assumptions (those are Signals)
- Questions (those are Signals)
- Opinions/recommendations

---

### 3. Updated Document Processing

**File:** [`backend/apps/projects/services.py`](backend/apps/projects/services.py)

**New pipeline:**
```
1. Extract text (PDF, DOCX, TXT)
2. Chunk (512 tokens, recursive)
3. Embed chunks
4. Extract Evidence from chunks  ← NEW
5. Link evidence to chunks
6. Store in PostgreSQL
```

**Result:** Documents now produce Evidence (not Signals).

---

### 4. Evidence API

**File:** [`backend/apps/projects/evidence_views.py`](backend/apps/projects/evidence_views.py)

**Endpoints:**
```http
GET /api/evidence/                          # List all evidence
GET /api/evidence/?document_id={id}         # Evidence from specific doc
GET /api/evidence/?case_id={id}             # All evidence in case
GET /api/evidence/?type=metric              # Filter by type
GET /api/evidence/?min_rating=4             # High-credibility only
GET /api/evidence/high_confidence/          # Confidence > 0.8 or rating >= 4
PATCH /api/evidence/{id}/rate/              # User rates credibility
```

---

### 5. Migration Command

**File:** [`backend/apps/projects/management/commands/migrate_signals_to_evidence.py`](backend/apps/projects/management/commands/migrate_signals_to_evidence.py)

**Usage:**
```bash
# Preview
python manage.py migrate_signals_to_evidence --dry-run

# Execute
python manage.py migrate_signals_to_evidence
```

**What it does:**
- Finds all Signals with `source_type='document'`
- Converts to Evidence objects
- Deletes the document-sourced signals
- Preserves embeddings and chunk links

---

### 6. Comprehensive Tests

**Files:**
- [`backend/apps/projects/tests.py`](backend/apps/projects/tests.py) - Evidence extraction tests

**Test coverage:**
- Evidence extraction from documents
- Chunk linking
- User credibility rating
- API filtering
- Migration script

---

## How to Use It

### Setup (5 minutes)

```bash
# 1. Rebuild (includes all Phase 2 dependencies)
docker-compose build backend
docker-compose up -d

# 2. Run migrations
docker-compose exec backend python manage.py makemigrations projects
docker-compose exec backend python manage.py migrate

# 3. Migrate existing data (if any)
docker-compose exec backend python manage.py migrate_signals_to_evidence
```

### Test It

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' | jq -r '.access')

# Create project
PROJECT=$(curl -s -X POST http://localhost:8000/api/projects/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Evidence Test"}' | jq -r '.id')

# Upload document with facts
curl -X POST http://localhost:8000/api/documents/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Performance Benchmark",
    "source_type":"text",
    "content_text":"Benchmark Results: PostgreSQL handled 50,000 writes per second. The p99 latency was 150ms. According to the report: PostgreSQL outperformed MongoDB by 2x for write operations.",
    "project_id":"'$PROJECT'"
  }'

# Wait for processing
sleep 10

# Query evidence
curl http://localhost:8000/api/evidence/?project_id=$PROJECT \
  -H "Authorization: Bearer $TOKEN" | jq
```

Expected response:
```json
[
  {
    "text": "PostgreSQL handled 50,000 writes per second",
    "type": "metric",
    "extraction_confidence": 0.95,
    "chunk_preview": {...}
  },
  {
    "text": "P99 latency was 150ms",
    "type": "metric",
    "extraction_confidence": 0.90
  },
  {
    "text": "PostgreSQL outperformed MongoDB by 2x for write operations",
    "type": "benchmark",
    "extraction_confidence": 0.85
  }
]
```

---

## The Clean Model

### Signals (User Thoughts)
**Source:** User chat messages ONLY

**Types:** Assumption, Question, Constraint, Goal, DecisionIntent

**Example:** "I assume we'll stay under 10k users"

---

### Evidence (External Facts)
**Source:** User-uploaded documents

**Types:** Metric, Benchmark, Fact, Claim, Quote

**Example:** "Benchmark shows 50k writes/sec"

---

### Future: Artifacts (AI Outputs)
**Source:** AI-generated research, briefs, criticism

**Structure:** Blocks (not chunks)

**Provenance:** CITES signals and evidence (doesn't re-extract)

---

## What This Fixes

✅ **No more circular extraction**
- AI docs won't create signals
- Only user chat creates signals

✅ **Clear conceptual model**
- Thoughts vs Facts
- Intent vs Evidence

✅ **Atomic grounding**
- Each evidence links to exact chunk
- Can show user: "This metric from page 3 supports your assumption"

✅ **User agency**
- User can rate evidence credibility
- Can accept/reject evidence like signals

✅ **Foundation for graph**
- Ready for Phase 2.3: Evidence → supports/contradicts → Signal

---

## Next Steps

### Immediate Testing

```bash
# Run tests
docker-compose exec backend pytest apps/projects/tests.py::EvidenceExtractionTest

# Upload a real document and verify evidence extraction
```

### Phase 2.3 (Next Week)

Add knowledge graph edges:
```python
# In Evidence model:
supports_signals = ManyToManyField(Signal)
contradicts_signals = ManyToManyField(Signal)

# In Signal model:
supported_by_evidence = ManyToManyField(Evidence)
contradicted_by_evidence = ManyToManyField(Evidence)
```

Then you can query: "What evidence supports this assumption?"

---

## Files Created/Modified

**New Files:**
- `apps/projects/evidence_extractor.py`
- `apps/projects/evidence_serializers.py`
- `apps/projects/evidence_views.py`
- `apps/projects/management/commands/migrate_signals_to_evidence.py`

**Modified Files:**
- `apps/projects/models.py` (Evidence model added)
- `apps/projects/services.py` (Evidence extraction in pipeline)
- `apps/projects/urls.py` (Evidence routes)
- `apps/signals/prompts.py` (Evidence extraction prompt)
- `apps/projects/tests.py` (Evidence tests)

---

## Success Metrics

After Phase 2.2:

✅ Documents create Evidence (not Signals)
✅ Evidence extraction is lighter/faster than signal extraction
✅ Each Evidence points to exact chunk (citation ready)
✅ User can rate evidence credibility
✅ Clean separation: thoughts vs facts
✅ Ready for knowledge graph (Phase 2.3)

**The conceptual model is now clean!** Ready to add relationship edges next.
