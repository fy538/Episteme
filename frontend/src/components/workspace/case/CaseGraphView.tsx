/**
 * CaseGraphView — Main wrapper for the case investigation graph.
 *
 * Composes GraphCanvas with case-specific features:
 *   - Analysis sidebar panel (readiness, blind spots, assumptions, tensions)
 *   - Node highlighting from analysis panel interactions
 *   - Empty/loading/error states
 *   - Analysis badge injection into graph nodes
 *   - "Ask about this node" → chat integration
 */

'use client';

import { useState, useMemo, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { AnalysisPanel } from './AnalysisPanel';
import { EmptyGraphState } from './EmptyGraphState';
import { useCaseGraph, useCaseAnalysis } from '@/hooks/useCaseGraph';
import { Spinner } from '@/components/ui/spinner';
import { Button } from '@/components/ui/button';
import { casesAPI } from '@/lib/api/cases';
import { useQueryClient } from '@tanstack/react-query';
import type { GraphNode } from '@/lib/types/graph';

interface CaseGraphViewProps {
  projectId: string;
  caseId: string;
  decisionQuestion?: string;
  onAskAboutNode?: (node: GraphNode) => void;
  onViewDocuments?: () => void;
  className?: string;
}

export function CaseGraphView({
  projectId,
  caseId,
  decisionQuestion,
  onAskAboutNode,
  onViewDocuments,
  className,
}: CaseGraphViewProps) {
  const queryClient = useQueryClient();
  const { data: graphData, isLoading: graphLoading } = useCaseGraph(projectId, caseId);
  const { data: analysis } = useCaseAnalysis(caseId);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<string[]>([]);
  const highlightedRef = useRef(highlightedNodeIds);
  highlightedRef.current = highlightedNodeIds;
  const [analysisPanelOpen, setAnalysisPanelOpen] = useState(true);

  // Build analysis flags map for node badge injection
  const analysisFlags = useMemo(() => {
    if (!analysis) return new Map<string, { unsupported?: boolean; untestedLoadBearing?: boolean }>();
    const flags = new Map<string, { unsupported?: boolean; untestedLoadBearing?: boolean }>();

    // Mark unsupported claims
    for (const c of analysis.evidence_coverage.unsupported_claims ?? []) {
      const existing = flags.get(c.node_id) ?? {};
      flags.set(c.node_id, { ...existing, unsupported: true });
    }

    // Mark untested load-bearing assumptions
    for (const a of analysis.assumption_assessment) {
      if (a.load_bearing && a.supporting_evidence === 0) {
        const existing = flags.get(a.node_id) ?? {};
        flags.set(a.node_id, { ...existing, untestedLoadBearing: true });
      }
    }

    return flags;
  }, [analysis]);

  // Enrich graph nodes with analysis flags in properties
  const enrichedNodes = useMemo(() => {
    if (!graphData?.nodes || analysisFlags.size === 0) return graphData?.nodes ?? [];
    return graphData.nodes.map(node => {
      const flags = analysisFlags.get(node.id);
      if (!flags) return node;
      return {
        ...node,
        properties: {
          ...node.properties,
          _analysisFlags: flags,
        },
      };
    });
  }, [graphData?.nodes, analysisFlags]);

  // Re-extract handler
  const handleReExtract = useCallback(async () => {
    try {
      await casesAPI.reExtract(caseId);
      // Invalidate queries so data refreshes after extraction completes
      queryClient.invalidateQueries({ queryKey: ['case-graph', projectId, caseId] });
      queryClient.invalidateQueries({ queryKey: ['case-analysis', caseId] });
    } catch (error) {
      console.error('Failed to trigger re-extraction:', error);
    }
  }, [caseId, projectId, queryClient]);

  // Clear highlights on Escape (uses ref to avoid re-creating callback on highlight changes)
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && highlightedRef.current.length > 0) {
      setHighlightedNodeIds([]);
    }
  }, []);

  // Loading state
  if (graphLoading) {
    return (
      <div className={cn('flex items-center justify-center h-full', className)}>
        <div className="flex items-center gap-2 text-sm text-neutral-500">
          <Spinner />
          Loading investigation graph...
        </div>
      </div>
    );
  }

  // Empty state — no graph data
  if (!graphData?.nodes?.length) {
    return (
      <EmptyGraphState
        caseId={caseId}
        onReExtract={handleReExtract}
        onViewDocuments={onViewDocuments}
        className={className}
      />
    );
  }

  return (
    <div
      className={cn('flex h-full', className)}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      {/* Graph area */}
      <div className="flex-1 relative flex flex-col min-w-0">
        {/* Header bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200/60 dark:border-neutral-800/60 bg-white dark:bg-neutral-950 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            {decisionQuestion && (
              <p className="text-sm text-neutral-600 dark:text-neutral-400 truncate">
                {decisionQuestion}
              </p>
            )}
            <div className="flex items-center gap-2 text-xs text-neutral-400 dark:text-neutral-500 shrink-0">
              <span>{graphData.nodes.length} nodes</span>
              <span className="text-neutral-300 dark:text-neutral-600">&middot;</span>
              <span>{graphData.edges.length} edges</span>
              {graphData.truncated && (
                <>
                  <span className="text-neutral-300 dark:text-neutral-600">&middot;</span>
                  <span className="text-warning-500">truncated</span>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {!analysisPanelOpen && analysis && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setAnalysisPanelOpen(true)}
                className="text-xs"
              >
                Show Analysis
              </Button>
            )}
          </div>
        </div>

        {/* Graph canvas */}
        <div className="flex-1 min-h-0">
          <GraphCanvas
            graphNodes={enrichedNodes}
            graphEdges={graphData.edges}
            projectId={projectId}
            caseId={caseId}
            highlightedNodeIds={highlightedNodeIds}
            onAskAboutNode={onAskAboutNode}
            totalNodeCount={graphData.total_node_count}
            truncated={graphData.truncated}
          />
        </div>
      </div>

      {/* Analysis sidebar */}
      {analysisPanelOpen && analysis && (
        <AnalysisPanel
          analysis={analysis}
          onHighlightNodes={setHighlightedNodeIds}
          onClose={() => setAnalysisPanelOpen(false)}
        />
      )}
    </div>
  );
}
