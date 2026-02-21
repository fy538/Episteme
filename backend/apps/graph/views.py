"""
Graph API views — endpoints for the knowledge graph and Evidence Map.

All views require authentication and filter by project ownership.
"""
import hashlib
import logging

logger = logging.getLogger(__name__)

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


def _parse_graph_params(request):
    """Extract limit and node_type query params for graph endpoints."""
    limit = request.query_params.get('limit')
    if limit is not None:
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = None
    node_type = request.query_params.get('node_type')
    return {'limit': limit, 'node_type': node_type}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_graph_view(request, project_id):
    """
    GET /api/v2/projects/{project_id}/graph/?limit=2000&node_type=claim

    Returns the graph (nodes + edges) for a project.
    Supports optional limit (default 2000, max 5000) and node_type filter.
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    params = _parse_graph_params(request)
    graph = GraphService.get_project_graph(project_id, **params)
    return Response({
        'nodes': NodeSerializer(graph['nodes'], many=True).data,
        'edges': EdgeSerializer(graph['edges'], many=True).data,
        'total_node_count': graph['total_node_count'],
        'truncated': graph['truncated'],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_graph_clustered_view(request, project_id):
    """
    GET /api/v2/projects/{project_id}/graph/clustered/?resolution=1.0&limit=2000&node_type=claim

    Returns the graph (nodes + edges) plus backend-computed clusters
    and cluster quality metrics. Clustering results are cached for 60s.
    Supports optional limit (default 2000, max 5000) and node_type filter.
    """
    from django.core.cache import cache

    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    resolution = float(request.query_params.get('resolution', '1.0'))
    params = _parse_graph_params(request)

    graph = GraphService.get_project_graph(project_id, **params)
    nodes_data = NodeSerializer(graph['nodes'], many=True).data
    edges_data = EdgeSerializer(graph['edges'], many=True).data

    # Cache clustering + enrichment together so the summary DB query
    # only runs once per cache miss (not on every request).
    node_count = len(graph['nodes'])
    latest_summary = ProjectSummaryService.get_current_summary(project_id)
    summary_version = latest_summary.version if latest_summary else 0
    cache_key = f"graph_clusters:{project_id}:{resolution}:{node_count}:{summary_version}"
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

        # Enrich clusters with LLM-generated labels and summaries from
        # the ProjectSummary (pre-computed during summary generation).
        # Only applies to FULL summaries which have centroid_node_id;
        # thematic summaries use chunk_ids and cannot match graph clusters.
        if (latest_summary
                and latest_summary.clusters
                and latest_summary.status in (SummaryStatus.FULL, SummaryStatus.PARTIAL)):
            summary_lookup = {}
            for sc in latest_summary.clusters:
                cid = sc.get('centroid_node_id')
                if cid:
                    summary_lookup[cid] = sc
            for cluster in clusters:
                stored = summary_lookup.get(cluster.get('centroid_node_id', ''))
                if stored:
                    if stored.get('label'):
                        cluster['label'] = stored['label']
                    if stored.get('summary'):
                        cluster['summary'] = stored['summary']

        cache.set(cache_key, (clusters, cluster_quality), timeout=60)

    return Response({
        'nodes': nodes_data,
        'edges': edges_data,
        'clusters': clusters,
        'cluster_quality': cluster_quality,
        'total_node_count': graph['total_node_count'],
        'truncated': graph['truncated'],
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
    missing_embedding_count = queryset.filter(embedding__isnull=True).count()

    semantic_results = list(similarity_search(
        queryset=queryset,
        embedding_field='embedding',
        query_vector=query_vector,
        threshold=0.4,
        top_k=top_k,
    ))

    results = list(semantic_results)

    # Fallback for nodes without embeddings so they are still discoverable.
    remaining = top_k - len(results)
    if remaining > 0:
        semantic_ids = [n.id for n in results]
        keyword_results = list(
            queryset.filter(
                embedding__isnull=True,
                content__icontains=query,
            )
            .exclude(id__in=semantic_ids)
            .order_by('-updated_at')[:remaining]
        )
        results.extend(keyword_results)

    semantic_id_set = {node.id for node in semantic_results}

    nodes_data = NodeSerializer(results, many=True).data
    for node_data, node_obj in zip(nodes_data, results):
        if node_obj.id in semantic_id_set:
            node_data['match_type'] = 'semantic'
            node_data['similarity'] = round(1.0 - node_obj.distance, 3)
        else:
            node_data['match_type'] = 'keyword_fallback'
            node_data['similarity'] = None

    payload = {'results': nodes_data}
    if missing_embedding_count:
        payload['warnings'] = {
            'nodes_missing_embeddings': missing_embedding_count,
        }

    return Response(payload)


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
    GET /api/v2/projects/{project_id}/cases/{case_id}/graph/?limit=2000&node_type=claim

    Returns the composed case graph (case-scoped nodes + referenced
    project nodes + edges where both endpoints are visible).
    Supports optional limit (default 2000, max 5000) and node_type filter.
    """
    case = _get_user_case(request, project_id, case_id)
    if not case:
        return Response({'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    params = _parse_graph_params(request)
    graph = GraphService.get_case_graph(case_id, **params)
    return Response({
        'nodes': NodeSerializer(graph['nodes'], many=True).data,
        'edges': EdgeSerializer(graph['edges'], many=True).data,
        'total_node_count': graph['total_node_count'],
        'truncated': graph['truncated'],
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

    Supports ETag / If-None-Match: returns 304 Not Modified when the
    summary hasn't changed, saving bandwidth on frequent polls.
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    summary = ProjectSummaryService.get_current_summary(project_id)

    if summary:
        # Build ETag from version + updated_at + status (stable, deterministic)
        etag_source = f'{summary.version}:{summary.updated_at.isoformat()}:{summary.status}'
        etag = f'"{hashlib.md5(etag_source.encode()).hexdigest()}"'

        # Check If-None-Match header from client
        if_none_match = request.META.get('HTTP_IF_NONE_MATCH', '')
        if if_none_match == etag:
            resp = Response(status=status.HTTP_304_NOT_MODIFIED)
            resp['ETag'] = etag
            return resp

        resp = Response(ProjectSummarySerializer(summary).data)
        resp['ETag'] = etag
        return resp

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


# ── Hierarchical Clustering endpoints ────────────────────────────


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_hierarchy_view(request, project_id):
    """
    GET /api/v2/projects/{project_id}/hierarchy/

    Returns the current cluster hierarchy for a project.
    """
    from .models import ClusterHierarchy
    from .serializers import ClusterHierarchySerializer

    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Return the current (ready/failed) hierarchy, or the latest building one
    hierarchy = (
        ClusterHierarchy.objects
        .filter(project_id=project_id, is_current=True)
        .first()
    )

    if not hierarchy:
        # Check for an in-progress build that hasn't become current yet
        from .models import HierarchyStatus
        hierarchy = (
            ClusterHierarchy.objects
            .filter(project_id=project_id, status=HierarchyStatus.BUILDING)
            .order_by('-created_at')
            .first()
        )

    if not hierarchy:
        return Response({
            'status': 'none',
            'tree': None,
            'metadata': {},
        })

    return Response(ClusterHierarchySerializer(hierarchy).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def project_hierarchy_rebuild_view(request, project_id):
    """
    POST /api/v2/projects/{project_id}/hierarchy/rebuild/

    Trigger a hierarchy rebuild. Returns 202 Accepted immediately.
    """
    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    from .models import ClusterHierarchy, HierarchyStatus

    # Check for an in-flight build before dispatching
    already_building = ClusterHierarchy.objects.filter(
        project_id=project_id,
        status=HierarchyStatus.BUILDING,
    ).exists()
    if already_building:
        return Response(
            {'status': 'already_building'},
            status=status.HTTP_409_CONFLICT,
        )

    from .tasks import build_cluster_hierarchy_task
    build_cluster_hierarchy_task.delay(str(project_id))

    return Response(
        {'status': 'building'},
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_insights_view(request, project_id):
    """
    GET /api/v2/projects/{project_id}/insights/?status=active&type=tension

    Returns project insights, filterable by status and type.
    """
    from .models import ProjectInsight
    from .serializers import ProjectInsightSerializer

    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    qs = ProjectInsight.objects.filter(project_id=project_id)

    # Optional filters
    insight_status = request.query_params.get('status')
    if insight_status:
        qs = qs.filter(status=insight_status)

    insight_type = request.query_params.get('type')
    if insight_type:
        qs = qs.filter(insight_type=insight_type)

    limit = min(int(request.query_params.get('limit', 20)), 100)
    qs = qs.order_by('-created_at')[:limit]

    return Response(ProjectInsightSerializer(qs, many=True).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def project_insight_update_view(request, project_id, insight_id):
    """
    PATCH /api/v2/projects/{project_id}/insights/{insight_id}/

    Update insight fields:
    - status: acknowledge, resolve, or dismiss
    - linked_thread: link a chat thread to this insight (for "Discuss this")
    """
    from .models import ProjectInsight
    from .serializers import ProjectInsightSerializer

    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        insight = ProjectInsight.objects.get(
            id=insight_id, project_id=project_id,
        )
    except ProjectInsight.DoesNotExist:
        return Response(
            {'error': 'Insight not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    update_fields = ['updated_at']

    # Status update (optional)
    new_status = request.data.get('status')
    if new_status is not None:
        if new_status not in ('acknowledged', 'resolved', 'dismissed'):
            return Response(
                {'error': 'status must be acknowledged, resolved, or dismissed'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        insight.status = new_status
        update_fields.append('status')

    # Thread linking (optional)
    linked_thread_id = request.data.get('linked_thread')
    if linked_thread_id is not None:
        from apps.chat.models import ChatThread
        try:
            thread = ChatThread.objects.get(id=linked_thread_id, user=request.user)
            insight.linked_thread = thread
            update_fields.append('linked_thread')
        except ChatThread.DoesNotExist:
            return Response(
                {'error': 'Thread not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

    if len(update_fields) == 1:
        # Only 'updated_at' — nothing to update
        return Response(
            {'error': 'No valid fields to update'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    insight.save(update_fields=update_fields)

    return Response(ProjectInsightSerializer(insight).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hierarchy_chunk_search_view(request, project_id):
    """
    GET /api/v2/projects/{project_id}/hierarchy/search/?q=...&top_k=20

    Search chunks by query embedding within the project's hierarchy.
    Returns chunks with their parent cluster context (topic/theme labels).

    This endpoint supports Plan 3 (Case Extraction) by providing
    relevant chunks from the hierarchy for case-level extraction.
    """
    from .models import ClusterHierarchy

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

    top_k = min(int(request.query_params.get('top_k', 20)), 50)

    # Semantic search over chunks
    from apps.common.vector_utils import generate_embedding, similarity_search
    from apps.projects.models import DocumentChunk

    query_vector = generate_embedding(query)
    chunk_qs = (
        DocumentChunk.objects
        .filter(document__project_id=project_id, embedding__isnull=False)
        .select_related('document')
    )

    results = list(similarity_search(
        queryset=chunk_qs,
        embedding_field='embedding',
        query_vector=query_vector,
        threshold=0.3,
        top_k=top_k,
    ))

    # Build chunk ID -> cluster context lookup from hierarchy
    from .models import HierarchyStatus
    hierarchy = (
        ClusterHierarchy.objects
        .filter(project_id=project_id, is_current=True, status=HierarchyStatus.READY)
        .first()
    )

    chunk_context = {}
    if hierarchy and hierarchy.tree:
        _build_chunk_context(hierarchy.tree, chunk_context, theme_label='', topic_label='')

    response_data = []
    for chunk in results:
        ctx = chunk_context.get(str(chunk.id), {})
        response_data.append({
            'chunk_id': str(chunk.id),
            'chunk_text': chunk.chunk_text[:500],
            'document_id': str(chunk.document_id),
            'document_title': chunk.document.title,
            'similarity': round(1.0 - chunk.distance, 3),
            'topic_label': ctx.get('topic_label', ''),
            'theme_label': ctx.get('theme_label', ''),
        })

    return Response({'results': response_data})


def _build_chunk_context(node: dict, context: dict, theme_label: str, topic_label: str):
    """Recursively build chunk_id -> {theme_label, topic_label} mapping."""
    level = node.get('level', 0)

    if level >= 2:
        theme_label = node.get('label', theme_label)
    if level == 1:
        topic_label = node.get('label', topic_label)

    # If this is a leaf-like node with chunk_ids, map them
    if not node.get('children'):
        for cid in node.get('chunk_ids', []):
            context[cid] = {
                'theme_label': theme_label,
                'topic_label': topic_label,
            }
    else:
        for child in node['children']:
            _build_chunk_context(child, context, theme_label, topic_label)


# ── Project Orientation endpoints ─────────────────────────────────


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_orientation_view(request, project_id):
    """
    GET /api/v2/projects/{project_id}/orientation/

    Returns the current orientation with its findings and exploration angles.
    """
    from .models import ProjectOrientation, OrientationStatus
    from .serializers import ProjectOrientationSerializer

    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    orientation = (
        ProjectOrientation.objects
        .filter(project_id=project_id, is_current=True)
        .prefetch_related('findings')
        .first()
    )

    if not orientation:
        # Check for an in-progress generation
        generating = (
            ProjectOrientation.objects
            .filter(project_id=project_id, status=OrientationStatus.GENERATING)
            .order_by('-created_at')
            .first()
        )
        if generating:
            return Response(ProjectOrientationSerializer(generating).data)

        return Response({
            'status': 'none',
            'lens_type': '',
            'lead_text': '',
            'findings': [],
        })

    return Response(ProjectOrientationSerializer(orientation).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def project_orientation_regenerate_view(request, project_id):
    """
    POST /api/v2/projects/{project_id}/orientation/regenerate/

    Trigger orientation regeneration from the current hierarchy.
    Returns 202 Accepted immediately.
    """
    from .models import ProjectOrientation, OrientationStatus, ClusterHierarchy, HierarchyStatus

    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Check for in-flight generation
    generating = ProjectOrientation.objects.filter(
        project_id=project_id,
        status=OrientationStatus.GENERATING,
    ).exists()
    if generating:
        return Response(
            {'error': 'Orientation is already being generated'},
            status=status.HTTP_409_CONFLICT,
        )

    # Need a ready hierarchy to regenerate from
    hierarchy = (
        ClusterHierarchy.objects
        .filter(
            project_id=project_id,
            is_current=True,
            status=HierarchyStatus.READY,
        )
        .first()
    )
    if not hierarchy:
        return Response(
            {'error': 'No ready hierarchy available'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from .tasks import generate_orientation_task
    task = generate_orientation_task.delay(
        project_id=str(project_id),
        hierarchy_id=str(hierarchy.id),
    )

    return Response(
        {'status': 'generating', 'task_id': task.id},
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def exploration_angle_generate_view(request, project_id, insight_id):
    """
    POST /api/v2/projects/{project_id}/insights/{insight_id}/generate/

    On-demand content generation for an exploration angle.
    Returns the generated content directly (synchronous, ~2-3s).
    """
    from asgiref.sync import async_to_sync
    from .models import ProjectInsight, InsightType
    from .orientation_service import OrientationService

    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        insight = ProjectInsight.objects.get(
            id=insight_id,
            project_id=project_id,
        )
    except ProjectInsight.DoesNotExist:
        return Response(
            {'error': 'Insight not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if insight.insight_type != InsightType.EXPLORATION_ANGLE:
        return Response(
            {'error': 'This insight is not an exploration angle'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Return cached content if already generated
    if insight.content:
        return Response({
            'insight_id': str(insight.id),
            'content': insight.content,
            'cached': True,
        })

    try:
        content = async_to_sync(OrientationService.generate_exploration_content)(
            insight_id=insight.id,
        )
        return Response({
            'insight_id': str(insight.id),
            'content': content,
            'cached': False,
        })
    except Exception as e:
        logger.exception("Failed to generate exploration content for insight %s", insight_id)
        return Response(
            {'error': 'Failed to generate exploration content. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def research_insight_view(request, project_id, insight_id):
    """
    POST /api/v2/projects/{project_id}/insights/{insight_id}/research/

    Trigger background research for a gap-type insight.
    Returns 202 Accepted immediately.
    """
    from .models import ProjectInsight, InsightStatus

    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        insight = ProjectInsight.objects.get(
            id=insight_id,
            project_id=project_id,
        )
    except ProjectInsight.DoesNotExist:
        return Response(
            {'error': 'Insight not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if insight.status == InsightStatus.RESEARCHING:
        return Response(
            {'error': 'Research is already in progress'},
            status=status.HTTP_409_CONFLICT,
        )

    from .tasks import research_insight_gap_task
    task = research_insight_gap_task.delay(
        project_id=str(project_id),
        insight_id=str(insight_id),
    )

    return Response(
        {'status': 'researching', 'task_id': task.id},
        status=status.HTTP_202_ACCEPTED,
    )


# ── Orientation chat editing ─────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def orientation_accept_diff_view(request, project_id):
    """
    POST /api/v2/projects/{project_id}/orientation/accept-diff/

    Accept an AI-proposed orientation diff from the chat UI.
    Merges the proposed state into the current orientation.

    Body: {
        orientation_id: uuid,
        proposed_state: {lead_text, lens_type, findings, angles},
        diff_summary: str,
        diff_data: dict,
    }
    """
    from .models import ProjectOrientation
    from .orientation_service import OrientationService

    project = _get_user_project(request, project_id)
    if not project:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    orientation_id = request.data.get('orientation_id')
    proposed_state = request.data.get('proposed_state')
    diff_summary = request.data.get('diff_summary', '')
    diff_data = request.data.get('diff_data', {})

    if not orientation_id or not proposed_state:
        return Response(
            {'error': 'orientation_id and proposed_state are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        orientation = OrientationService.apply_orientation_edits(
            project_id=project_id,
            orientation_id=orientation_id,
            proposed_state=proposed_state,
            diff_summary=diff_summary,
            diff_data=diff_data,
            user_id=request.user.id,
        )
    except ProjectOrientation.DoesNotExist:
        return Response(
            {'error': 'Orientation not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response({
        'status': 'accepted',
        'orientation_id': str(orientation.id),
        'lens_type': orientation.lens_type,
        'lead_text': orientation.lead_text,
    })
