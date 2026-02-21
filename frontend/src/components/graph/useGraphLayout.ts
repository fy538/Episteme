/**
 * useGraphLayout — Computes node positions using ELKjs.
 *
 * Transforms GraphNode[] + GraphEdge[] into positioned React Flow nodes.
 * Supports two layout modes:
 *   - 'clustered': Groups nodes using backend clusters (preferred) or local
 *                  importance-based fallback
 *   - 'layered':   Top-down hierarchy (decision tree view)
 *
 * ELK runs async (web worker compatible) so layout never blocks the UI.
 */

'use client';

import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react';
import type { ElkNode, ElkExtendedEdge } from 'elkjs';
import type { Node as FlowNode, Edge as FlowEdge } from '@xyflow/react';
import type { GraphNode, GraphEdge, NodeType, BackendCluster } from '@/lib/types/graph';
import { NODE_DIMENSIONS, EDGE_TYPE_CONFIG, CLUSTER_CONFIG } from './graph-config';

// ── Types ────────────────────────────────────────────────────

export type LayoutMode = 'clustered' | 'layered';

export interface LayoutOptions {
  mode: LayoutMode;
  /** Filter to specific node types */
  visibleTypes?: NodeType[];
  /** Minimum importance to show (1-3) */
  minImportance?: number;
  /** Backend-computed clusters — used instead of local clustering when provided */
  backendClusters?: BackendCluster[];
  /** Cluster IDs that are currently collapsed into super-nodes */
  collapsedClusterIds?: Set<string>;
  /** Callback to toggle collapse on a cluster (threaded into super-node data) */
  onToggleCollapse?: (clusterId: string) => void;
}

interface LayoutState {
  nodes: FlowNode[];
  edges: FlowEdge[];
  clusters: ClusterInfo[];
  isLayouting: boolean;
}

export interface ClusterInfo {
  id: string;
  label: string;
  anchorNodeId: string;
  nodeIds: string[];
  bounds: { x: number; y: number; width: number; height: number };
}

// ── Lazy ELK instance (loaded on first layout) ──────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let elkInstance: any = null;

async function getElk() {
  if (!elkInstance) {
    // Dynamic import — ELK (~130KB) is only loaded when graph view is opened.
    const ELK = (await import('elkjs/lib/elk.bundled.js')).default;
    elkInstance = new ELK();
  }
  return elkInstance as { layout: (graph: ElkNode) => Promise<ElkNode> };
}

// ── Reducer for batched state updates ────────────────────────

type LayoutAction =
  | { type: 'LAYOUT_START' }
  | { type: 'LAYOUT_COMPLETE'; nodes: FlowNode[]; edges: FlowEdge[]; clusters: ClusterInfo[] }
  | { type: 'LAYOUT_CLEAR' }
  | { type: 'LAYOUT_ERROR' };

const initialState: LayoutState = { nodes: [], edges: [], clusters: [], isLayouting: false };

function layoutReducer(state: LayoutState, action: LayoutAction): LayoutState {
  switch (action.type) {
    case 'LAYOUT_START':
      return { ...state, isLayouting: true };
    case 'LAYOUT_COMPLETE':
      return { nodes: action.nodes, edges: action.edges, clusters: action.clusters, isLayouting: false };
    case 'LAYOUT_CLEAR':
      return initialState;
    case 'LAYOUT_ERROR':
      return { ...state, isLayouting: false };
    default:
      return state;
  }
}

// ── Hook ─────────────────────────────────────────────────────

export function useGraphLayout(
  graphNodes: GraphNode[],
  graphEdges: GraphEdge[],
  options: LayoutOptions = { mode: 'clustered' }
): LayoutState {
  const [state, dispatch] = useReducer(layoutReducer, initialState);
  const layoutIdRef = useRef(0);

  // Stabilize options to prevent unnecessary recomputation
  const mode = options.mode;
  const visibleTypes = options.visibleTypes;
  const minImportance = options.minImportance;
  const backendClusters = options.backendClusters;
  const collapsedClusterIds = options.collapsedClusterIds;
  const onToggleCollapse = options.onToggleCollapse;
  const visibleTypesKey = useMemo(
    () => visibleTypes ? visibleTypes.slice().sort().join(',') : 'all',
    [visibleTypes]
  );
  const backendClustersKey = useMemo(
    () => backendClusters ? backendClusters.length.toString() : 'none',
    [backendClusters]
  );
  const collapsedKey = useMemo(
    () => collapsedClusterIds ? [...collapsedClusterIds].sort().join(',') : 'none',
    [collapsedClusterIds]
  );

  const computeLayout = useCallback(async () => {
    if (graphNodes.length === 0) {
      dispatch({ type: 'LAYOUT_CLEAR' });
      return;
    }

    const layoutId = ++layoutIdRef.current;
    dispatch({ type: 'LAYOUT_START' });

    try {
      // Filter nodes by visibility
      const filteredNodes = graphNodes.filter(n => {
        if (visibleTypes && !visibleTypes.includes(n.node_type)) return false;
        const importance = n.properties?.importance ?? 1;
        if (minImportance && importance < minImportance) return false;
        return true;
      });

      const visibleIds = new Set(filteredNodes.map(n => n.id));

      // Filter edges to only connect visible nodes
      const filteredEdges = graphEdges.filter(
        e => visibleIds.has(e.source_node) && visibleIds.has(e.target_node)
      );

      let elkGraph: ElkNode;

      if (mode === 'clustered') {
        elkGraph = buildClusteredGraph(filteredNodes, filteredEdges, backendClusters, visibleIds, collapsedClusterIds);
      } else {
        elkGraph = buildLayeredGraph(filteredNodes, filteredEdges);
      }

      const elk = await getElk();
      const layoutResult = await elk.layout(elkGraph);

      // Bail if a newer layout was requested
      if (layoutId !== layoutIdRef.current) return;

      const { nodes: positioned, edges: positionedEdges, clusterInfos } =
        extractPositions(layoutResult, filteredNodes, filteredEdges, mode, backendClusters, collapsedClusterIds, onToggleCollapse);

      // Single dispatch → single render (batched via useReducer)
      dispatch({ type: 'LAYOUT_COMPLETE', nodes: positioned, edges: positionedEdges, clusters: clusterInfos });
    } catch (err) {
      console.error('[useGraphLayout] Layout failed:', err);
      if (layoutId === layoutIdRef.current) {
        dispatch({ type: 'LAYOUT_ERROR' });
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphNodes, graphEdges, mode, visibleTypesKey, minImportance, backendClustersKey, collapsedKey]);

  useEffect(() => {
    computeLayout();
  }, [computeLayout]);

  return state;
}

// ── Build ELK graphs ────────────────────────────────────────

function buildClusteredGraph(
  nodes: GraphNode[],
  edges: GraphEdge[],
  backendClusters?: BackendCluster[],
  visibleIds?: Set<string>,
  collapsedClusterIds?: Set<string>,
): ElkNode {
  // Use backend clusters when available, fall back to local clustering
  const clusterMap = backendClusters && backendClusters.length > 0
    ? convertBackendClusters(backendClusters, nodes, visibleIds)
    : buildLocalClusters(nodes, edges);

  const nodeById = new Map(nodes.map(n => [n.id, n]));

  // Build a reverse lookup: nodeId -> clusterId (O(1) per lookup)
  const nodeToCluster = new Map<string, string>();
  for (const [clusterId, cluster] of clusterMap) {
    for (const nodeId of cluster.nodeIds) {
      nodeToCluster.set(nodeId, clusterId);
    }
  }

  // Pre-build summary lookup for O(1) height decisions
  const clusterSummaryMap = new Map<string, boolean>();
  if (backendClusters) {
    for (let i = 0; i < backendClusters.length; i++) {
      const bc = backendClusters[i];
      const cid = bc.centroid_node_id || `backend-${i}`;
      if (bc.summary) clusterSummaryMap.set(cid, true);
    }
  }

  const children: ElkNode[] = [];

  for (const [clusterId, cluster] of clusterMap) {
    const isCollapsed = collapsedClusterIds?.has(clusterId) ?? false;

    if (isCollapsed) {
      // Collapsed cluster → single super-node
      const nodeCount = cluster.nodeIds.length;
      const width = Math.min(300, 180 + Math.min(nodeCount, 20) * 4);
      const hasSummary = clusterSummaryMap.has(clusterId);
      children.push({
        id: `cluster-${clusterId}`,
        width,
        height: hasSummary ? CLUSTER_CONFIG.superNodeSummaryHeight : CLUSTER_CONFIG.superNodeMinHeight,
      });
    } else {
      // Expanded cluster → sub-graph with children
      const clusterNodeSet = new Set(cluster.nodeIds);
      const clusterChildren: ElkNode[] = cluster.nodeIds.map(nodeId => {
        const node = nodeById.get(nodeId)!;
        const dims = getNodeDimensions(node);
        return {
          id: nodeId,
          width: dims.width,
          height: dims.height,
        };
      });

      // Edges within this cluster — O(1) membership check via Set
      const intraEdges: ElkExtendedEdge[] = edges
        .filter(e => clusterNodeSet.has(e.source_node) && clusterNodeSet.has(e.target_node))
        .map(e => ({
          id: e.id,
          sources: [e.source_node],
          targets: [e.target_node],
        }));

      children.push({
        id: `cluster-${clusterId}`,
        layoutOptions: {
          'elk.algorithm': 'force',
          'elk.force.iterations': '100',
          'elk.padding': '[top=40,left=24,bottom=24,right=24]',
          'elk.spacing.nodeNode': '30',
        },
        children: clusterChildren,
        edges: intraEdges,
      });
    }
  }

  // Inter-cluster edges — reroute to super-node for collapsed clusters
  const interEdges: ElkExtendedEdge[] = [];
  const seenEdgePairs = new Set<string>();

  for (const e of edges) {
    const sourceCluster = nodeToCluster.get(e.source_node);
    const targetCluster = nodeToCluster.get(e.target_node);
    if (!sourceCluster || !targetCluster || sourceCluster === targetCluster) continue;

    // For collapsed clusters, reroute to the super-node
    const sourceCollapsed = collapsedClusterIds?.has(sourceCluster) ?? false;
    const targetCollapsed = collapsedClusterIds?.has(targetCluster) ?? false;

    const source = sourceCollapsed ? `cluster-${sourceCluster}` : e.source_node;
    const target = targetCollapsed ? `cluster-${targetCluster}` : e.target_node;

    // Deduplicate edges between same super-node pair
    const pairKey = `${source}:${target}`;
    if (seenEdgePairs.has(pairKey)) continue;
    seenEdgePairs.add(pairKey);

    interEdges.push({
      id: `agg-${e.id}`,
      sources: [source],
      targets: [target],
    });
  }

  return {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'force',
      'elk.force.iterations': '200',
      'elk.spacing.nodeNode': '60',
      'elk.spacing.componentComponent': '80',
    },
    children,
    edges: interEdges,
  };
}

function buildLayeredGraph(nodes: GraphNode[], edges: GraphEdge[]): ElkNode {
  const children: ElkNode[] = nodes.map(node => {
    const dims = getNodeDimensions(node);
    return {
      id: node.id,
      width: dims.width,
      height: dims.height,
    };
  });

  const elkEdges: ElkExtendedEdge[] = edges.map(e => ({
    id: e.id,
    sources: [e.source_node],
    targets: [e.target_node],
  }));

  return {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'DOWN',
      'elk.layered.spacing.nodeNodeBetweenLayers': '80',
      'elk.spacing.nodeNode': '40',
      'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
      'elk.edgeRouting': 'SPLINES',
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
    },
    children,
    edges: elkEdges,
  };
}

// ── Clustering logic ─────────────────────────────────────────

interface ClusterDraft {
  anchorId: string;
  anchorLabel: string;
  nodeIds: string[];
}

/**
 * Convert backend clusters into the ClusterDraft format used by ELK layout.
 * Filters to only include visible nodes and drops empty clusters.
 */
function convertBackendClusters(
  backendClusters: BackendCluster[],
  nodes: GraphNode[],
  visibleIds?: Set<string>,
): Map<string, ClusterDraft> {
  const clusters = new Map<string, ClusterDraft>();
  const assigned = new Set<string>();

  for (let i = 0; i < backendClusters.length; i++) {
    const bc = backendClusters[i];
    // Filter to only visible nodes
    const nodeIds = visibleIds
      ? bc.node_ids.filter(id => visibleIds.has(id))
      : bc.node_ids;

    if (nodeIds.length === 0) continue;

    const clusterId = bc.centroid_node_id || `backend-${i}`;
    clusters.set(clusterId, {
      anchorId: bc.centroid_node_id,
      anchorLabel: bc.label ?? `Cluster ${i + 1}`,
      nodeIds,
    });

    for (const id of nodeIds) {
      assigned.add(id);
    }
  }

  // Any visible nodes not in a backend cluster go into "unclustered"
  const unassigned = nodes.filter(n => !assigned.has(n.id));
  if (unassigned.length > 0) {
    clusters.set('unclustered', {
      anchorId: 'unclustered',
      anchorLabel: 'Other',
      nodeIds: unassigned.map(n => n.id),
    });
  }

  return clusters;
}

/**
 * Local fallback clustering: group nodes around high-importance claims.
 * Used when backend clusters are unavailable.
 */
function buildLocalClusters(
  nodes: GraphNode[],
  edges: GraphEdge[]
): Map<string, ClusterDraft> {
  const clusters = new Map<string, ClusterDraft>();
  const assigned = new Set<string>();

  // Claims with importance >= 2 become cluster anchors
  const anchors = nodes
    .filter(n => n.node_type === 'claim' && (n.properties?.importance ?? 1) >= 2)
    .sort((a, b) => (b.properties?.importance ?? 1) - (a.properties?.importance ?? 1));

  for (const anchor of anchors) {
    const cluster: ClusterDraft = {
      anchorId: anchor.id,
      anchorLabel: anchor.content.slice(0, 60),
      nodeIds: [anchor.id],
    };
    assigned.add(anchor.id);

    // Find nodes connected to this anchor via supports/depends_on
    for (const edge of edges) {
      if (edge.edge_type === 'contradicts') continue;

      let connectedId: string | null = null;
      if (edge.target_node === anchor.id && !assigned.has(edge.source_node)) {
        connectedId = edge.source_node;
      } else if (edge.source_node === anchor.id && !assigned.has(edge.target_node)) {
        connectedId = edge.target_node;
      }

      if (connectedId) {
        cluster.nodeIds.push(connectedId);
        assigned.add(connectedId);
      }
    }

    clusters.set(anchor.id, cluster);
  }

  // Unassigned nodes go into an "unclustered" group
  const unassigned = nodes.filter(n => !assigned.has(n.id));
  if (unassigned.length > 0) {
    clusters.set('unclustered', {
      anchorId: 'unclustered',
      anchorLabel: 'Other',
      nodeIds: unassigned.map(n => n.id),
    });
  }

  return clusters;
}

// ── Extract positions from ELK result ────────────────────────

function extractPositions(
  elkResult: ElkNode,
  originalNodes: GraphNode[],
  originalEdges: GraphEdge[],
  mode: LayoutMode,
  backendClusters?: BackendCluster[],
  collapsedClusterIds?: Set<string>,
  onToggleCollapse?: (clusterId: string) => void,
): {
  nodes: FlowNode[];
  edges: FlowEdge[];
  clusterInfos: ClusterInfo[];
} {
  const nodeMap = new Map(originalNodes.map(n => [n.id, n]));
  const positionedNodes: FlowNode[] = [];
  const clusterInfos: ClusterInfo[] = [];

  // Build label + type-counts + summary lookup from backend clusters
  const clusterLabelLookup = new Map<string, string>();
  const clusterTypeCounts = new Map<string, Record<string, number>>();
  const clusterNodeIds = new Map<string, string[]>();
  const clusterSummaryLookup = new Map<string, string>();
  if (backendClusters) {
    for (let i = 0; i < backendClusters.length; i++) {
      const bc = backendClusters[i];
      const clusterId = bc.centroid_node_id || `backend-${i}`;
      clusterLabelLookup.set(clusterId, bc.label ?? `Cluster ${i + 1}`);
      clusterTypeCounts.set(clusterId, bc.node_types ?? {});
      clusterNodeIds.set(clusterId, bc.node_ids);
      if (bc.summary) {
        clusterSummaryLookup.set(clusterId, bc.summary);
      }
    }
  }

  if (mode === 'clustered') {
    // Nodes are nested inside cluster containers
    for (const clusterElk of elkResult.children ?? []) {
      const clusterId = clusterElk.id.replace('cluster-', '');
      const clusterX = clusterElk.x ?? 0;
      const clusterY = clusterElk.y ?? 0;
      const isCollapsed = collapsedClusterIds?.has(clusterId) ?? false;

      if (isCollapsed) {
        // Collapsed → emit a super-node (type='cluster')
        const label = clusterLabelLookup.get(clusterId) ?? 'Cluster';
        const memberIds = clusterNodeIds.get(clusterId) ?? [];
        const typeCounts = clusterTypeCounts.get(clusterId) ?? {};

        const summary = clusterSummaryLookup.get(clusterId);

        positionedNodes.push({
          id: clusterElk.id,
          type: 'cluster',
          position: { x: clusterX, y: clusterY },
          data: {
            label,
            summary,
            nodeCount: memberIds.length,
            typeCounts,
            clusterId,
            isCollapsed: true,
            onToggleCollapse,
          },
        });

        clusterInfos.push({
          id: clusterId,
          label,
          anchorNodeId: clusterId,
          nodeIds: memberIds,
          bounds: {
            x: clusterX,
            y: clusterY,
            width: clusterElk.width ?? 200,
            height: clusterElk.height ?? 120,
          },
        });
      } else {
        // Expanded → emit individual nodes
        const nodeIds: string[] = [];

        for (const elkNode of clusterElk.children ?? []) {
          const graphNode = nodeMap.get(elkNode.id);
          if (!graphNode) continue;

          nodeIds.push(elkNode.id);
          positionedNodes.push({
            id: elkNode.id,
            type: graphNode.node_type,
            position: {
              x: clusterX + (elkNode.x ?? 0),
              y: clusterY + (elkNode.y ?? 0),
            },
            data: { graphNode },
          });
        }

        if (nodeIds.length > 0) {
          const label = clusterLabelLookup.get(clusterId)
            ?? nodeMap.get(clusterId)?.content.slice(0, 60)
            ?? 'Other';

          clusterInfos.push({
            id: clusterId,
            label,
            anchorNodeId: clusterId,
            nodeIds,
            bounds: {
              x: clusterX,
              y: clusterY,
              width: clusterElk.width ?? 300,
              height: clusterElk.height ?? 200,
            },
          });
        }
      }
    }
  } else {
    // Flat layered — nodes at root level
    for (const elkNode of elkResult.children ?? []) {
      const graphNode = nodeMap.get(elkNode.id);
      if (!graphNode) continue;

      positionedNodes.push({
        id: elkNode.id,
        type: graphNode.node_type,
        position: {
          x: elkNode.x ?? 0,
          y: elkNode.y ?? 0,
        },
        data: { graphNode },
      });
    }
  }

  // Convert edges — use Set for O(1) endpoint checks
  const positionedNodeIds = new Set(positionedNodes.map(n => n.id));
  const positionedEdges: FlowEdge[] = originalEdges
    .filter(e => positionedNodeIds.has(e.source_node) && positionedNodeIds.has(e.target_node))
    .map(e => {
      const config = EDGE_TYPE_CONFIG[e.edge_type];
      return {
        id: e.id,
        source: e.source_node,
        target: e.target_node,
        type: e.edge_type,
        data: { graphEdge: e },
        style: {
          stroke: config.strokeColor,
          strokeWidth: Math.max(1, (e.strength ?? 0.5) * 3),
          strokeDasharray: config.strokeDasharray,
        },
        markerEnd: config.markerEnd,
        animated: config.animated,
      };
    });

  return { nodes: positionedNodes, edges: positionedEdges, clusterInfos };
}

// ── Helpers ──────────────────────────────────────────────────

function getNodeDimensions(node: GraphNode) {
  const importance = node.properties?.importance ?? 1;
  if (importance >= 3) return NODE_DIMENSIONS.detail;
  if (importance >= 2) return NODE_DIMENSIONS.summary;
  return NODE_DIMENSIONS.compact;
}
