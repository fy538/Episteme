"""
Graph API views — endpoints for the knowledge graph and Evidence Map.

All views require authentication and filter by project ownership.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.projects.models import Project
from apps.cases.models import Case
from apps.events.services import EventService
from apps.events.models import EventType, ActorType

from .models import Node, GraphDelta, CaseNodeReference, InclusionType, ProjectSummary, SummaryStatus
from .serializers import (
    NodeSerializer,
    NodeDetailSerializer,
    EdgeSerializer,
    GraphDeltaSerializer,
    NodeUpdateSerializer,
    CaseNodeReferenceSerializer,
    ProjectSummarySerializer,
)
from .clustering import ClusteringService
from .services import GraphService
from .summary_service import ProjectSummaryService


def _get_user_project(request, project_id):
    """Get a project owned by the requesting user, or None."""
    try:
        return Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_graph_view(request, project_id):
    """
    GET /api/v2/projects/{project_id}/graph/

    Returns the full graph (nodes + edges) for a project.
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    graph = GraphService.get_project_graph(project_id)
    return Response({
        'nodes': NodeSerializer(graph['nodes'], many=True).data,
        'edges': EdgeSerializer(graph['edges'], many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_graph_clustered_view(request, project_id):
    """
    GET /api/v2/projects/{project_id}/graph/clustered/?resolution=1.0

    Returns the full graph (nodes + edges) plus backend-computed clusters
    and cluster quality metrics. Clustering results are cached for 60s.
    """
    from django.core.cache import cache

    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    resolution = float(request.query_params.get('resolution', '1.0'))

    graph = GraphService.get_project_graph(project_id)
    nodes_data = NodeSerializer(graph['nodes'], many=True).data
    edges_data = EdgeSerializer(graph['edges'], many=True).data

    # Cache clustering by project + resolution + node count (proxy for staleness)
    node_count = len(graph['nodes'])
    cache_key = f"graph_clusters:{project_id}:{resolution}:{node_count}"
    cached = cache.get(cache_key)

    if cached:
        clusters, cluster_quality = cached
    else:
        clusters = ClusteringService.cluster_project_nodes(
            project_id, resolution=resolution,
        )
        cluster_quality = ClusteringService.compute_cluster_quality(
            clusters, graph['edges'],
        )
        cache.set(cache_key, (clusters, cluster_quality), timeout=60)

    return Response({
        'nodes': nodes_data,
        'edges': edges_data,
        'clusters': clusters,
        'cluster_quality': cluster_quality,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def node_search_view(request, project_id):
    """
    GET /api/v2/projects/{project_id}/nodes/search/?q=...&top_k=10&type=claim

    Semantic search over graph nodes using pgvector cosine similarity.
    Optional filters: type (claim|evidence|assumption|tension), top_k (max 50).
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    query = request.query_params.get('q', '').strip()
    if not query:
        return Response(
            {'error': 'q parameter required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from apps.common.vector_utils import generate_embedding, similarity_search

    query_vector = generate_embedding(query)
    queryset = Node.objects.filter(project_id=project_id).select_related('source_document')

    # Optional type filter
    node_type = request.query_params.get('type')
    if node_type:
        queryset = queryset.filter(node_type=node_type)

    top_k = min(int(request.query_params.get('top_k', 10)), 50)

    results = similarity_search(
        queryset=queryset,
        embedding_field='embedding',
        query_vector=query_vector,
        threshold=0.4,
        top_k=top_k,
    )

    nodes_data = NodeSerializer(results, many=True).data
    for node_data, node_obj in zip(nodes_data, results):
        node_data['similarity'] = round(1.0 - node_obj.distance, 3)

    return Response({'results': nodes_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def node_detail_view(request, project_id, node_id):
    """
    GET /api/v2/projects/{project_id}/nodes/{node_id}/

    Returns a single node with its connected edges and neighbors.
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        node = (
            Node.objects
            .select_related('source_document')
            .prefetch_related('source_chunks__document')
            .get(id=node_id, project_id=project_id)
        )
    except Node.DoesNotExist:
        return Response(
            {'error': 'Node not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = NodeDetailSerializer(node)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def node_update_view(request, project_id, node_id):
    """
    PATCH /api/v2/projects/{project_id}/nodes/{node_id}/

    Update a node (content, status, properties, confidence).
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        node = Node.objects.get(id=node_id, project_id=project_id)
    except Node.DoesNotExist:
        return Response(
            {'error': 'Node not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = NodeUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    updated_node = GraphService.update_node(
        node_id=node_id,
        **serializer.validated_data,
    )

    return Response(NodeDetailSerializer(updated_node).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_graph_delta_view(request, project_id, document_id):
    """
    GET /api/v2/projects/{project_id}/documents/{document_id}/graph-delta/

    Returns the most recent graph delta for a specific document.
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    from .delta_service import GraphDeltaService

    delta = GraphDeltaService.get_document_delta(project_id, document_id)
    if not delta:
        return Response(
            {'error': 'No graph delta found for this document'},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = GraphDeltaSerializer(delta)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_subgraph_view(request, project_id, document_id):
    """
    GET /api/v2/projects/{project_id}/documents/{document_id}/graph/

    Returns the argument structure graph for a single document:
    nodes sorted by importance (core thesis first) + intra-document edges.
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    subgraph = GraphService.get_document_subgraph(document_id)
    if not subgraph['nodes']:
        return Response(
            {'error': 'No graph nodes found for this document'},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response({
        'nodes': NodeSerializer(subgraph['nodes'], many=True).data,
        'edges': EdgeSerializer(subgraph['edges'], many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_deltas_view(request, project_id):
    """
    GET /api/v2/projects/{project_id}/graph/deltas/

    Returns recent graph deltas for a project.
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    from .delta_service import GraphDeltaService

    limit = int(request.query_params.get('limit', 20))
    deltas = GraphDeltaService.get_project_deltas(project_id, limit=limit)
    serializer = GraphDeltaSerializer(deltas, many=True)
    return Response(serializer.data)


# ── Case-scoped graph endpoints ─────────────────────────────────


def _get_user_case(request, project_id, case_id):
    """Get a case owned by the requesting user within a project, or None."""
    try:
        return Case.objects.get(
            id=case_id, project_id=project_id, user=request.user,
        )
    except Case.DoesNotExist:
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_graph_view(request, project_id, case_id):
    """
    GET /api/v2/projects/{project_id}/cases/{case_id}/graph/

    Returns the composed case graph (case-scoped nodes + referenced
    project nodes + edges where both endpoints are visible).
    """
    case = _get_user_case(request, project_id, case_id)
    if not case:
        return Response({'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    graph = GraphService.get_case_graph(case_id)
    return Response({
        'nodes': NodeSerializer(graph['nodes'], many=True).data,
        'edges': EdgeSerializer(graph['edges'], many=True).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def case_pull_node_view(request, project_id, case_id):
    """
    POST /api/v2/projects/{project_id}/cases/{case_id}/graph/pull/

    Pull a project-scoped node into the case view.
    Body: {"node_id": "uuid"}
    """
    case = _get_user_case(request, project_id, case_id)
    if not case:
        return Response({'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    node_id = request.data.get('node_id')
    if not node_id:
        return Response({'error': 'node_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        node = Node.objects.get(id=node_id, project_id=project_id, scope='project')
    except Node.DoesNotExist:
        return Response({'error': 'Node not found or not project-scoped'}, status=status.HTTP_404_NOT_FOUND)

    ref, created = CaseNodeReference.objects.get_or_create(
        case=case, node=node,
        defaults={'inclusion_type': InclusionType.MANUAL, 'excluded': False},
    )
    if not created and ref.excluded:
        ref.excluded = False
        ref.inclusion_type = InclusionType.MANUAL
        ref.save(update_fields=['excluded', 'inclusion_type', 'updated_at'])

    EventService.append(
        event_type=EventType.CASE_NODE_PULLED,
        payload={'node_id': str(node_id), 'node_content': node.content[:80]},
        actor_type=ActorType.USER,
        actor_id=request.user.id,
        case_id=case_id,
    )

    return Response(
        CaseNodeReferenceSerializer(ref).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def case_exclude_node_view(request, project_id, case_id):
    """
    POST /api/v2/projects/{project_id}/cases/{case_id}/graph/exclude/

    Soft-hide a referenced node from the case view.
    Body: {"node_id": "uuid"}
    """
    case = _get_user_case(request, project_id, case_id)
    if not case:
        return Response({'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    node_id = request.data.get('node_id')
    if not node_id:
        return Response({'error': 'node_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        ref = CaseNodeReference.objects.get(case_id=case_id, node_id=node_id)
    except CaseNodeReference.DoesNotExist:
        return Response({'error': 'Node reference not found'}, status=status.HTTP_404_NOT_FOUND)

    ref.excluded = True
    ref.save(update_fields=['excluded', 'updated_at'])

    EventService.append(
        event_type=EventType.CASE_NODE_EXCLUDED,
        payload={'node_id': str(node_id)},
        actor_type=ActorType.USER,
        actor_id=request.user.id,
        case_id=case_id,
    )

    return Response({'status': 'excluded', 'node_id': str(node_id)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def promote_document_view(request, project_id, document_id):
    """
    POST /api/v2/projects/{project_id}/documents/{document_id}/promote/

    Promote a case-scoped document to project scope.
    """
    from apps.projects.models import Document

    project = _get_user_project(request, project_id)
    if not project:
        return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        document = Document.objects.get(id=document_id, project_id=project_id)
    except Document.DoesNotExist:
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)

    if document.scope != 'case':
        return Response({'error': 'Document is already project-scoped'}, status=status.HTTP_400_BAD_REQUEST)

    original_case_id = document.case_id
    result = GraphService.promote_document_to_project(document)

    EventService.append(
        event_type=EventType.DOCUMENT_PROMOTED,
        payload={
            'document_id': str(document_id),
            'document_title': document.title,
            'node_count': len(result.get('node_ids', [])),
        },
        actor_type=ActorType.USER,
        actor_id=request.user.id,
        case_id=original_case_id,
    )

    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def demote_document_view(request, project_id, document_id):
    """
    POST /api/v2/projects/{project_id}/documents/{document_id}/demote/

    Demote a project-scoped document to case scope.
    Body: {"case_id": "uuid"}
    """
    from apps.projects.models import Document

    project = _get_user_project(request, project_id)
    if not project:
        return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

    target_case_id = request.data.get('case_id')
    if not target_case_id:
        return Response({'error': 'case_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        document = Document.objects.get(id=document_id, project_id=project_id)
    except Document.DoesNotExist:
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)

    if document.scope != 'project':
        return Response({'error': 'Document is already case-scoped'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        case = Case.objects.get(id=target_case_id, project_id=project_id, user=request.user)
    except Case.DoesNotExist:
        return Response({'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    result = GraphService.demote_document_to_case(document, case)

    EventService.append(
        event_type=EventType.DOCUMENT_DEMOTED,
        payload={
            'document_id': str(document_id),
            'document_title': document.title,
            'case_id': str(target_case_id),
            'node_count': len(result.get('node_ids', [])),
            'references_created': result.get('references_created', 0),
        },
        actor_type=ActorType.USER,
        actor_id=request.user.id,
        case_id=target_case_id,
    )

    return Response(result)


# ── Project Summary endpoints ────────────────────────────────────


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_summary_view(request, project_id):
    """
    GET /api/v2/projects/{project_id}/summary/

    Returns the current project summary. If no summary exists,
    returns a seed/empty response based on graph size.
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    summary = ProjectSummaryService.get_current_summary(project_id)

    if summary:
        return Response(ProjectSummarySerializer(summary).data)

    # No summary — check node count to determine state
    node_count = Node.objects.filter(project_id=project_id).count()

    if node_count == 0:
        return Response({
            'status': SummaryStatus.NONE,
            'sections': {},
            'is_stale': False,
            'clusters': [],
        })

    if node_count < 5:
        sections = ProjectSummaryService.get_seed_summary(project_id)
        return Response({
            'status': SummaryStatus.SEED,
            'sections': sections,
            'is_stale': False,
            'clusters': [],
        })

    # 5+ nodes but no summary yet — frontend can trigger generation
    return Response({
        'status': SummaryStatus.NONE,
        'sections': {},
        'is_stale': True,
        'clusters': [],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def project_summary_regenerate_view(request, project_id):
    """
    POST /api/v2/projects/{project_id}/summary/regenerate/

    Trigger summary regeneration. Returns 202 Accepted immediately.
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    generating = ProjectSummary.objects.filter(
        project_id=project_id,
        status=SummaryStatus.GENERATING,
    ).exists()
    if generating:
        return Response(
            {'error': 'Summary is already being generated'},
            status=status.HTTP_409_CONFLICT,
        )

    from .tasks import generate_project_summary
    task = generate_project_summary.delay(str(project_id), force=True)

    return Response(
        {'status': 'generating', 'task_id': task.id},
        status=status.HTTP_202_ACCEPTED,
    )
