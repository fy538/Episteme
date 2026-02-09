/**
 * GraphCanvas — Main graph visualization component.
 *
 * Wraps React Flow with:
 *   - Custom node types (claim, evidence, assumption, tension, cluster)
 *   - Custom edge types (supports, contradicts, depends_on)
 *   - ELK-powered layout (clustered or layered)
 *   - Zoom-based progressive disclosure
 *   - Cluster click-to-expand
 *   - Edge marker definitions (SVG arrows)
 *   - Node click → detail drawer
 *   - Filter bar + health bar
 */

'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  type NodeTypes,
  type EdgeTypes,
  type Node as FlowNode,
  type Edge as FlowEdge,
  type OnSelectionChangeParams,
  BackgroundVariant,
} from '@xyflow/react';
import { AnimatePresence } from 'framer-motion';
import '@xyflow/react/dist/style.css';

import type { GraphNode, GraphEdge, NodeType, BackendCluster, ClusterQuality } from '@/lib/types/graph';
import { useGraphLayout, type LayoutMode, type ClusterInfo } from './useGraphLayout';
import { GraphNodeCard } from './nodes/GraphNodeCard';
import { ClusterNode } from './nodes/ClusterNode';
import { SupportsEdge, ContradictsEdge, DependsOnEdge } from './edges/GraphEdge';
import { NodeDetailDrawer } from './NodeDetailDrawer';
import { GraphFilterBar } from './GraphFilterBar';
import { GraphHealthBar } from './GraphHealthBar';
import { EdgeMarkerDefs } from './EdgeMarkerDefs';
import { ClusterHulls } from './ClusterHulls';

// ── MiniMap color callback (stable reference, avoids re-renders) ──

const MINIMAP_COLORS: Record<string, string> = {
  claim: '#3b82f6',
  evidence: '#10b981',
  assumption: '#f59e0b',
  tension: '#f43f5e',
  cluster: '#94a3b8',
};
const miniMapNodeColor = (node: { type?: string }) => MINIMAP_COLORS[node.type ?? ''] ?? '#94a3b8';

// ── Stable config objects (prevents re-renders from new object references) ──

const FIT_VIEW_OPTIONS = { padding: 0.2, duration: 400 } as const;
const DEFAULT_EDGE_OPTIONS = { type: 'supports' } as const;
const PRO_OPTIONS = { hideAttribution: true } as const;

// ── Node + Edge type registrations ───────────────────────────

const nodeTypes: NodeTypes = {
  claim: GraphNodeCard,
  evidence: GraphNodeCard,
  assumption: GraphNodeCard,
  tension: GraphNodeCard,
  cluster: ClusterNode,
};

const edgeTypes: EdgeTypes = {
  supports: SupportsEdge,
  contradicts: ContradictsEdge,
  depends_on: DependsOnEdge,
};

// ── Props ────────────────────────────────────────────────────

interface GraphCanvasProps {
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];
  projectId: string;
  caseId?: string;
  /** Initial layout mode */
  layoutMode?: LayoutMode;
  /** When set, scroll to and highlight this node (e.g. from summary citation click) */
  focusedNodeId?: string | null;
  /** Backend-computed clusters for Leiden-based layout */
  backendClusters?: BackendCluster[];
  /** Cluster quality metrics from backend */
  clusterQuality?: ClusterQuality;
  className?: string;
}

export function GraphCanvas(props: GraphCanvasProps) {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner {...props} />
    </ReactFlowProvider>
  );
}

// ── Inner component (needs ReactFlowProvider) ────────────────

function GraphCanvasInner({
  graphNodes,
  graphEdges,
  projectId,
  caseId,
  layoutMode: initialMode = 'clustered',
  focusedNodeId,
  backendClusters,
  clusterQuality,
  className,
}: GraphCanvasProps) {
  const [layoutMode, setLayoutMode] = useState<LayoutMode>(initialMode);
  const [visibleTypes, setVisibleTypes] = useState<NodeType[] | undefined>(undefined);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [showClusters, setShowClusters] = useState(initialMode === 'clustered');
  const [collapsedClusterIds, setCollapsedClusterIds] = useState<Set<string>>(new Set());
  const { fitView, setCenter, zoomTo } = useReactFlow();

  // Sync collapsed state when backend clusters change (e.g. resolution change)
  useEffect(() => {
    if (!backendClusters) {
      setCollapsedClusterIds(new Set());
      return;
    }
    const collapsed = new Set<string>();
    for (const bc of backendClusters) {
      if (bc.node_ids.length >= 8) {
        collapsed.add(bc.centroid_node_id);
      }
    }
    setCollapsedClusterIds(collapsed);
  }, [backendClusters]);

  // Toggle collapse for a cluster
  const handleToggleCollapse = useCallback((clusterId: string) => {
    setCollapsedClusterIds(prev => {
      const next = new Set(prev);
      if (next.has(clusterId)) {
        next.delete(clusterId);
      } else {
        next.add(clusterId);
      }
      return next;
    });
  }, []);

  // Compute layout — thread backend clusters for Leiden-based grouping
  const { nodes: layoutNodes, edges: layoutEdges, clusters, isLayouting } = useGraphLayout(
    graphNodes,
    graphEdges,
    {
      mode: layoutMode,
      visibleTypes,
      backendClusters,
      collapsedClusterIds: layoutMode === 'clustered' ? collapsedClusterIds : undefined,
      onToggleCollapse: handleToggleCollapse,
    }
  );

  // React Flow state — initialized empty, synced via useEffect
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<FlowEdge>([]);

  // Sync layout results into React Flow state
  useEffect(() => {
    setNodes(layoutNodes);
    setEdges(layoutEdges);
  }, [layoutNodes, layoutEdges, setNodes, setEdges]);

  // Focus a specific node (e.g. from summary citation click)
  useEffect(() => {
    if (!focusedNodeId || isLayouting) return;
    const targetNode = layoutNodes.find(n => n.id === focusedNodeId);
    if (targetNode?.position) {
      // Small delay to ensure layout is rendered before scrolling
      const timer = setTimeout(() => {
        setCenter(
          targetNode.position.x + 80,
          targetNode.position.y + 40,
          { zoom: 1.5, duration: 600 }
        );
        setSelectedNodeId(focusedNodeId);
        setDrawerOpen(true);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [focusedNodeId, layoutNodes, isLayouting, setCenter]);

  // Node click → open detail drawer, or expand collapsed cluster
  const handleNodeClick = useCallback((_event: React.MouseEvent, node: FlowNode) => {
    if (node.type === 'cluster') {
      // Expand the collapsed cluster
      const clusterId = (node.data as any)?.clusterId;
      if (clusterId) {
        handleToggleCollapse(clusterId);
      }
      return;
    }
    setSelectedNodeId(node.id);
    setDrawerOpen(true);
  }, [handleToggleCollapse]);

  // Selection change
  const handleSelectionChange = useCallback(({ nodes: selectedNodes }: OnSelectionChangeParams) => {
    if (selectedNodes.length === 1) {
      setSelectedNodeId(selectedNodes[0].id);
    } else if (selectedNodes.length === 0) {
      setSelectedNodeId(null);
    }
  }, []);

  // Close drawer
  const handleDrawerClose = useCallback(() => {
    setDrawerOpen(false);
    setSelectedNodeId(null);
  }, []);

  // Filter change
  const handleFilterChange = useCallback((types: NodeType[] | undefined) => {
    setVisibleTypes(types);
  }, []);

  // Layout mode toggle
  const handleLayoutToggle = useCallback(() => {
    setLayoutMode(prev => {
      const next = prev === 'clustered' ? 'layered' : 'clustered';
      // Auto-show hulls in clustered mode, auto-hide in layered
      setShowClusters(next === 'clustered');
      return next;
    });
  }, []);

  // Cluster hull toggle
  const handleClusterToggle = useCallback(() => {
    setShowClusters(prev => !prev);
  }, []);

  // Navigate to a neighbor node from the drawer
  const handleNavigateToNode = useCallback((nodeId: string) => {
    setSelectedNodeId(nodeId);
    const targetNode = nodes.find(n => n.id === nodeId);
    if (targetNode) {
      setCenter(targetNode.position.x, targetNode.position.y, {
        zoom: 1,
        duration: 400,
      });
    }
  }, [nodes, setCenter]);

  // Derive cluster node type counts for hull coloring — keyed by cluster ID
  const clusterNodeTypesMap = useMemo(() => {
    if (!backendClusters) return new Map<string, Record<string, number>>();
    const map = new Map<string, Record<string, number>>();
    for (let i = 0; i < backendClusters.length; i++) {
      const bc = backendClusters[i];
      const clusterId = bc.centroid_node_id || `backend-${i}`;
      map.set(clusterId, bc.node_types ?? {});
    }
    return map;
  }, [backendClusters]);

  // Build ordered array of node_types matching `clusters` order for ClusterHulls
  const clusterNodeTypes = useMemo(() => {
    return clusters.map(c => clusterNodeTypesMap.get(c.id) ?? {});
  }, [clusters, clusterNodeTypesMap]);

  // Derive selected node data — memoized to avoid recomputing on pan/zoom
  const { selectedGraphNode, selectedNodeEdges, neighborNodes } = useMemo(() => {
    if (!selectedNodeId) return { selectedGraphNode: null, selectedNodeEdges: [], neighborNodes: [] };

    const node = graphNodes.find(n => n.id === selectedNodeId) ?? null;
    const nodeEdges = graphEdges.filter(e => e.source_node === selectedNodeId || e.target_node === selectedNodeId);
    const neighborIds = new Set(
      nodeEdges.flatMap(e => [e.source_node, e.target_node]).filter(id => id !== selectedNodeId)
    );
    const neighbors = graphNodes.filter(n => neighborIds.has(n.id));

    return { selectedGraphNode: node, selectedNodeEdges: nodeEdges, neighborNodes: neighbors };
  }, [selectedNodeId, graphNodes, graphEdges]);

  return (
    <div className={`relative flex h-full w-full ${className ?? ''}`}>
      {/* Main graph area */}
      <div className="flex-1 relative">
        {/* Health bar */}
        <GraphHealthBar nodes={graphNodes} clusterQuality={clusterQuality} className="absolute top-3 left-3 z-10" />

        {/* Filter bar */}
        <GraphFilterBar
          nodes={graphNodes}
          activeTypes={visibleTypes}
          onFilterChange={handleFilterChange}
          layoutMode={layoutMode}
          onLayoutToggle={handleLayoutToggle}
          showClusters={showClusters}
          onClusterToggle={handleClusterToggle}
          className="absolute top-3 right-3 z-10"
        />

        {/* Loading overlay */}
        {isLayouting && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/50 dark:bg-neutral-950/50 backdrop-blur-sm">
            <div className="flex items-center gap-2 text-sm text-neutral-500">
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                <path d="M12 2a10 10 0 019.17 6" strokeLinecap="round" />
              </svg>
              Computing layout...
            </div>
          </div>
        )}

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          onSelectionChange={handleSelectionChange}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={FIT_VIEW_OPTIONS}
          minZoom={0.1}
          maxZoom={2}
          defaultEdgeOptions={DEFAULT_EDGE_OPTIONS}
          proOptions={PRO_OPTIONS}
          colorMode="system"
        >
          <EdgeMarkerDefs />
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--xy-background-pattern-dots-color-default, #ddd)" />
          {showClusters && layoutMode === 'clustered' && clusters.length > 0 && (
            <ClusterHulls clusters={clusters} nodes={nodes} clusterNodeTypes={clusterNodeTypes} />
          )}
          <Controls
            showInteractive={false}
            className="!bg-white dark:!bg-neutral-800 !border-neutral-200 dark:!border-neutral-700 !shadow-sm"
          />
          <MiniMap
            nodeColor={miniMapNodeColor}
            maskColor="rgba(0,0,0,0.08)"
            className="!bg-white dark:!bg-neutral-800 !border-neutral-200 dark:!border-neutral-700"
          />
        </ReactFlow>
      </div>

      {/* Node detail drawer */}
      <AnimatePresence>
        {drawerOpen && selectedGraphNode && (
          <NodeDetailDrawer
            node={selectedGraphNode}
            edges={selectedNodeEdges}
            neighbors={neighborNodes}
            projectId={projectId}
            onClose={handleDrawerClose}
            onNavigateToNode={handleNavigateToNode}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
