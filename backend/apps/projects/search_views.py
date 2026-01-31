"""
Document search views - semantic search across documents.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from sentence_transformers import SentenceTransformer

from apps.common.vector_service import get_vector_service
from apps.projects.models import Document, DocumentChunk


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def search_documents(request):
    """
    Semantic search across all documents.
    
    POST /api/documents/semantic-search/
    {
        "query": "What does research say about user latency?",
        "top_k": 10,
        "filters": {
            "case_id": "uuid",  // optional
            "document_ids": ["uuid1", "uuid2"]  // optional
        }
    }
    
    Returns:
    {
        "results": [
            {
                "chunk_id": "uuid",
                "document_id": "uuid",
                "document_title": "...",
                "chunk_text": "...",
                "chunk_index": 0,
                "relevance_score": 0.85,
                "span": {"page": 5, "start_char": 100, "end_char": 1100}
            }
        ]
    }
    """
    query_text = request.data.get('query')
    if not query_text:
        return Response(
            {'error': 'query is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    top_k = request.data.get('top_k', 10)
    filters = request.data.get('filters', {})
    
    # Generate query embedding
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode(query_text).tolist()
    
    # Build metadata filter for vector DB
    vector_filter = {}
    
    if 'document_ids' in filters and filters['document_ids']:
        # Pinecone filter format
        vector_filter['document_id'] = {'$in': [str(doc_id) for doc_id in filters['document_ids']]}
    
    # Search vector database
    vector_service = get_vector_service()
    search_results = vector_service.search(
        query_embedding=query_embedding,
        top_k=top_k,
        filter=vector_filter if vector_filter else None
    )
    
    # Process results
    results = []
    chunk_ids = [match['id'] for match in search_results.get('matches', [])]
    
    # Fetch chunk details from DB
    chunks = DocumentChunk.objects.filter(
        id__in=chunk_ids
    ).select_related('document')
    
    # Create lookup
    chunk_lookup = {str(chunk.id): chunk for chunk in chunks}
    
    # Build response
    for match in search_results.get('matches', []):
        chunk_id = match['id']
        chunk = chunk_lookup.get(chunk_id)
        
        if not chunk:
            continue
        
        # Apply case filter if specified (DB-level)
        if 'case_id' in filters and filters['case_id']:
            if not chunk.document.case_id or str(chunk.document.case_id) != str(filters['case_id']):
                continue
        
        results.append({
            'chunk_id': str(chunk.id),
            'document_id': str(chunk.document.id),
            'document_title': chunk.document.title,
            'document_author': chunk.document.author,
            'chunk_text': chunk.chunk_text,
            'chunk_index': chunk.chunk_index,
            'relevance_score': match['score'],
            'span': chunk.span,
            'token_count': chunk.token_count,
        })
    
    return Response({
        'results': results,
        'total': len(results),
        'query': query_text,
    })
