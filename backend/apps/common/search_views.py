"""
Unified Search API Views
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .unified_search import unified_search, SearchResult


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unified_search_view(request):
    """
    Unified semantic search across all content types.

    POST /api/search/
    {
        "query": "market assumptions",  // Search text (empty for recent items)
        "context": {
            "case_id": "uuid",  // Optional: current case for grouping
            "project_id": "uuid"  // Optional: current project for grouping
        },
        "types": ["signal", "evidence", "inquiry"],  // Optional: filter types
        "top_k": 20,  // Optional: max results per group
        "threshold": 0.4  // Optional: minimum similarity
    }

    Returns:
    {
        "query": "market assumptions",
        "in_context": [...],  // Results in current case/project
        "other": [...],  // Results from other cases
        "recent": [...],  // Recent items (when no query)
        "total_count": 15
    }
    """
    query = request.data.get('query', '')
    context = request.data.get('context', {})
    types = request.data.get('types')
    top_k = request.data.get('top_k', 20)
    threshold = request.data.get('threshold', 0.4)

    result = unified_search(
        query=query,
        user=request.user,
        context_case_id=context.get('case_id'),
        context_project_id=context.get('project_id'),
        types=types,
        top_k=top_k,
        threshold=threshold,
    )

    return Response({
        'query': result.query,
        'in_context': [_serialize_result(r) for r in result.in_context],
        'other': [_serialize_result(r) for r in result.other],
        'recent': [_serialize_result(r) for r in result.recent],
        'total_count': result.total_count,
    })


def _serialize_result(result: SearchResult) -> dict:
    """Serialize a SearchResult to JSON"""
    return {
        'id': result.id,
        'type': result.type,
        'title': result.title,
        'subtitle': result.subtitle,
        'score': round(result.score, 3),
        'case_id': result.case_id,
        'case_title': result.case_title,
        'metadata': result.metadata,
    }
