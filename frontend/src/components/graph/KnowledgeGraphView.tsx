/**
 * Interactive Knowledge Graph Visualization
 * 
 * Displays inquiries, signals, and evidence as an interactive graph.
 * Launched from companion's "View graph" button (focused mode).
 * 
 * TODO: Install reactflow: npm install reactflow
 */

'use client';

import { useEffect, useState, useCallback } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';

interface GraphData {
  nodes: Array<{
    id: string;
    type: string;
    label: string;
    confidence?: number;
    data: any;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    type: string;
    label?: string;
    strength?: number;
  }>;
  stats: {
    total_nodes: number;
    total_edges: number;
    inquiries: number;
    signals: number;
    evidence: number;
  };
}

interface KnowledgeGraphViewProps {
  caseId: string;
  onClose: () => void;
}

export function KnowledgeGraphView({ caseId, onClose }: KnowledgeGraphViewProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [filter, setFilter] = useState<'all' | 'inquiries' | 'contradictions'>('all');

  // Fetch graph data
  useEffect(() => {
    async function fetchGraph() {
      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        const response = await fetch(
          `${backendUrl}/api/knowledge-graph/case/${caseId}/`,
          { credentials: 'include' }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch graph data');
        }

        const data: GraphData = await response.json();
        setGraphData(data);

        // Convert to ReactFlow format
        const flowNodes: Node[] = data.nodes.map((node) => ({
          id: node.id,
          type: 'custom',
          position: { x: 0, y: 0 }, // Will be auto-laid out
          data: {
            ...node.data,
            label: node.label,
            nodeType: node.type,
            confidence: node.confidence
          },
          style: getNodeStyle(node.type)
        }));

        const flowEdges: Edge[] = data.edges.map((edge) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: 'smoothstep',
          label: edge.label,
          animated: edge.type === 'contradicts',
          markerEnd: {
            type: MarkerType.ArrowClosed,
          },
          style: getEdgeStyle(edge.type)
        }));

        // Auto-layout using dagre
        const layoutedNodes = autoLayout(flowNodes, flowEdges);
        setNodes(layoutedNodes);
        setEdges(flowEdges);
        setIsLoading(false);

      } catch (err) {
        console.error('Failed to load graph:', err);
        setError(err instanceof Error ? err.message : 'Failed to load graph');
        setIsLoading(false);
      }
    }

    fetchGraph();
  }, [caseId, setNodes, setEdges]);

  // Filter logic
  useEffect(() => {
    if (!graphData) return;

    let filteredNodes = graphData.nodes;
    let filteredEdges = graphData.edges;

    if (filter === 'inquiries') {
      filteredNodes = graphData.nodes.filter(n => n.type === 'inquiry');
      filteredEdges = graphData.edges.filter(e =>
        e.source.startsWith('inquiry-') || e.target.startsWith('inquiry-')
      );
    } else if (filter === 'contradictions') {
      filteredEdges = graphData.edges.filter(e => e.type === 'contradicts');
      const contradictionNodeIds = new Set([
        ...filteredEdges.map(e => e.source),
        ...filteredEdges.map(e => e.target)
      ]);
      filteredNodes = graphData.nodes.filter(n => contradictionNodeIds.has(n.id));
    }

    const flowNodes: Node[] = filteredNodes.map((node) => ({
      id: node.id,
      type: 'custom',
      position: { x: 0, y: 0 },
      data: {
        ...node.data,
        label: node.label,
        nodeType: node.type,
        confidence: node.confidence
      },
      style: getNodeStyle(node.type)
    }));

    const flowEdges: Edge[] = filteredEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      label: edge.label,
      animated: edge.type === 'contradicts',
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle(edge.type)
    }));

    const layoutedNodes = autoLayout(flowNodes, flowEdges);
    setNodes(layoutedNodes);
    setEdges(flowEdges);
  }, [filter, graphData, setNodes, setEdges]);

  if (isLoading) {
    return (
      <GraphModal onClose={onClose}>
        <div className="flex items-center justify-center h-full">
          <div className="text-neutral-600 dark:text-neutral-400">
            Loading knowledge graph...
          </div>
        </div>
      </GraphModal>
    );
  }

  if (error) {
    return (
      <GraphModal onClose={onClose}>
        <div className="flex items-center justify-center h-full">
          <div className="text-error-600">{error}</div>
        </div>
      </GraphModal>
    );
  }

  return (
    <GraphModal onClose={onClose}>
      <div className="h-full w-full">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
        >
          <Background />
          <Controls />
          
          <Panel position="top-right" className="bg-white dark:bg-neutral-900 rounded-lg shadow-lg p-4 space-y-2">
            <div className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
              Filters
            </div>
            <div className="space-y-1">
              <FilterButton
                active={filter === 'all'}
                onClick={() => setFilter('all')}
                label="All"
              />
              <FilterButton
                active={filter === 'inquiries'}
                onClick={() => setFilter('inquiries')}
                label="Inquiries Only"
              />
              <FilterButton
                active={filter === 'contradictions'}
                onClick={() => setFilter('contradictions')}
                label="Contradictions"
              />
            </div>
            
            {graphData && (
              <div className="pt-2 border-t border-neutral-200 dark:border-neutral-800 text-xs text-neutral-600 dark:text-neutral-400 space-y-1">
                <div>{graphData.stats.inquiries} inquiries</div>
                <div>{graphData.stats.signals} signals</div>
                <div>{graphData.stats.evidence} evidence</div>
              </div>
            )}
          </Panel>
        </ReactFlow>
      </div>
    </GraphModal>
  );
}

function GraphModal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm">
      <div className="absolute inset-4 bg-white dark:bg-neutral-900 rounded-lg shadow-2xl overflow-hidden">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 px-3 py-1.5 text-sm bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded transition-colors"
        >
          Close
        </button>
        {children}
      </div>
    </div>
  );
}

function FilterButton({ 
  active, 
  onClick, 
  label 
}: { 
  active: boolean; 
  onClick: () => void; 
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-2 py-1 text-xs rounded transition-colors ${
        active
          ? 'bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 font-medium'
          : 'hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-600 dark:text-neutral-400'
      }`}
    >
      {label}
    </button>
  );
}

function getNodeStyle(type: string) {
  const baseStyle = {
    padding: '12px',
    borderRadius: '8px',
    fontSize: '12px',
    border: '2px solid',
  };

  switch (type) {
    case 'inquiry':
      return {
        ...baseStyle,
        width: 200,
        background: 'rgb(239 246 255)',
        borderColor: 'rgb(96 165 250)',
        color: 'rgb(30 58 138)'
      };
    case 'signal':
      return {
        ...baseStyle,
        width: 160,
        background: 'rgb(243 244 246)',
        borderColor: 'rgb(156 163 175)',
        color: 'rgb(55 65 81)'
      };
    case 'evidence':
      return {
        ...baseStyle,
        width: 140,
        background: 'rgb(236 253 245)',
        borderColor: 'rgb(52 211 153)',
        color: 'rgb(6 78 59)'
      };
    default:
      return baseStyle;
  }
}

function getEdgeStyle(type: string) {
  switch (type) {
    case 'supports':
      return { stroke: 'rgb(34 197 94)', strokeWidth: 2 };
    case 'contradicts':
      return { stroke: 'rgb(239 68 68)', strokeWidth: 2 };
    case 'depends_on':
      return { stroke: 'rgb(59 130 246)', strokeWidth: 2 };
    default:
      return { stroke: 'rgb(156 163 175)', strokeWidth: 1 };
  }
}

function autoLayout(nodes: Node[], edges: Edge[]): Node[] {
  // Simple grid layout (dagre would be better but requires additional dependency)
  const grid = {
    inquiries: { x: 100, y: 100 },
    signals: { x: 400, y: 100 },
    evidence: { x: 700, y: 100 }
  };

  let yOffsets = { inquiries: 0, signals: 0, evidence: 0 };

  return nodes.map((node) => {
    const nodeType = node.data.nodeType as 'inquiry' | 'signal' | 'evidence';
    
    // Map node types to grid keys
    const gridKey = nodeType === 'inquiry' ? 'inquiries' : nodeType === 'signal' ? 'signals' : 'evidence';
    const offsetKey = nodeType === 'inquiry' ? 'inquiries' : nodeType === 'signal' ? 'signals' : 'evidence';
    
    const x = grid[gridKey].x;
    const y = grid[gridKey].y + yOffsets[offsetKey];

    yOffsets[offsetKey] += 120; // Vertical spacing

    return {
      ...node,
      position: { x, y }
    };
  });
}
