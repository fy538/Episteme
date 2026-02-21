"""
Graph serializers — DRF serializers for Node, Edge, GraphDelta, and views.
"""
from rest_framework import serializers

from .models import (
    Node, Edge, GraphDelta, CaseNodeReference, ProjectSummary,
    ClusterHierarchy, ProjectInsight, ProjectOrientation,
)


class NodeSerializer(serializers.ModelSerializer):
    """Compact node serializer for list views and graph responses."""
    source_document_title = serializers.CharField(
        source='source_document.title', read_only=True, default=None
    )

    class Meta:
        model = Node
        fields = [
            'id',
            'node_type',
            'status',
            'content',
            'properties',
            'project',
            'case',
            'scope',
            'source_type',
            'source_document',
            'source_document_title',
            'confidence',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]


class EdgeSerializer(serializers.ModelSerializer):
    """Edge serializer."""
    source_content = serializers.CharField(
        source='source_node.content', read_only=True
    )
    target_content = serializers.CharField(
        source='target_node.content', read_only=True
    )

    class Meta:
        model = Edge
        fields = [
            'id',
            'edge_type',
            'source_node',
            'target_node',
            'source_content',
            'target_content',
            'strength',
            'provenance',
            'source_type',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class NodeDetailSerializer(serializers.ModelSerializer):
    """Detailed node serializer with connected edges, neighbors, and source chunks."""
    source_document_title = serializers.CharField(
        source='source_document.title', read_only=True, default=None
    )
    edges = serializers.SerializerMethodField()
    neighbors = serializers.SerializerMethodField()
    source_chunks = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = [
            'id',
            'node_type',
            'status',
            'content',
            'properties',
            'project',
            'case',
            'scope',
            'source_type',
            'source_document',
            'source_document_title',
            'source_chunks',
            'confidence',
            'created_at',
            'updated_at',
            'edges',
            'neighbors',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]

    def _get_cached_edges(self, obj):
        """Fetch edges once and cache on the serializer instance."""
        if not hasattr(self, '_edges_cache'):
            from django.db.models import Q
            self._edges_cache = list(
                Edge.objects.filter(
                    Q(source_node=obj) | Q(target_node=obj)
                ).select_related('source_node', 'target_node')
            )
        return self._edges_cache

    def get_edges(self, obj):
        """Get all edges connected to this node."""
        return EdgeSerializer(self._get_cached_edges(obj), many=True).data

    def get_neighbors(self, obj):
        """Get 1-hop neighbor nodes (reuses cached edges — single query)."""
        edges = self._get_cached_edges(obj)
        neighbor_ids = set()
        for edge in edges:
            if edge.source_node_id != obj.id:
                neighbor_ids.add(edge.source_node_id)
            if edge.target_node_id != obj.id:
                neighbor_ids.add(edge.target_node_id)

        neighbors = Node.objects.filter(id__in=neighbor_ids).select_related('source_document')
        return NodeSerializer(neighbors, many=True).data

    def get_source_chunks(self, obj):
        """Return source chunk provenance — the document passages backing this node."""
        chunks = obj.source_chunks.all().order_by('chunk_index').select_related('document')[:5]
        return [
            {
                'id': str(chunk.id),
                'chunk_index': chunk.chunk_index,
                'chunk_text': chunk.chunk_text[:300],
                'document_id': str(chunk.document_id),
                'document_title': chunk.document.title if chunk.document else None,
                'span': chunk.span,
            }
            for chunk in chunks
        ]


class GraphDeltaSerializer(serializers.ModelSerializer):
    """Serializer for GraphDelta — mutation records."""
    source_document_title = serializers.CharField(
        source='source_document.title', read_only=True, default=None
    )

    class Meta:
        model = GraphDelta
        fields = [
            'id',
            'project',
            'trigger',
            'patch',
            'narrative',
            'nodes_created',
            'nodes_updated',
            'edges_created',
            'tensions_surfaced',
            'assumptions_challenged',
            'source_document',
            'source_document_title',
            'source_message',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class NodeUpdateSerializer(serializers.Serializer):
    """Serializer for partial node updates via PATCH."""
    content = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    properties = serializers.DictField(required=False)
    confidence = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)


class CaseNodeReferenceSerializer(serializers.ModelSerializer):
    """Serializer for CaseNodeReference — case-to-project-node through table."""
    node_content = serializers.CharField(source='node.content', read_only=True)
    node_type = serializers.CharField(source='node.node_type', read_only=True)

    class Meta:
        model = CaseNodeReference
        fields = [
            'id',
            'case',
            'node',
            'node_content',
            'node_type',
            'inclusion_type',
            'relevance',
            'excluded',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ProjectSummarySerializer(serializers.ModelSerializer):
    """Serializer for ProjectSummary — AI-generated project narrative."""

    class Meta:
        model = ProjectSummary
        fields = [
            'id',
            'project',
            'status',
            'sections',
            'is_stale',
            'stale_since',
            'generation_metadata',
            'version',
            'clusters',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClusterHierarchySerializer(serializers.ModelSerializer):
    """Serializer for ClusterHierarchy — hierarchical cluster tree."""

    diff_summary = serializers.SerializerMethodField()
    metadata = serializers.SerializerMethodField()

    def get_diff_summary(self, obj) -> str | None:
        """Human-readable summary of changes from the previous hierarchy version (Plan 6)."""
        meta = obj.metadata or {}
        return meta.get('diff_summary', None)

    def get_metadata(self, obj) -> dict:
        """Return metadata without internal-only fields.

        Strips `document_manifest` (used only for backend diff computation)
        to keep the API payload lean. The `diff` object and basic stats
        are preserved for the frontend.
        """
        meta = obj.metadata or {}
        return {
            'total_chunks': meta.get('total_chunks', 0),
            'total_clusters': meta.get('total_clusters', 0),
            'levels': meta.get('levels', 0),
            'duration_ms': meta.get('duration_ms', 0),
            'document_count': meta.get('document_count', 0),
            'diff': meta.get('diff'),
            'diff_summary': meta.get('diff_summary'),
        }

    class Meta:
        model = ClusterHierarchy
        fields = [
            'id',
            'project',
            'version',
            'status',
            'tree',
            'metadata',
            'is_current',
            'diff_summary',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'project', 'version', 'tree', 'metadata', 'is_current', 'diff_summary', 'created_at', 'updated_at']


class ProjectInsightSerializer(serializers.ModelSerializer):
    """Serializer for ProjectInsight — agent-discovered observations."""

    class Meta:
        model = ProjectInsight
        fields = [
            'id',
            'project',
            'insight_type',
            'title',
            'content',
            'source_type',
            'source_cluster_ids',
            'source_case',
            'status',
            'confidence',
            'metadata',
            'orientation',
            'display_order',
            'action_type',
            'linked_thread',
            'research_result',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'project', 'insight_type', 'title', 'content',
            'source_type', 'source_cluster_ids', 'source_case',
            'confidence', 'metadata', 'orientation', 'display_order',
            'action_type', 'linked_thread', 'research_result',
            'created_at', 'updated_at',
        ]


class ProjectOrientationSerializer(serializers.ModelSerializer):
    """Serializer for ProjectOrientation — lens-based project analysis."""

    findings = serializers.SerializerMethodField()

    class Meta:
        model = ProjectOrientation
        fields = [
            'id',
            'project',
            'status',
            'lens_type',
            'lead_text',
            'lens_scores',
            'secondary_lens',
            'secondary_lens_reason',
            'is_current',
            'generation_metadata',
            'findings',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'project', 'status', 'lens_type', 'lead_text',
            'lens_scores', 'secondary_lens', 'secondary_lens_reason',
            'is_current', 'generation_metadata',
            'created_at', 'updated_at',
        ]

    def get_findings(self, obj):
        """Return non-superseded insights ordered by display_order."""
        insights = (
            obj.findings
            .exclude(status='superseded')
            .order_by('display_order')
        )
        return ProjectInsightSerializer(insights, many=True).data
