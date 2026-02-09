"""
Document chunk retrieval for RAG-augmented chat.

Retrieves the most relevant document chunks for a user's message
and formats them for injection into the LLM context window.
"""
import logging
from typing import Optional
from uuid import UUID

from django.db.models import Q

from apps.common.vector_utils import generate_embedding, similarity_search

logger = logging.getLogger(__name__)

# Token budget for retrieval context (leaves room for system prompt + conversation)
MAX_RETRIEVAL_TOKENS = 3000


def retrieve_document_context(
    query: str,
    project_id: UUID,
    case_id: Optional[UUID] = None,
    user=None,
    top_k: int = 5,
    threshold: float = 0.5,
) -> str:
    """
    Retrieve document chunks relevant to the user's message.

    Generates an embedding for the query, searches project/case document
    chunks via pgvector cosine similarity, and formats results for LLM
    context injection.

    Args:
        query: The user's message text
        project_id: Project to search within
        case_id: Optional case to prioritise (also includes project-scope docs)
        user: Authenticated user (for ownership verification)
        top_k: Maximum chunks to retrieve
        threshold: Minimum cosine similarity (0.0-1.0)

    Returns:
        Formatted context string, or "" if nothing relevant found
    """
    if not query or not project_id:
        return ""

    # Generate query embedding
    query_vector = generate_embedding(query)
    if not query_vector:
        return ""

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

    similar_chunks = similarity_search(
        queryset=queryset,
        embedding_field='embedding',
        query_vector=query_vector,
        threshold=threshold,
        top_k=top_k,
    )

    if not similar_chunks:
        return ""

    # Format results with token budget
    parts = []
    total_tokens = 0

    for chunk in similar_chunks:
        if total_tokens + chunk.token_count > MAX_RETRIEVAL_TOKENS:
            break

        doc_title = chunk.document.title or 'Untitled'
        parts.append(
            f'[Doc: "{doc_title}" chunk {chunk.chunk_index}]\n'
            f'{chunk.chunk_text}'
        )
        total_tokens += chunk.token_count

    if not parts:
        return ""

    logger.debug(
        "rag_chunks_retrieved",
        extra={
            'project_id': str(project_id),
            'case_id': str(case_id) if case_id else None,
            'chunks_retrieved': len(parts),
            'total_tokens': total_tokens,
        },
    )

    return "\n\n".join(parts)
