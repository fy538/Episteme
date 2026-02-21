"""
Graph URL routing — v2 API endpoints for the knowledge graph.
"""
from django.urls import path

from . import views
from . import streaming_views

app_name = 'graph'

urlpatterns = [
    # Full graph
    path(
        'projects/<uuid:project_id>/graph/',
        views.project_graph_view,
        name='project-graph',
    ),

    # Full graph with backend-computed clusters
    path(
        'projects/<uuid:project_id>/graph/clustered/',
        views.project_graph_clustered_view,
        name='project-graph-clustered',
    ),

    # Graph deltas (mutation history)
    path(
        'projects/<uuid:project_id>/graph/deltas/',
        views.project_deltas_view,
        name='project-deltas',
    ),

    # Node semantic search
    path(
        'projects/<uuid:project_id>/nodes/search/',
        views.node_search_view,
        name='node-search',
    ),

    # Individual node
    path(
        'projects/<uuid:project_id>/nodes/<uuid:node_id>/',
        views.node_detail_view,
        name='node-detail',
    ),

    # Node update
    path(
        'projects/<uuid:project_id>/nodes/<uuid:node_id>/update/',
        views.node_update_view,
        name='node-update',
    ),

    # Document-specific graph delta
    path(
        'projects/<uuid:project_id>/documents/<uuid:document_id>/graph-delta/',
        views.document_graph_delta_view,
        name='document-graph-delta',
    ),

    # Document argument structure (subgraph)
    path(
        'projects/<uuid:project_id>/documents/<uuid:document_id>/graph/',
        views.document_subgraph_view,
        name='document-subgraph',
    ),

    # ── Case-scoped graph ──────────────────────────────────────
    path(
        'projects/<uuid:project_id>/cases/<uuid:case_id>/graph/',
        views.case_graph_view,
        name='case-graph',
    ),
    path(
        'projects/<uuid:project_id>/cases/<uuid:case_id>/graph/pull/',
        views.case_pull_node_view,
        name='case-pull-node',
    ),
    path(
        'projects/<uuid:project_id>/cases/<uuid:case_id>/graph/exclude/',
        views.case_exclude_node_view,
        name='case-exclude-node',
    ),

    # ── Document scope transitions ─────────────────────────────
    path(
        'projects/<uuid:project_id>/documents/<uuid:document_id>/promote/',
        views.promote_document_view,
        name='document-promote',
    ),
    path(
        'projects/<uuid:project_id>/documents/<uuid:document_id>/demote/',
        views.demote_document_view,
        name='document-demote',
    ),

    # ── Project Summary ──────────────────────────────────────
    path(
        'projects/<uuid:project_id>/summary/',
        views.project_summary_view,
        name='project-summary',
    ),
    path(
        'projects/<uuid:project_id>/summary/regenerate/',
        views.project_summary_regenerate_view,
        name='project-summary-regenerate',
    ),
    path(
        'projects/<uuid:project_id>/summary/stream/',
        streaming_views.summary_generation_stream,
        name='project-summary-stream',
    ),

    # ── Hierarchical Clustering ───────────────────────────────
    path(
        'projects/<uuid:project_id>/hierarchy/',
        views.project_hierarchy_view,
        name='project-hierarchy',
    ),
    path(
        'projects/<uuid:project_id>/hierarchy/rebuild/',
        views.project_hierarchy_rebuild_view,
        name='project-hierarchy-rebuild',
    ),
    path(
        'projects/<uuid:project_id>/hierarchy/search/',
        views.hierarchy_chunk_search_view,
        name='hierarchy-chunk-search',
    ),

    # ── Project Insights ──────────────────────────────────────
    path(
        'projects/<uuid:project_id>/insights/',
        views.project_insights_view,
        name='project-insights',
    ),
    path(
        'projects/<uuid:project_id>/insights/<uuid:insight_id>/',
        views.project_insight_update_view,
        name='project-insight-update',
    ),

    # ── Project Orientation ───────────────────────────────────
    path(
        'projects/<uuid:project_id>/orientation/',
        views.project_orientation_view,
        name='project-orientation',
    ),
    path(
        'projects/<uuid:project_id>/orientation/regenerate/',
        views.project_orientation_regenerate_view,
        name='project-orientation-regenerate',
    ),
    path(
        'projects/<uuid:project_id>/orientation/stream/',
        streaming_views.orientation_generation_stream,
        name='project-orientation-stream',
    ),
    path(
        'projects/<uuid:project_id>/orientation/accept-diff/',
        views.orientation_accept_diff_view,
        name='project-orientation-accept-diff',
    ),

    # ── Insight Actions (orientation exit ramps) ──────────────
    path(
        'projects/<uuid:project_id>/insights/<uuid:insight_id>/generate/',
        views.exploration_angle_generate_view,
        name='insight-generate-angle',
    ),
    path(
        'projects/<uuid:project_id>/insights/<uuid:insight_id>/research/',
        views.research_insight_view,
        name='insight-research',
    ),
]
