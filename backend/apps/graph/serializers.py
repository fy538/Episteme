"""
Graph serializers — DRF serializers for Node, Edge, GraphDelta, and views.
"""
from rest_framework import serializers

from .models import Node, Edge, GraphDelta, CaseNodeReference, ProjectSummary


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

    def get_edges(self, obj):
        """Get all edges connected to this node."""
        from django.db.models import Q
        edges = Edge.objects.filter(
            Q(source_node=obj) | Q(target_node=obj)
        ).select_related('source_node', 'target_node')
        return EdgeSerializer(edges, many=True).data

    def get_neighbors(self, obj):
        """Get 1-hop neighbor nodes."""
        from django.db.models import Q
        edge_qs = Edge.objects.filter(
            Q(source_node=obj) | Q(target_node=obj)
        )
        neighbor_ids = set()
        for edge in edge_qs:
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
