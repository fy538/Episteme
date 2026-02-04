/**
 * DecisionCanvas - The graph-first view for case exploration
 *
 * Shows the decision as a visual graph with:
 * - Central decision node
 * - Connected inquiry nodes
 * - Evidence clusters
 * - Status indicators (not computed confidence)
 *
 * Philosophy: Show evidence counts and status, not computed scores.
 */

'use client';

import { useCallback, useMemo, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { DecisionNode } from './nodes/DecisionNode';
import { InquiryNode } from './nodes/InquiryNode';
import { EvidenceCluster } from './nodes/EvidenceCluster';
import { CanvasControls } from './CanvasControls';
import { useCanvasLayout } from './useCanvasLayout';
import { useEvidenceLandscape } from '@/hooks/useEvidenceLandscape';
import {
  ChevronDownIcon,
  ChevronUpIcon,
  CheckCircleIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/react/24/outline';
import type { Case, Inquiry } from '@/lib/types/case';

// Custom node types
const nodeTypes = {
  decision: DecisionNode,
  inquiry: InquiryNode,
  evidence: EvidenceCluster,
};

interface Signal {
  id: string;
  signal_type: string;
  content: string;
  inquiry_id?: string;
}

interface DecisionCanvasProps {
  caseData: Case;
  inquiries: Inquiry[];
  signals?: Signal[];
  onInquiryClick: (inquiryId: string) => void;
  onDecisionClick: () => void;
  onAddInquiry: () => void;
  onOpenBrief: () => void;
  onOpenSignals?: () => void;
  onOpenReadiness?: () => void;
}

export function DecisionCanvas({
  caseData,
  inquiries,
  signals = [],
  onInquiryClick,
  onDecisionClick,
  onAddInquiry,
  onOpenBrief,
  onOpenSignals,
  onOpenReadiness,
}: DecisionCanvasProps) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [showEvidencePanel, setShowEvidencePanel] = useState(false);

  // Load evidence landscape (replaces computed confidence/readiness scores)
  const {
    landscape,
    totalEvidence,
    hasContradictions,
    untestedAssumptionCount,
    openInquiryCount,
    isLoading: landscapeLoading,
  } = useEvidenceLandscape({ caseId: caseData.id, autoRefresh: true, refreshInterval: 30000 });

  // Build nodes and edges from data
  const { initialNodes, initialEdges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Central decision node
    nodes.push({
      id: 'decision',
      type: 'decision',
      position: { x: 400, y: 50 },
      data: {
        title: caseData.decision_question || caseData.title,
        userConfidence: caseData.user_confidence, // User's self-stated confidence
        status: caseData.status,
        onClick: onDecisionClick,
      },
    });

    // Inquiry nodes
    const openInquiries = inquiries.filter(i => i.status !== 'resolved');
    const resolvedInquiries = inquiries.filter(i => i.status === 'resolved');

    // Position open inquiries in a row below decision
    openInquiries.forEach((inquiry, idx) => {
      const xOffset = (idx - (openInquiries.length - 1) / 2) * 220;

      nodes.push({
        id: `inquiry-${inquiry.id}`,
        type: 'inquiry',
        position: { x: 400 + xOffset, y: 200 },
        data: {
          inquiry,
          onClick: () => onInquiryClick(inquiry.id),
          isBlocked: (inquiry.blocked_by?.length ?? 0) > 0,
        },
      });

      // Edge from decision to inquiry
      edges.push({
        id: `edge-decision-${inquiry.id}`,
        source: 'decision',
        target: `inquiry-${inquiry.id}`,
        type: 'smoothstep',
        animated: inquiry.status === 'investigating',
        style: {
          stroke: getStatusColor(inquiry.status),
          strokeWidth: 2,
        },
      });
    });

    // Resolved inquiries in a lower row
    resolvedInquiries.forEach((inquiry, idx) => {
      const xOffset = (idx - (resolvedInquiries.length - 1) / 2) * 220;

      nodes.push({
        id: `inquiry-${inquiry.id}`,
        type: 'inquiry',
        position: { x: 400 + xOffset, y: 380 },
        data: {
          inquiry,
          onClick: () => onInquiryClick(inquiry.id),
          isResolved: true,
        },
      });

      edges.push({
        id: `edge-decision-${inquiry.id}`,
        source: 'decision',
        target: `inquiry-${inquiry.id}`,
        type: 'smoothstep',
        style: {
          stroke: '#22c55e',
          strokeWidth: 2,
        },
      });
    });

    // Evidence clusters (grouped by inquiry)
    const signalsByInquiry = signals.reduce((acc, signal) => {
      const key = signal.inquiry_id || 'unlinked';
      if (!acc[key]) acc[key] = [];
      acc[key].push(signal);
      return acc;
    }, {} as Record<string, Signal[]>);

    Object.entries(signalsByInquiry).forEach(([inquiryId, inquirySignals]) => {
      if (inquiryId === 'unlinked') return;

      const parentNode = nodes.find(n => n.id === `inquiry-${inquiryId}`);
      if (!parentNode) return;

      nodes.push({
        id: `evidence-${inquiryId}`,
        type: 'evidence',
        position: {
          x: parentNode.position.x,
          y: parentNode.position.y + 120,
        },
        data: {
          signals: inquirySignals,
          inquiryId,
        },
      });

      edges.push({
        id: `edge-evidence-${inquiryId}`,
        source: `inquiry-${inquiryId}`,
        target: `evidence-${inquiryId}`,
        type: 'smoothstep',
        style: {
          stroke: '#94a3b8',
          strokeWidth: 1,
          strokeDasharray: '4 2',
        },
      });
    });

    // Add dependency edges between inquiries
    inquiries.forEach(inquiry => {
      inquiry.blocked_by?.forEach(blockerId => {
        edges.push({
          id: `dep-${blockerId}-${inquiry.id}`,
          source: `inquiry-${blockerId}`,
          target: `inquiry-${inquiry.id}`,
          type: 'smoothstep',
          animated: true,
          style: {
            stroke: '#f59e0b',
            strokeWidth: 2,
          },
          label: 'blocks',
          labelStyle: { fontSize: 10, fill: '#f59e0b' },
        });
      });
    });

    return { initialNodes: nodes, initialEdges: edges };
  }, [caseData, inquiries, signals, onInquiryClick, onDecisionClick]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Apply dagre layout
  const { layoutNodes } = useCanvasLayout(nodes, edges);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node.id);
  }, []);

  return (
    <div className="w-full h-full bg-neutral-50">
      <ReactFlow
        nodes={layoutNodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={1.5}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
      >
        <Background color="#e5e7eb" gap={20} size={1} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(node) => {
            if (node.type === 'decision') return '#6366f1';
            if (node.type === 'inquiry') {
              const inquiry = node.data?.inquiry;
              if (inquiry?.status === 'resolved') return '#22c55e';
              if (node.data?.isBlocked) return '#f59e0b';
              return '#3b82f6';
            }
            return '#94a3b8';
          }}
          maskColor="rgba(0,0,0,0.1)"
          className="!bg-white !border-neutral-200"
        />

        {/* Canvas controls panel */}
        <Panel position="top-right">
          <CanvasControls
            onAddInquiry={onAddInquiry}
            onOpenBrief={onOpenBrief}
            onOpenSignals={onOpenSignals}
            onOpenReadiness={onOpenReadiness}
            inquiryCount={inquiries.length}
            openCount={inquiries.filter(i => i.status !== 'resolved').length}
            resolvedCount={inquiries.filter(i => i.status === 'resolved').length}
            signalCount={signals.length}
          />
        </Panel>

        {/* Evidence landscape panel (replaces confidence) */}
        <Panel position="bottom-left">
          <div className="bg-white/90 backdrop-blur rounded-xl shadow-lg border border-neutral-200 overflow-hidden max-w-xs">
            {/* Header - always visible */}
            <button
              onClick={() => setShowEvidencePanel(!showEvidencePanel)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-neutral-50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="text-left">
                  <p className="text-sm font-medium text-neutral-900">Evidence</p>
                  <p className="text-xs text-neutral-500">
                    {totalEvidence} items · {openInquiryCount} open inquiries
                  </p>
                </div>
              </div>
              {showEvidencePanel ? (
                <ChevronDownIcon className="w-4 h-4 text-neutral-400" />
              ) : (
                <ChevronUpIcon className="w-4 h-4 text-neutral-400" />
              )}
            </button>

            {/* Expanded details */}
            {showEvidencePanel && landscape && (
              <div className="border-t px-4 py-3 space-y-3">
                {/* Evidence counts */}
                <div className="space-y-2">
                  <p className="text-xs font-medium text-neutral-600">Evidence</p>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-green-600">{landscape.evidence.supporting} supporting</span>
                    <span className="text-red-600">{landscape.evidence.contradicting} contradicting</span>
                    <span className="text-neutral-500">{landscape.evidence.neutral} neutral</span>
                  </div>
                </div>

                {/* Inquiry stats */}
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div className="bg-neutral-50 rounded-lg p-2 text-center">
                    <p className="font-semibold text-neutral-600">{landscape.inquiries.open}</p>
                    <span className="text-neutral-400 text-xs">Open</span>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-2 text-center">
                    <p className="font-semibold text-blue-600">{landscape.inquiries.investigating}</p>
                    <span className="text-blue-400 text-xs">Active</span>
                  </div>
                  <div className="bg-green-50 rounded-lg p-2 text-center">
                    <p className="font-semibold text-green-600">{landscape.inquiries.resolved}</p>
                    <span className="text-green-400 text-xs">Done</span>
                  </div>
                </div>

                {/* Untested assumptions warning */}
                {untestedAssumptionCount > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-2">
                    <div className="flex items-center gap-1.5 text-xs text-amber-700">
                      <QuestionMarkCircleIcon className="w-3 h-3" />
                      <span>{untestedAssumptionCount} untested assumptions</span>
                    </div>
                  </div>
                )}

                {/* User's confidence (if set) */}
                {caseData.user_confidence !== null && caseData.user_confidence !== undefined && (
                  <div className="bg-neutral-50 rounded-lg p-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-neutral-500">Your confidence:</span>
                      <span className={`font-medium ${getUserConfidenceColor(caseData.user_confidence)}`}>
                        {caseData.user_confidence}
                      </span>
                    </div>
                  </div>
                )}

                {/* View readiness button */}
                <button
                  onClick={onOpenReadiness}
                  className="w-full text-center text-xs text-accent-600 hover:text-accent-700 py-1"
                >
                  View full readiness assessment
                </button>
              </div>
            )}
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}

// Helpers
function getStatusColor(status: string): string {
  switch (status) {
    case 'resolved':
      return '#22c55e'; // green
    case 'investigating':
      return '#3b82f6'; // blue
    default:
      return '#94a3b8'; // neutral
  }
}

function getUserConfidenceColor(confidence: number): string {
  if (confidence >= 70) return 'text-green-600';
  if (confidence >= 40) return 'text-amber-600';
  return 'text-red-600';
}
