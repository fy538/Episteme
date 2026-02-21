"""
Document chunk retrieval for RAG-augmented chat.

Retrieves the most relevant document chunks for a user's message
and formats them for injection into the LLM context window.

Retrieval strategies:
  1. Semantic (pgvector cosine similarity) — existing
  2. Keyword  (tsvector / BM25-style)       — added in hybrid retrieval
  3. Reciprocal Rank Fusion (RRF)            — merges results from both strategies
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from django.db.models import Q

from apps.common.vector_utils import generate_embedding, similarity_search

logger = logging.getLogger(__name__)

# Token budget for retrieval context (leaves room for system prompt + conversation)
MAX_RETRIEVAL_TOKENS = 3000


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
    context_text: str                        # Formatted for LLM prompt
    chunks: List[RetrievalChunk] = field(default_factory=list)

    @property
    def has_sources(self) -> bool:
        return len(self.chunks) > 0


# ---------------------------------------------------------------------------
# BM25-style keyword search via PostgreSQL tsvector
# ---------------------------------------------------------------------------

def bm25_search(
    query: str,
    project_id: UUID,
    case_id: Optional[UUID] = None,
    top_k: int = 10,
) -> List:
    """
    Keyword search using PostgreSQL full-text search (tsvector + ts_rank_cd).

    ts_rank_cd uses cover density ranking which approximates BM25 behaviour.
    Requires the search_vector generated column + GIN index from migration
    0017_add_tsvector_gin_index.

    Args:
        query: User's natural language query
        project_id: Scope to this project
        case_id: Optional case scope
        top_k: Max results to return

    Returns:
        List of DocumentChunk annotated with `rank` and `distance` fields,
        ordered by rank descending. Returns empty list on any error
        (including if the migration hasn't been run yet).
    """
    try:
        from django.contrib.postgres.search import SearchQuery, SearchRank
        from django.db.models import F
        from apps.projects.models import DocumentChunk

        # 'websearch' type handles natural language: OR, quoted phrases, -exclude
        search_query = SearchQuery(query, search_type='websearch')

        queryset = DocumentChunk.objects.filter(
            document__project_id=project_id,
            document__processing_status='indexed',
        ).select_related('document')

        if case_id:
            queryset = queryset.filter(
                Q(document__case_id=case_id) | Q(document__scope='project')
            )

        # ts_rank_cd: cover density ranking (approximates BM25)
        queryset = (
            queryset
            .filter(search_vector=search_query)
            .annotate(rank=SearchRank(F('search_vector'), search_query, cover_density=True))
            .order_by('-rank')[:top_k]
        )

        results = list(queryset)

        # Add a `distance` attribute for compatibility with semantic results
        # (distance = 1 - normalized_rank, so lower distance = better match)
        for r in results:
            # ts_rank_cd returns values roughly 0-1 but can exceed 1
            r.distance = max(0.0, 1.0 - min(float(r.rank), 1.0))

        return results
    except Exception as e:
        # Graceful fallback: tsvector column may not exist yet
        logger.debug(f"BM25 search unavailable (migration pending?): {e}")
        return []


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    *result_lists: List,
    k: int = 60,
    max_results: int = 5,
) -> List[Tuple]:
    """
    Merge multiple ranked result lists using Reciprocal Rank Fusion (RRF).

    RRF score for each document = sum(1 / (k + rank_i + 1)) across all lists.
    This is rank-based (not score-based) so it handles different score scales
    naturally — ideal for combining semantic similarity with BM25 rankings.

    Args:
        *result_lists: One or more ranked lists of DocumentChunk objects.
                       Rank is inferred from list position (0 = best).
        k: RRF constant (default 60, standard in literature)
        max_results: Maximum fused results to return

    Returns:
        List of (chunk, rrf_score) tuples sorted by score descending.
    """
    scores: Dict[str, float] = {}      # chunk_id → RRF score
    chunk_map: Dict[str, object] = {}   # chunk_id → chunk object

    for result_list in result_lists:
        for rank, chunk in enumerate(result_list):
            cid = str(chunk.id)
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            if cid not in chunk_map:
                chunk_map[cid] = chunk

    # Sort by RRF score descending
    sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

    fused = []
    for cid in sorted_ids[:max_results]:
        chunk = chunk_map[cid]
        # Set distance based on RRF score (higher RRF = lower distance)
        chunk.distance = max(0.0, 1.0 - scores[cid])
        fused.append((chunk, scores[cid]))

    return fused


def retrieve_document_context(
    query: str,
    project_id: UUID,
    case_id: Optional[UUID] = None,
    user=None,
    top_k: int = 5,
    threshold: float = 0.5,
    use_hybrid: bool = True,
) -> RetrievalResult:
    """
    Retrieve document chunks relevant to the user's message.

    When use_hybrid=True (default), runs both semantic search (pgvector)
    and keyword search (tsvector BM25) in parallel, then merges via RRF.
    Gracefully falls back to semantic-only if BM25 is unavailable.

    Args:
        query: The user's message text
        project_id: Project to search within
        case_id: Optional case to prioritise (also includes project-scope docs)
        user: Authenticated user (for ownership verification)
        top_k: Maximum chunks to retrieve
        threshold: Minimum cosine similarity (0.0-1.0)
        use_hybrid: If True, combine semantic + BM25 via RRF

    Returns:
        RetrievalResult with formatted context and chunk metadata,
        or empty RetrievalResult if nothing relevant found
    """
    empty = RetrievalResult(context_text='')

    if not query or not project_id:
        return empty

    # Generate query embedding
    query_vector = generate_embedding(query)
    if not query_vector:
        return empty

    from apps.projects.models import DocumentChunk

    # Build base queryset scoped to project
    queryset = DocumentChunk.objects.filter(
        document__project_id=project_id,
        document__processing_status='indexed',
    ).select_related('document')

    # If case context provided, retrieve case-scoped docs + project-scoped docs
    if case_id:
        queryset = queryset.filter(
            Q(document__case_id=case_id) | Q(document__scope='project')
        )

    # --- Semantic retrieval (always run) ---
    # Over-retrieve when hybrid is on, so RRF has a larger pool to fuse
    semantic_top_k = top_k * 2 if use_hybrid else top_k
    semantic_results = similarity_search(
        queryset=queryset,
        embedding_field='embedding',
        query_vector=query_vector,
        threshold=threshold,
        top_k=semantic_top_k,
    )

    # --- BM25 keyword retrieval (if hybrid enabled) ---
    keyword_results = []
    if use_hybrid:
        keyword_results = bm25_search(
            query=query,
            project_id=project_id,
            case_id=case_id,
            top_k=semantic_top_k,
        )

    # --- Fuse results ---
    if keyword_results and semantic_results:
        fused = reciprocal_rank_fusion(
            semantic_results, keyword_results,
            max_results=top_k,
        )
        final_chunks = [chunk for chunk, _score in fused]
        retrieval_method = 'hybrid'
    elif semantic_results:
        final_chunks = semantic_results[:top_k]
        retrieval_method = 'semantic'
    else:
        return empty

    if not final_chunks:
        return empty

    # Format results with token budget and numbered citations
    parts = []
    chunks = []
    total_tokens = 0

    for chunk in final_chunks:
        if total_tokens + chunk.token_count > MAX_RETRIEVAL_TOKENS:
            break

        # Skip orphaned chunks (document deleted between indexing and retrieval)
        if not chunk.document:
            logger.warning(f"Skipping orphaned chunk {chunk.id} — document missing")
            continue

        doc_title = chunk.document.title or 'Untitled'
        citation_num = len(parts) + 1  # 1-indexed for LLM display

        try:
            similarity = round(1 - float(chunk.distance), 3)
        except (TypeError, ValueError):
            similarity = 0.0

        # Numbered format so LLM can reference [1], [2], etc.
        parts.append(
            f'[{citation_num}] [Doc: "{doc_title}" chunk {chunk.chunk_index}]\n'
            f'{chunk.chunk_text}'
        )

        chunks.append(RetrievalChunk(
            chunk_id=str(chunk.id),
            document_id=str(chunk.document_id),
            document_title=doc_title,
            chunk_index=chunk.chunk_index,
            text=chunk.chunk_text,
            excerpt=chunk.chunk_text[:200],
            similarity=similarity,
        ))

        total_tokens += chunk.token_count

    if not parts:
        return empty

    logger.debug(
        "rag_chunks_retrieved",
        extra={
            'project_id': str(project_id),
            'case_id': str(case_id) if case_id else None,
            'chunks_retrieved': len(parts),
            'total_tokens': total_tokens,
            'retrieval_method': retrieval_method,
            'keyword_results': len(keyword_results),
            'semantic_results': len(semantic_results or []),
        },
    )

    return RetrievalResult(
        context_text="\n\n".join(parts),
        chunks=chunks,
    )
