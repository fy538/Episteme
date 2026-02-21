"""
Unified Search Service

Combines semantic search across all content types:
- Inquiries (investigations)
- Cases (decisions)
- Documents (briefs, research)
- Nodes (graph knowledge: claims, evidence, assumptions)

Groups results by context (current case vs other cases).

Optimizations:
- Parallel search across content types
- Batch embeddings for inquiries/cases
- No N+1 queries
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.db.models import Q

from apps.common.embeddings import generate_embedding
from apps.common.vector_utils import cosine_similarity, batch_cosine_similarity, similarity_search

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result with metadata"""
    id: str
    type: str  # 'inquiry', 'case', 'document'
    title: str
    subtitle: str
    score: float
    case_id: Optional[str] = None
    case_title: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedSearchResponse:
    """Grouped search results"""
    query: str
    in_context: List[SearchResult]  # Results in current case/project
    other: List[SearchResult]  # Results from other cases
    recent: List[SearchResult]  # Recent items (when no query)
    total_count: int


# ─── Inquiry search ──────────────────────────────────────────────────────────

def _search_inquiries(
    query_embedding: List[float],
    user,
    top_k: int,
    threshold: float
) -> List[SearchResult]:
    """
    Search inquiries using pre-computed embeddings.

    Optimization: Uses pre-computed embeddings stored on Inquiry model.
    Falls back to batch generation only for items without embeddings.
    """
    from apps.inquiries.models import Inquiry

    results: List[SearchResult] = []

    # Get inquiries for user
    inquiries = Inquiry.objects.filter(
        case__user=user
    ).select_related('case').order_by('-updated_at')[:100]

    inquiry_list = list(inquiries)
    scored = []

    # Separate inquiries with/without pre-computed embeddings
    with_embedding = []
    without_embedding = []

    for inquiry in inquiry_list:
        if inquiry.embedding:
            with_embedding.append(inquiry)
        else:
            without_embedding.append(inquiry)

    # Score inquiries that have pre-computed embeddings (fast path)
    for inquiry in with_embedding:
        similarity = cosine_similarity(query_embedding, inquiry.embedding)
        if similarity >= threshold:
            scored.append((inquiry, similarity))

    # Batch generate embeddings for items without them (legacy data)
    if without_embedding:
        from apps.common.embeddings import generate_embeddings_batch
        texts_to_embed = [
            f"{inq.title} {inq.description or ''}"[:200]
            for inq in without_embedding
        ]
        embeddings = generate_embeddings_batch(texts_to_embed)

        for inquiry, emb in zip(without_embedding, embeddings):
            if emb is None:
                continue
            similarity = cosine_similarity(query_embedding, emb)
            if similarity >= threshold:
                scored.append((inquiry, similarity))

    scored.sort(key=lambda x: x[1], reverse=True)

    for inquiry, score in scored[:top_k]:
        status_icon = {
            'open': '🟡',
            'investigating': '🔵',
            'resolved': '✓',
            'archived': '📦'
        }.get(inquiry.status, '')

        results.append(SearchResult(
            id=str(inquiry.id),
            type='inquiry',
            title=inquiry.title,
            subtitle=f"{status_icon} {inquiry.status.title()} · {inquiry.case.title if inquiry.case else 'No case'}",
            score=score,
            case_id=str(inquiry.case_id) if inquiry.case_id else None,
            case_title=inquiry.case.title if inquiry.case else None,
            metadata={
                'status': inquiry.status,
                'priority': inquiry.priority,
            }
        ))

    return results


# ─── Case search ─────────────────────────────────────────────────────────────

def _search_cases(
    query_embedding: List[float],
    user,
    top_k: int,
    threshold: float
) -> List[SearchResult]:
    """
    Search cases using pre-computed embeddings.

    Optimization: Uses pre-computed embeddings stored on Case model.
    Falls back to batch generation only for items without embeddings.
    """
    from apps.cases.models import Case

    results: List[SearchResult] = []
    cases = list(Case.objects.filter(user=user).order_by('-updated_at')[:50])

    if not cases:
        return results

    scored = []

    # Separate cases with/without pre-computed embeddings
    with_embedding = [c for c in cases if c.embedding]
    without_embedding = [c for c in cases if not c.embedding]

    # Score cases that have pre-computed embeddings (fast path)
    for case in with_embedding:
        similarity = cosine_similarity(query_embedding, case.embedding)
        if similarity >= threshold:
            scored.append((case, similarity))

    # Batch generate embeddings for items without them (legacy data)
    if without_embedding:
        from apps.common.embeddings import generate_embeddings_batch
        texts_to_embed = [
            f"{case.title or ''} {case.position or ''}"[:200]
            for case in without_embedding
        ]
        embeddings = generate_embeddings_batch(texts_to_embed)

        for case, emb in zip(without_embedding, embeddings):
            if emb is None:
                continue
            similarity = cosine_similarity(query_embedding, emb)
            if similarity >= threshold:
                scored.append((case, similarity))

    scored.sort(key=lambda x: x[1], reverse=True)

    for case, score in scored[:top_k]:
        results.append(SearchResult(
            id=str(case.id),
            type='case',
            title=case.title or 'Untitled Case',
            subtitle=f"{case.status.title()} · {case.stakes or 'No stakes'}",
            score=score,
            case_id=str(case.id),
            case_title=case.title,
            metadata={
                'status': case.status,
                'stakes': case.stakes,
            }
        ))

    return results


# ─── Document search ─────────────────────────────────────────────────────────

def _search_documents(
    query_embedding: List[float],
    user,
    top_k: int,
    threshold: float
) -> List[SearchResult]:
    """Search documents by chunk embedding similarity using pgvector CosineDistance."""
    from apps.projects.models import DocumentChunk

    results: List[SearchResult] = []
    seen_docs: set = set()

    queryset = DocumentChunk.objects.filter(
        document__project__user=user,
    ).select_related('document', 'document__case')

    similar_chunks = similarity_search(
        queryset=queryset,
        embedding_field='embedding',
        query_vector=query_embedding,
        threshold=threshold,
        top_k=top_k * 3,  # Fetch extra for dedup across documents
    )

    for chunk in similar_chunks:
        doc_id = str(chunk.document_id)
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)

        doc = chunk.document
        score = 1.0 - chunk.distance
        results.append(SearchResult(
            id=str(doc.id),
            type='document',
            title=doc.title or 'Untitled Document',
            subtitle=f"{doc.source_type.replace('_', ' ').title()} · {chunk.chunk_text[:50]}...",
            score=score,
            case_id=str(doc.case_id) if doc.case_id else None,
            case_title=doc.case.title if doc.case else None,
            metadata={
                'source_type': doc.source_type,
                'chunk_preview': chunk.chunk_text[:100],
            }
        ))

        if len(results) >= top_k:
            break

    return results


# ─── Node search ────────────────────────────────────────────────────────────

def _search_nodes(
    query_embedding: List[float],
    user,
    top_k: int,
    threshold: float,
) -> List[SearchResult]:
    """Search graph nodes by embedding similarity using pgvector CosineDistance."""
    from apps.graph.models import Node

    results: List[SearchResult] = []

    queryset = Node.objects.filter(
        project__user=user,
    ).select_related('source_document', 'project')

    similar_nodes = similarity_search(
        queryset=queryset,
        embedding_field='embedding',
        query_vector=query_embedding,
        threshold=threshold,
        top_k=top_k,
    )

    for node in similar_nodes:
        score = 1.0 - node.distance
        results.append(SearchResult(
            id=str(node.id),
            type='node',
            title=node.content[:80],
            subtitle=f"{node.node_type.title()} \u00b7 {node.status}",
            score=score,
            case_id=str(node.case_id) if node.case_id else None,
            metadata={
                'node_type': node.node_type,
                'status': node.status,
                'confidence': node.confidence,
                'project_id': str(node.project_id),
                'source_document_title': (
                    node.source_document.title if node.source_document else None
                ),
            },
        ))

    return results


# ─── Episode search ─────────────────────────────────────────────────────────

def _search_episodes(
    query_embedding: List[float],
    user,
    top_k: int,
    threshold: float,
) -> List[SearchResult]:
    """Search sealed conversation episodes by embedding similarity using pgvector CosineDistance."""
    from apps.chat.models import ConversationEpisode

    results: List[SearchResult] = []

    queryset = ConversationEpisode.objects.filter(
        thread__user=user,
        sealed=True,
    ).select_related('thread')

    similar_episodes = similarity_search(
        queryset=queryset,
        embedding_field='embedding',
        query_vector=query_embedding,
        threshold=threshold,
        top_k=top_k,
    )

    for episode in similar_episodes:
        score = 1.0 - episode.distance
        thread = episode.thread
        label = episode.topic_label or f"Episode {episode.episode_index}"
        thread_title = thread.title[:60] if thread else 'Unknown thread'

        results.append(SearchResult(
            id=str(episode.id),
            type='episode',
            title=label,
            subtitle=f"From \"{thread_title}\" \u00b7 {episode.message_count} messages",
            score=score,
            case_id=str(thread.primary_case_id) if thread and thread.primary_case_id else None,
            metadata={
                'thread_id': str(thread.id) if thread else None,
                'thread_title': thread_title,
                'shift_type': episode.shift_type,
                'message_count': episode.message_count,
                'content_summary': (episode.content_summary or '')[:100],
                'project_id': str(thread.project_id) if thread and thread.project_id else None,
            },
        ))

    return results


# ─── Unified search entry point ──────────────────────────────────────────────

def unified_search(
    query: str,
    user,
    context_case_id: Optional[str] = None,
    context_project_id: Optional[str] = None,
    types: Optional[List[str]] = None,  # Filter to specific types ['inquiry', 'case', 'document', 'node', 'episode']
    top_k: int = 20,
    threshold: float = 0.4,
) -> UnifiedSearchResponse:
    """
    Perform unified semantic search across all content types.

    Args:
        query: Search query text
        user: Authenticated user
        context_case_id: Current case ID for grouping (optional)
        context_project_id: Current project ID for grouping (optional)
        types: Filter to specific types ['inquiry', 'case', 'document', 'node', 'episode']
        top_k: Max results per type
        threshold: Minimum similarity threshold

    Returns:
        UnifiedSearchResponse with grouped results
    """
    if not query or not query.strip():
        return _get_recent_items(user, context_case_id)

    # Generate query embedding
    query_embedding = generate_embedding(query)
    if not query_embedding:
        return UnifiedSearchResponse(
            query=query,
            in_context=[],
            other=[],
            recent=[],
            total_count=0
        )

    all_results: List[SearchResult] = []
    search_types = types or ['inquiry', 'case', 'document', 'node', 'episode']

    # Map of search type to function
    search_functions = {
        'inquiry': _search_inquiries,
        'case': _search_cases,
        'document': _search_documents,
        'node': _search_nodes,
        'episode': _search_episodes,
    }

    # Execute searches in parallel for better latency
    # Each search type runs concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for search_type in search_types:
            if search_type in search_functions:
                future = executor.submit(
                    search_functions[search_type],
                    query_embedding, user, top_k, threshold
                )
                futures[future] = search_type

        # Collect results as they complete
        for future in as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Search failed for {futures[future]}: {e}")

    # Sort all results by score
    all_results.sort(key=lambda r: r.score, reverse=True)

    # Group by context
    in_context = []
    other = []

    for result in all_results:
        is_in_context = False

        if context_case_id and result.case_id == context_case_id:
            is_in_context = True
        elif context_project_id and result.metadata.get('project_id') == context_project_id:
            is_in_context = True

        if is_in_context:
            if len(in_context) < top_k:
                in_context.append(result)
        else:
            if len(other) < top_k:
                other.append(result)

    return UnifiedSearchResponse(
        query=query,
        in_context=in_context,
        other=other,
        recent=[],
        total_count=len(in_context) + len(other)
    )


def _get_recent_items(user, context_case_id: Optional[str] = None) -> UnifiedSearchResponse:
    """Get recent items for empty query state"""
    from apps.cases.models import Case
    from apps.inquiries.models import Inquiry
    from apps.cases.models import WorkingDocument

    recent = []

    # Recent cases
    cases = Case.objects.filter(user=user).order_by('-updated_at')[:5]
    for case in cases:
        recent.append(SearchResult(
            id=str(case.id),
            type='case',
            title=case.title or 'Untitled Case',
            subtitle=f"{case.status} · {case.stakes or 'No stakes set'}",
            score=1.0,
            case_id=str(case.id),
            case_title=case.title,
            metadata={'status': case.status, 'stakes': case.stakes}
        ))

    # Recent inquiries (if in a case context)
    if context_case_id:
        inquiries = Inquiry.objects.filter(
            case_id=context_case_id
        ).order_by('-updated_at')[:3]
        for inq in inquiries:
            recent.append(SearchResult(
                id=str(inq.id),
                type='inquiry',
                title=inq.title,
                subtitle=f"{inq.status} · {inq.case.title if inq.case else 'No case'}",
                score=1.0,
                case_id=str(inq.case_id) if inq.case_id else None,
                case_title=inq.case.title if inq.case else None,
                metadata={'status': inq.status}
            ))

    return UnifiedSearchResponse(
        query='',
        in_context=[],
        other=[],
        recent=recent,
        total_count=len(recent)
    )
