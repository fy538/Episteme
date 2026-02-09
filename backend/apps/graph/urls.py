"""
Graph URL routing — v2 API endpoints for the knowledge graph.
"""
from django.urls import path

from . import views

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
]
