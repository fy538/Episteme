# Quick Start: Document System

## TL;DR

Documents are now **chunked and searchable** (like Cursor with code), not extracted into signals. They can be **cited as evidence** in inquiries and serve as sources for **objections**.

## 5-Minute Setup

### 1. Install & Migrate

```bash
# Install dependencies
pip install -r requirements/base.txt

# Run migrations
python manage.py makemigrations projects inquiries
python manage.py migrate
```

### 2. Configure Pinecone

Sign up at [pinecone.io](https://pinecone.io) (free tier available)

Add to `.env`:
```bash
PINECONE_API_KEY=your-api-key-here
PINECONE_ENVIRONMENT=us-east-1
```

### 3. Initialize Vector Index

```python
python manage.py shell

from apps.common.vector_service import get_vector_service
vector_service = get_vector_service()
vector_service.initialize_index(dimension=384)
```

Done! Ready to use.

## Common Workflows

### Upload a Document

```python
# Via API
POST /api/documents/
{
    "title": "PostgreSQL Performance Study",
    "project_id": "uuid",
    "source_type": "upload",
    file: <PDF/DOCX file>
}

# Automatically:
# 1. Extracts text
# 2. Chunks into ~1000 char segments
# 3. Generates embeddings
# 4. Indexes in Pinecone
```

### Search Documents

```python
POST /api/documents/semantic-search/
{
    "query": "PostgreSQL write performance",
    "top_k": 5
}

# Returns relevant chunks with scores
```

### Create an Inquiry

```python
POST /api/inquiries/
{
    "case": "case-uuid",
    "title": "Is PostgreSQL fast enough for our workload?",
    "elevation_reason": "user_created"
}
```

### Cite Document as Evidence

```python
# After searching and finding relevant chunks...
POST /api/evidence/cite_document/
{
    "inquiry_id": "inquiry-uuid",
    "document_id": "doc-uuid",
    "chunk_ids": ["chunk-uuid-1", "chunk-uuid-2"],
    "evidence_text": "Benchmarks show PG handles 15k writes/sec",
    "direction": "supports",
    "strength": 0.8,
    "credibility": 0.9
}
```

### Add Objection

```python
POST /api/objections/
{
    "inquiry": "inquiry-uuid",
    "objection_text": "Benchmark uses 1GB dataset, ours is 10GB",
    "objection_type": "scope_limitation",
    "source": "document",
    "source_document": "doc-uuid",
    "chunk_ids": ["chunk-uuid-3"]
}
```

### View Inquiry with Evidence & Objections

```python
GET /api/inquiries/{inquiry-uuid}/

# Then get related items:
GET /api/evidence/?inquiry={inquiry-uuid}
GET /api/objections/?inquiry={inquiry-uuid}
```

## Understanding the Flow

```
1. USER UPLOADS DOCUMENT
   └─> Document created (pending)
   └─> process_document_workflow triggered (async)
       ├─> Extract text (PDF/DOCX/text)
       ├─> Chunk into segments
       ├─> Generate embeddings
       └─> Index in Pinecone

2. USER SEARCHES
   └─> Embed query
   └─> Search Pinecone
   └─> Return relevant chunks

3. USER CITES AS EVIDENCE
   └─> Link chunks to inquiry
   └─> Mark as supports/contradicts
   └─> Track strength & credibility

4. INQUIRY SHOWS STRUCTURED REASONING
   └─> Related signals (user's thoughts)
   └─> Evidence (document citations)
   └─> Objections (challenges)
   └─> Conclusion (when resolved)
```

## Key Concepts

### Signals vs Chunks

**Signals** (from chat):
- User's own thinking extracted from conversation
- Tracks assumptions, claims, questions over time
- Shows evolution of thought

**Chunks** (from documents):
- Static knowledge, not user's thinking
- Searchable, citable, but not extracted
- Preserves full context

### Evidence vs Objections

**Evidence:**
- Supports or contradicts an inquiry
- Has direction, strength, credibility
- User verifies and adds notes

**Objections:**
- Challenges assumptions
- Surfaces alternative perspectives
- Can be addressed or dismissed

### Inquiry Structure

```
Inquiry: "Is PostgreSQL faster?"
├─ Related Signals (user's claims/assumptions)
├─ Evidence (document citations, tests)
├─ Objections (challenges to reasoning)
└─ Conclusion (resolution with confidence)
```

## Frontend Integration Points

### Document Upload Flow

```javascript
// 1. Upload document
POST /api/documents/
FormData: {file, title, project_id}

// 2. Poll for processing completion
GET /api/documents/{id}/
// Wait until processing_status === 'indexed'

// 3. Show chunks
GET /api/documents/{id}/chunks/
```

### Document Search & Citation

```javascript
// 1. User asks about topic
POST /api/documents/semantic-search/
{query: "write performance", top_k: 5}

// 2. Show results to user
results.forEach(chunk => {
  // Display: chunk_text, document_title, relevance_score
  // Action: [Cite as evidence] [View in document]
})

// 3. User cites
POST /api/evidence/cite_document/
{inquiry_id, document_id, chunk_ids, direction}
```

### Inquiry Detail View

```javascript
// Get inquiry
GET /api/inquiries/{id}/

// Get related content
GET /api/evidence/?inquiry={id}
GET /api/objections/?inquiry={id}

// Show structure:
// - Title, status, conclusion
// - Evidence (supports/contradicts)
// - Objections (active/addressed)
// - Related signals
```

## Troubleshooting

### Document Processing Fails
- Check file type is supported (PDF, DOCX, txt)
- Check file size under MAX_UPLOAD_SIZE
- Check Celery is running
- View logs: `document.processing_status === 'failed'`

### Search Returns No Results
- Verify document is `indexed` (not pending/chunking)
- Check Pinecone credentials
- Verify vector index exists
- Try broader query

### Can't Create Evidence
- Verify inquiry exists and belongs to user
- Check document is indexed
- Verify chunk_ids exist if providing them

## Advanced Usage

### Search with Filters

```python
POST /api/documents/semantic-search/
{
    "query": "latency benchmarks",
    "top_k": 10,
    "filters": {
        "case_id": "uuid",
        "document_ids": ["doc1", "doc2"]  // only search these docs
    }
}
```

### Cite Multiple Chunks

```python
POST /api/evidence/cite_document/
{
    "chunk_ids": ["chunk1", "chunk2", "chunk3"],
    // User is citing multiple sections from same document
}
```

### System-Generated Objections (Future)

```python
# When inquiry is created, system can analyze and generate objections
POST /api/objections/
{
    "source": "system",
    "objection_type": "challenge_assumption",
    "objection_text": "Your assumption depends on X, but document Y contradicts X"
}
```

## Performance Tips

- **Batch uploads**: Upload multiple documents, they process in parallel
- **Filter searches**: Use case_id or document_ids to narrow results
- **Cache results**: Search results can be cached client-side
- **Chunk summaries**: Coming in Phase 3 for faster browsing

## What Changed from Signal Extraction

**Before (Lossy):**
```
Document: "PG handled 15k writes/sec in tests, but performance 
degraded beyond 20k writes/sec with complex queries..."

Extracted Signal: "PostgreSQL handles 15k writes/sec"
└─> Lost: degradation, complex queries, context
```

**Now (Full Context):**
```
Document → Chunks (full text preserved)
User searches → Finds relevant chunks
User cites → Evidence with full context visible
```

## Summary

The document system is production-ready with:
- Complete implementation (models, services, APIs)
- Vector search (Pinecone integration)
- Evidence-based reasoning (cite documents in inquiries)
- Structured challenges (objections)
- Full documentation

**Start using it:** Upload docs, search, cite as evidence, add objections!
