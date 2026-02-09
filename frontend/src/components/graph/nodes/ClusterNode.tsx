/**
 * ClusterNode — Super-node rendered when a cluster is collapsed.
 *
 * Shows cluster label, node count, type breakdown, and a
 * collapse/expand toggle. Size scales with member count.
 */

'use client';

import { memo, useCallback } from 'react';
import { Handle, Position } from '@xyflow/react';
import { cn } from '@/lib/utils';
import { CLUSTER_CONFIG } from '../graph-config';

interface ClusterNodeProps {
  data: {
    label: string;
    nodeCount: number;
    typeCounts: Record<string, number>;
    clusterId: string;
    isCollapsed: boolean;
    onToggleCollapse?: (clusterId: string) => void;
    onExpand?: () => void;
  };
  selected?: boolean;
}

export const ClusterNode = memo(function ClusterNode({ data, selected }: ClusterNodeProps) {
  const { label, nodeCount, typeCounts, clusterId, isCollapsed, onToggleCollapse } = data;

  // Dynamic width based on node count
  const width = Math.min(
    CLUSTER_CONFIG.superNodeMaxWidth,
    CLUSTER_CONFIG.superNodeMinWidth + Math.min(nodeCount, 20) * 4,
  );

  const handleToggle = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleCollapse?.(clusterId);
  }, [clusterId, onToggleCollapse]);

  return (
    <div
      className={cn(
        'rounded-2xl border-2 border-dashed border-neutral-300 dark:border-neutral-600',
        'bg-white/60 dark:bg-neutral-900/60 backdrop-blur-sm',
        'shadow-sm p-4 cursor-pointer',
        'transition-all hover:shadow-md hover:border-neutral-400 dark:hover:border-neutral-500',
        selected && 'ring-2 ring-accent-500',
      )}
      style={{ minWidth: width, minHeight: CLUSTER_CONFIG.superNodeMinHeight }}
      onClick={data.onExpand}
    >
      <Handle type="target" position={Position.Top} className="!w-0 !h-0 !border-0 !bg-transparent" />

      {/* Header row with label + toggle */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-xs font-semibold text-neutral-700 dark:text-neutral-200 line-clamp-2 flex-1">
          {label}
        </p>
        {onToggleCollapse && (
          <button
            onClick={handleToggle}
            className={cn(
              'shrink-0 w-5 h-5 rounded flex items-center justify-center',
              'bg-neutral-100 dark:bg-neutral-800',
              'hover:bg-neutral-200 dark:hover:bg-neutral-700',
              'text-neutral-500 dark:text-neutral-400',
              'transition-colors',
            )}
            title={isCollapsed ? 'Expand cluster' : 'Collapse cluster'}
          >
            {isCollapsed ? (
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M4 14h6v6M14 4h6v6M10 14l-7 7M21 3l-7 7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </button>
        )}
      </div>

      {/* Node count */}
      <div className="flex items-center gap-1.5 text-[10px] text-neutral-500 dark:text-neutral-400">
        <span className="font-medium">{nodeCount} nodes</span>
      </div>

      {/* Type breakdown dots */}
      <div className="flex items-center gap-2 mt-2">
        {(typeCounts.claim ?? 0) > 0 && (
          <TypeDot color="bg-blue-500" count={typeCounts.claim} label="claims" />
        )}
        {(typeCounts.evidence ?? 0) > 0 && (
          <TypeDot color="bg-emerald-500" count={typeCounts.evidence} label="evidence" />
        )}
        {(typeCounts.assumption ?? 0) > 0 && (
          <TypeDot color="bg-amber-500" count={typeCounts.assumption} label="assumptions" />
        )}
        {(typeCounts.tension ?? 0) > 0 && (
          <TypeDot color="bg-rose-500" count={typeCounts.tension} label="tensions" />
        )}
      </div>

      {/* Expand hint (only when collapsed) */}
      {isCollapsed && (
        <div className="mt-2 flex items-center gap-1 text-[9px] text-neutral-400 dark:text-neutral-500">
          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Click to expand
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!w-0 !h-0 !border-0 !bg-transparent" />
    </div>
  );
});

function TypeDot({ color, count, label }: { color: string; count: number; label: string }) {
  return (
    <span className="flex items-center gap-0.5" title={`${count} ${label}`}>
      <span className={cn('w-2 h-2 rounded-full', color)} />
      <span className="text-[9px] text-neutral-500 dark:text-neutral-400">{count}</span>
    </span>
  );
}
