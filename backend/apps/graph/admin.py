"""
Graph admin — Node, Edge, GraphDelta, CaseNodeReference.
"""
from django.contrib import admin
from .models import Node, Edge, GraphDelta, CaseNodeReference


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ('content_preview', 'node_type', 'status', 'project', 'scope', 'source_type', 'created_at')
    list_filter = ('node_type', 'status', 'scope', 'source_type')
    search_fields = ('content',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('project', 'case', 'source_document', 'source_message', 'created_by')

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    list_display = ('edge_type', 'source_preview', 'target_preview', 'strength', 'source_type', 'created_at')
    list_filter = ('edge_type', 'source_type')
    raw_id_fields = ('source_node', 'target_node', 'source_document', 'created_by')

    def source_preview(self, obj):
        return obj.source_node.content[:40]
    source_preview.short_description = 'Source'

    def target_preview(self, obj):
        return obj.target_node.content[:40]
    target_preview.short_description = 'Target'


@admin.register(GraphDelta)
class GraphDeltaAdmin(admin.ModelAdmin):
    list_display = ('trigger', 'narrative_preview', 'nodes_created', 'edges_created', 'tensions_surfaced', 'project', 'created_at')
    list_filter = ('trigger',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'patch')
    raw_id_fields = ('project', 'source_document', 'source_message')

    def narrative_preview(self, obj):
        return obj.narrative[:80] + '...' if obj.narrative and len(obj.narrative) > 80 else obj.narrative
    narrative_preview.short_description = 'Narrative'


@admin.register(CaseNodeReference)
class CaseNodeReferenceAdmin(admin.ModelAdmin):
    list_display = ('node_preview', 'case', 'inclusion_type', 'relevance', 'excluded', 'created_at')
    list_filter = ('inclusion_type', 'excluded')
    raw_id_fields = ('case', 'node')

    def node_preview(self, obj):
        return obj.node.content[:60]
    node_preview.short_description = 'Node'
