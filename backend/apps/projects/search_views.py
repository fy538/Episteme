"""
Document search views - semantic search across documents using pgvector.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.common.vector_utils import generate_embedding, similarity_search
from apps.projects.models import DocumentChunk


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def search_documents(request):
    """
    Semantic search across all documents using pgvector.

    POST /api/documents/semantic-search/
    {
        "query": "What does research say about user latency?",
        "top_k": 10,
        "filters": {
            "case_id": "uuid",
            "document_ids": ["uuid1", "uuid2"]
        }
    }
    """
    query_text = request.data.get('query')
    if not query_text:
        return Response(
            {'error': 'query is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    top_k = request.data.get('top_k', 10)
    filters = request.data.get('filters', {})

    # Generate query embedding
    query_embedding = generate_embedding(query_text)

    # Build queryset with filters
    queryset = DocumentChunk.objects.select_related('document').exclude(
        embedding__isnull=True
    )

    if 'document_ids' in filters and filters['document_ids']:
        queryset = queryset.filter(document_id__in=filters['document_ids'])

    if 'case_id' in filters and filters['case_id']:
        queryset = queryset.filter(document__case_id=filters['case_id'])

    # Similarity search via pgvector
    similar_chunks = similarity_search(
        queryset=queryset,
        embedding_field='embedding',
        query_vector=query_embedding,
        threshold=0.4,
        top_k=top_k,
    )

    results = []
    for chunk in similar_chunks:
        similarity = 1.0 - chunk.distance
        results.append({
            'chunk_id': str(chunk.id),
            'document_id': str(chunk.document.id),
            'document_title': chunk.document.title,
            'chunk_text': chunk.chunk_text,
            'chunk_index': chunk.chunk_index,
            'relevance_score': round(similarity, 4),
            'span': chunk.span,
            'token_count': chunk.token_count,
        })

    return Response({
        'results': results,
        'total': len(results),
        'query': query_text,
    })
