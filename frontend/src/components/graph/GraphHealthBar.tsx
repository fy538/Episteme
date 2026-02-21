/**
 * GraphHealthBar — Compact summary of graph composition.
 *
 * Shows: "24 nodes · 4 assumptions · 2 tensions · 1 ungrounded"
 * Floats in the top-left of the graph canvas.
 * Highlights epistemic risks (untested assumptions, unresolved tensions).
 */

'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import type { GraphNode, ClusterQuality } from '@/lib/types/graph';

interface GraphHealthBarProps {
  nodes: GraphNode[];
  clusterQuality?: ClusterQuality;
  totalNodeCount?: number;
  truncated?: boolean;
  className?: string;
}

export function GraphHealthBar({ nodes, clusterQuality, totalNodeCount, truncated, className }: GraphHealthBarProps) {
  const stats = useMemo(() => {
    let claims = 0;
    let evidence = 0;
    let assumptions = 0;
    let tensions = 0;
    let untestedAssumptions = 0;
    let unresolvedTensions = 0;
    let unsubstantiatedClaims = 0;

    for (const node of nodes) {
      switch (node.node_type) {
        case 'claim':
          claims++;
          if (node.status === 'unsubstantiated') unsubstantiatedClaims++;
          break;
        case 'evidence':
          evidence++;
          break;
        case 'assumption':
          assumptions++;
          if (node.status === 'untested') untestedAssumptions++;
          break;
        case 'tension':
          tensions++;
          if (node.status !== 'resolved') unresolvedTensions++;
          break;
      }
    }

    return {
      total: nodes.length,
      claims,
      evidence,
      assumptions,
      tensions,
      untestedAssumptions,
      unresolvedTensions,
      unsubstantiatedClaims,
    };
  }, [nodes]);

  if (stats.total === 0) return null;

  return (
    <div className={cn(
      'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg',
      'bg-white/90 dark:bg-neutral-800/90 backdrop-blur-sm',
      'border border-neutral-200/60 dark:border-neutral-700/60',
      'shadow-sm text-xs',
      className,
    )}>
      {/* Total */}
      <span className="font-semibold text-neutral-700 dark:text-neutral-200">
        {truncated
          ? `${stats.total} / ${totalNodeCount} nodes`
          : `${stats.total} nodes`}
      </span>

      <Dot />

      {/* Type breakdown */}
      <span className="text-info-600 dark:text-info-400">{stats.claims}C</span>
      <span className="text-success-600 dark:text-success-400">{stats.evidence}E</span>
      <span className="text-warning-600 dark:text-warning-400">{stats.assumptions}A</span>
      <span className="text-rose-600 dark:text-rose-400">{stats.tensions}T</span>

      {/* Modularity score */}
      {clusterQuality && clusterQuality.modularity > 0 && (
        <>
          <Dot />
          <span
            className={cn(
              'font-medium',
              clusterQuality.modularity > 0.3
                ? 'text-success-600 dark:text-success-400'
                : 'text-warning-600 dark:text-warning-400',
            )}
            title={`Cluster quality: ${clusterQuality.modularity > 0.5 ? 'Strong' : clusterQuality.modularity > 0.3 ? 'Good' : 'Weak'} groupings (modularity ${clusterQuality.modularity.toFixed(2)}, conductance ${clusterQuality.mean_conductance.toFixed(2)})`}
          >
            Q={clusterQuality.modularity.toFixed(2)}
          </span>
        </>
      )}

      {/* Risk indicators */}
      {(stats.untestedAssumptions > 0 || stats.unresolvedTensions > 0) && (
        <>
          <Dot />
          {stats.untestedAssumptions > 0 && (
            <span className="flex items-center gap-0.5 text-warning-600 dark:text-warning-400 font-medium">
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              {stats.untestedAssumptions} untested
            </span>
          )}
          {stats.unresolvedTensions > 0 && (
            <span className="flex items-center gap-0.5 text-rose-600 dark:text-rose-400 font-medium">
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              {stats.unresolvedTensions} unresolved
            </span>
          )}
        </>
      )}

      {/* Truncation warning */}
      {truncated && (
        <>
          <Dot />
          <span
            className="flex items-center gap-0.5 text-orange-600 dark:text-orange-400 font-medium"
            title={`Graph capped at ${stats.total} nodes. ${totalNodeCount! - stats.total} nodes not shown.`}
          >
            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 4h18M3 8h18M3 12h12M3 16h8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            capped
          </span>
        </>
      )}
    </div>
  );
}

function Dot() {
  return <span className="text-neutral-300 dark:text-neutral-600">&middot;</span>;
}
