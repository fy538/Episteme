/**
 * ClusterNode — Super-node rendered when a cluster is collapsed.
 *
 * Shows cluster label, node count, type breakdown, and a
 * collapse/expand toggle. Size scales with member count.
 * When a summary is available and zoom >= ZOOM_THRESHOLDS.summary,
 * displays a 1-2 sentence thematic description.
 */

'use client';

import { memo, useCallback } from 'react';
import { Handle, Position, useStore } from '@xyflow/react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { CLUSTER_CONFIG, ZOOM_THRESHOLDS } from '../graph-config';

const zoomSelector = (s: { transform: [number, number, number] }) => s.transform[2];

interface ClusterNodeProps {
  data: {
    label: string;
    summary?: string;
    nodeCount: number;
    typeCounts: Record<string, number>;
    clusterId: string;
    isCollapsed: boolean;
    highlightsActive?: boolean;
    onToggleCollapse?: (clusterId: string) => void;
    onExpand?: () => void;
  };
  selected?: boolean;
}

export const ClusterNode = memo(function ClusterNode({ data, selected }: ClusterNodeProps) {
  const { label, summary, nodeCount, typeCounts, clusterId, isCollapsed, highlightsActive, onToggleCollapse } = data;

  const zoom = useStore(zoomSelector);
  const showSummary = !!summary && zoom >= ZOOM_THRESHOLDS.summary;

  // Dynamic width based on node count
  const width = Math.min(
    CLUSTER_CONFIG.superNodeMaxWidth,
    CLUSTER_CONFIG.superNodeMinWidth + Math.min(nodeCount, 20) * 4,
  );

  // Taller when summary is visible
  const minHeight = showSummary
    ? CLUSTER_CONFIG.superNodeSummaryHeight
    : CLUSTER_CONFIG.superNodeMinHeight;

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
        highlightsActive && 'opacity-30',
      )}
      style={{ minWidth: width, minHeight }}
      onClick={data.onExpand}
    >
      <Handle type="target" position={Position.Top} className="!w-0 !h-0 !border-0 !bg-transparent" />

      {/* Header row with label + toggle */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <p className="text-xs font-semibold text-neutral-700 dark:text-neutral-200 line-clamp-2 flex-1">
          {label}
        </p>
        {onToggleCollapse && (
          <Button
            variant="ghost"
            size="icon"
            onClick={handleToggle}
            className={cn(
              'shrink-0 h-5 w-5',
              'bg-neutral-100 dark:bg-neutral-800',
              'hover:bg-neutral-200 dark:hover:bg-neutral-700',
              'text-neutral-500 dark:text-neutral-400',
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
          </Button>
        )}
      </div>

      {/* Summary (zoom-aware: visible at medium+ zoom, placed right after label) */}
      {showSummary && (
        <p className="text-xs text-neutral-500 dark:text-neutral-400 leading-tight mt-1 mb-2 line-clamp-3">
          {summary}
        </p>
      )}

      {/* Metadata row: node count + type breakdown */}
      <div className="flex items-center gap-3 mt-1.5">
        <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
          {nodeCount} nodes
        </span>
        <div className="flex items-center gap-2">
          {(typeCounts.claim ?? 0) > 0 && (
            <TypeDot color="bg-info-500" count={typeCounts.claim} label="claims" />
          )}
          {(typeCounts.evidence ?? 0) > 0 && (
            <TypeDot color="bg-success-500" count={typeCounts.evidence} label="evidence" />
          )}
          {(typeCounts.assumption ?? 0) > 0 && (
            <TypeDot color="bg-warning-500" count={typeCounts.assumption} label="assumptions" />
          )}
          {(typeCounts.tension ?? 0) > 0 && (
            <TypeDot color="bg-rose-500" count={typeCounts.tension} label="tensions" />
          )}
        </div>
      </div>

      {/* Expand hint (only when collapsed) */}
      {isCollapsed && (
        <div className="mt-2 flex items-center gap-1 text-xs text-neutral-400 dark:text-neutral-500">
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
      <span className="text-xs text-neutral-500 dark:text-neutral-400">{count}</span>
    </span>
  );
}
