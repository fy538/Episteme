/**
 * useCanvasLayout - Hook for auto-laying out canvas nodes
 *
 * Uses dagre for hierarchical layout:
 * - Decision at top
 * - Inquiries in rows below
 * - Evidence clusters at bottom
 */

import { useMemo } from 'react';
import dagre from '@dagrejs/dagre';
import { Node, Edge } from 'reactflow';

interface UseCanvasLayoutReturn {
  layoutNodes: Node[];
}

export function useCanvasLayout(
  nodes: Node[],
  edges: Edge[]
): UseCanvasLayoutReturn {
  const layoutNodes = useMemo(() => {
    if (nodes.length === 0) return [];

    // Create dagre graph
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    // Configure layout
    dagreGraph.setGraph({
      rankdir: 'TB', // Top to bottom
      ranksep: 80,   // Vertical spacing
      nodesep: 40,   // Horizontal spacing
      align: 'UL',
    });

    // Add nodes with dimensions
    nodes.forEach((node) => {
      const dimensions = getNodeDimensions(node.type);
      dagreGraph.setNode(node.id, {
        width: dimensions.width,
        height: dimensions.height,
      });
    });

    // Add edges
    edges.forEach((edge) => {
      dagreGraph.setEdge(edge.source, edge.target);
    });

    // Run layout
    dagre.layout(dagreGraph);

    // Apply positions
    return nodes.map((node) => {
      const nodeWithPosition = dagreGraph.node(node.id);

      if (!nodeWithPosition) {
        return node;
      }

      const dimensions = getNodeDimensions(node.type);

      return {
        ...node,
        position: {
          x: nodeWithPosition.x - dimensions.width / 2,
          y: nodeWithPosition.y - dimensions.height / 2,
        },
      };
    });
  }, [nodes, edges]);

  return { layoutNodes };
}

/**
 * Get approximate dimensions for different node types
 */
function getNodeDimensions(type?: string): { width: number; height: number } {
  switch (type) {
    case 'decision':
      return { width: 320, height: 160 };
    case 'inquiry':
      return { width: 200, height: 100 };
    case 'evidence':
      return { width: 120, height: 50 };
    default:
      return { width: 150, height: 80 };
  }
}
