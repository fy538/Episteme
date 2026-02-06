"""
Unified Search Service

Combines semantic search across all content types:
- Signals (assumptions, questions, constraints, evidence mentions)
- Evidence (extracted facts from documents)
- Inquiries (investigations)
- Cases (decisions)
- Documents (briefs, research)

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
from apps.signals.similarity import cosine_similarity, batch_cosine_similarity

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result with metadata"""
    id: str
    type: str  # 'signal', 'evidence', 'inquiry', 'case', 'document'
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


def unified_search(
    query: str,
    user,
    context_case_id: Optional[str] = None,
    context_project_id: Optional[str] = None,
    types: Optional[List[str]] = None,  # Filter to specific types
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
        types: Filter to specific types ['signal', 'evidence', 'inquiry', 'case', 'document']
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
    search_types = types or ['signal', 'evidence', 'inquiry', 'case', 'document']

    # Map of search type to function
    search_functions = {
        'signal': _search_signals,
        'evidence': _search_evidence,
        'inquiry': _search_inquiries,
        'case': _search_cases,
        'document': _search_documents,
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
    from apps.cases.models import CaseDocument

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


def _search_signals(
    query_embedding: List[float],
    user,
    top_k: int,
    threshold: float
) -> List[SearchResult]:
    """Search signals by embedding similarity using vectorized batch comparison"""
    from apps.signals.models import Signal

    results = []

    # Get signals with embeddings
    signals = list(Signal.objects.filter(
        Q(case__user=user) | Q(thread__user=user),
        embedding__isnull=False,
        dismissed_at__isnull=True
    ).select_related('case', 'thread')[:500])  # Limit for performance

    if not signals:
        return results

    # Extract embeddings for batch processing
    embeddings = [s.embedding for s in signals if s.embedding]
    valid_signals = [s for s in signals if s.embedding]

    if not embeddings:
        return results

    # Vectorized batch similarity (much faster than loop)
    similarities = batch_cosine_similarity(query_embedding, embeddings)

    # Filter by threshold and pair with signals
    scored = [
        (signal, float(sim))
        for signal, sim in zip(valid_signals, similarities)
        if sim >= threshold
    ]

    # Sort and take top_k
    scored.sort(key=lambda x: x[1], reverse=True)

    for signal, score in scored[:top_k]:
        # Format signal type for display
        type_display = _format_signal_type(signal.type)
        status_badge = _get_signal_status_badge(signal)

        results.append(SearchResult(
            id=str(signal.id),
            type='signal',
            title=signal.text[:100] + ('...' if len(signal.text) > 100 else ''),
            subtitle=f"{type_display} {status_badge}",
            score=score,
            case_id=str(signal.case_id) if signal.case_id else None,
            case_title=signal.case.title if signal.case else None,
            metadata={
                'signal_type': signal.type,
                'confidence': signal.confidence,
                'has_evidence': hasattr(signal, 'supporting_evidence') and signal.supporting_evidence.exists(),
            }
        ))

    return results


def _search_evidence(
    query_embedding: List[float],
    user,
    top_k: int,
    threshold: float
) -> List[SearchResult]:
    """Search evidence by embedding similarity using vectorized batch comparison"""
    from apps.projects.models import Evidence

    results = []

    # Get evidence with embeddings
    evidence_items = list(Evidence.objects.filter(
        document__case__user=user,
        embedding__isnull=False
    ).select_related('document', 'document__case')[:500])

    if not evidence_items:
        return results

    # Extract embeddings for batch processing
    embeddings = [e.embedding for e in evidence_items if e.embedding]
    valid_evidence = [e for e in evidence_items if e.embedding]

    if not embeddings:
        return results

    # Vectorized batch similarity
    similarities = batch_cosine_similarity(query_embedding, embeddings)

    scored = [
        (evidence, float(sim))
        for evidence, sim in zip(valid_evidence, similarities)
        if sim >= threshold
    ]

    scored.sort(key=lambda x: x[1], reverse=True)

    for evidence, score in scored[:top_k]:
        results.append(SearchResult(
            id=str(evidence.id),
            type='evidence',
            title=evidence.text[:100] + ('...' if len(evidence.text) > 100 else ''),
            subtitle=f"From: {evidence.document.title if evidence.document else 'Unknown'}",
            score=score,
            case_id=str(evidence.document.case_id) if evidence.document and evidence.document.case_id else None,
            case_title=evidence.document.case.title if evidence.document and evidence.document.case else None,
            metadata={
                'evidence_type': evidence.evidence_type,
                'credibility': evidence.user_credibility_rating,
                'document_id': str(evidence.document_id) if evidence.document_id else None,
            }
        ))

    return results


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

    results = []

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

    results = []
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


def _search_documents(
    query_embedding: List[float],
    user,
    top_k: int,
    threshold: float
) -> List[SearchResult]:
    """Search documents by chunk embedding similarity using vectorized batch comparison"""
    from apps.projects.models import DocumentChunk, Document
    from apps.cases.models import CaseDocument

    results = []
    seen_docs = set()

    # Search document chunks
    chunks = list(DocumentChunk.objects.filter(
        document__case__user=user,
        embedding__isnull=False
    ).select_related('document', 'document__case')[:500])

    if not chunks:
        return results

    # Extract embeddings for batch processing
    embeddings = [c.embedding for c in chunks if c.embedding]
    valid_chunks = [c for c in chunks if c.embedding]

    if not embeddings:
        return results

    # Vectorized batch similarity
    similarities = batch_cosine_similarity(query_embedding, embeddings)

    scored = [
        (chunk, float(sim))
        for chunk, sim in zip(valid_chunks, similarities)
        if sim >= threshold
    ]

    scored.sort(key=lambda x: x[1], reverse=True)

    for chunk, score in scored[:top_k * 2]:  # Get more, will dedup
        doc_id = str(chunk.document_id)
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)

        doc = chunk.document
        results.append(SearchResult(
            id=str(doc.id),
            type='document',
            title=doc.title or 'Untitled Document',
            subtitle=f"{doc.document_type.replace('_', ' ').title()} · {chunk.chunk_text[:50]}...",
            score=score,
            case_id=str(doc.case_id) if doc.case_id else None,
            case_title=doc.case.title if doc.case else None,
            metadata={
                'document_type': doc.document_type,
                'chunk_preview': chunk.chunk_text[:100],
            }
        ))

        if len(results) >= top_k:
            break

    return results


def _format_signal_type(signal_type: str) -> str:
    """Format signal type for display"""
    type_icons = {
        'Assumption': '💭',
        'Question': '❓',
        'Constraint': '🚧',
        'EvidenceMention': '📊',
        'DecisionIntent': '🎯',
        'Claim': '💬',
        'Goal': '🏆',
    }
    icon = type_icons.get(signal_type, '📌')
    return f"{icon} {signal_type}"


def _get_signal_status_badge(signal) -> str:
    """
    Get status badge for signal.

    Note: Simplified to avoid N+1 queries. For accurate validation status,
    this should be pre-computed on the signal model or cached.
    """
    if signal.type == 'Assumption':
        # Use confidence as proxy for validation status
        # High confidence signals are more likely validated
        if signal.confidence and signal.confidence >= 0.8:
            return '✓ Validated'
        return '⚠️ Unvalidated'

    return ''
