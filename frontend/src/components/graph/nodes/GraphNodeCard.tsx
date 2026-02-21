/**
 * GraphNodeCard — Unified custom node component for React Flow.
 *
 * Renders differently based on zoom level:
 *   - Far:    Compact pill (type icon + short label)
 *   - Medium: Summary card (type badge + status + truncated content)
 *   - Close:  Full detail (confidence bar + source + edge count)
 *
 * Used as the node renderer for all four types (claim, evidence, assumption, tension).
 * The node type determines color scheme via graph-config.
 */

'use client';

import { memo } from 'react';
import { Handle, Position, useStore } from '@xyflow/react';
import { cn } from '@/lib/utils';
import type { GraphNode } from '@/lib/types/graph';
import {
  NODE_TYPE_CONFIG,
  NODE_STATUS_CONFIG,
  ZOOM_THRESHOLDS,
  IMPORTANCE_VISIBILITY,
} from '../graph-config';

// Hex colors for minimal dot rendering (avoids parsing Tailwind classes)
const NODE_TYPE_COLORS: Record<string, string> = {
  claim: '#3b82f6',
  evidence: '#10b981',
  assumption: '#f59e0b',
  tension: '#f43f5e',
};

interface GraphNodeCardProps {
  data: {
    graphNode: GraphNode;
    /** True when this node is in the highlighted set (e.g. from upload impact) */
    highlighted?: boolean;
    /** True when any highlighting is active (non-highlighted nodes dim) */
    highlightsActive?: boolean;
  };
  selected?: boolean;
}

// Selector extracted outside component to maintain stable reference
const zoomSelector = (s: { transform: [number, number, number] }) => s.transform[2];

export const GraphNodeCard = memo(function GraphNodeCard({
  data,
  selected,
}: GraphNodeCardProps) {
  const { graphNode, highlighted, highlightsActive } = data;
  const typeConfig = NODE_TYPE_CONFIG[graphNode.node_type];
  const statusConfig = NODE_STATUS_CONFIG[graphNode.status];
  const importance = graphNode.properties?.importance ?? 1;
  const zoom = useStore(zoomSelector);

  // Dim non-highlighted nodes when highlighting is active
  const isDimmed = highlightsActive && !highlighted;

  // At low zoom, show lower-importance nodes as compact pills instead of hiding
  const minZoom = IMPORTANCE_VISIBILITY[importance] ?? 0.65;
  const effectiveZoom = zoom < minZoom ? -1 : zoom;

  // Below visibility threshold: render a minimal dot so edges still connect properly
  if (effectiveZoom < 0) {
    return (
      <div className={cn('w-3 h-3 rounded-full opacity-30', isDimmed && 'opacity-10')} style={{ background: NODE_TYPE_COLORS[graphNode.node_type] }}>
        <Handle type="target" position={Position.Top} className="!w-0 !h-0 !border-0 !bg-transparent" />
        <Handle type="source" position={Position.Bottom} className="!w-0 !h-0 !border-0 !bg-transparent" />
      </div>
    );
  }

  // Determine rendering tier
  if (zoom < ZOOM_THRESHOLDS.compact) {
    return <CompactPill graphNode={graphNode} typeConfig={typeConfig} selected={selected} highlighted={highlighted} isDimmed={isDimmed} />;
  }

  if (zoom < ZOOM_THRESHOLDS.summary) {
    return <SummaryCard graphNode={graphNode} typeConfig={typeConfig} statusConfig={statusConfig} selected={selected} highlighted={highlighted} isDimmed={isDimmed} />;
  }

  return (
    <DetailCard
      graphNode={graphNode}
      typeConfig={typeConfig}
      statusConfig={statusConfig}
      selected={selected}
      highlighted={highlighted}
      isDimmed={isDimmed}
    />
  );
});

// ── Compact Pill (far zoom) ──────────────────────────────────

function CompactPill({
  graphNode,
  typeConfig,
  selected,
  highlighted,
  isDimmed,
}: {
  graphNode: GraphNode;
  typeConfig: typeof NODE_TYPE_CONFIG[keyof typeof NODE_TYPE_CONFIG];
  selected?: boolean;
  highlighted?: boolean;
  isDimmed?: boolean;
}) {
  return (
    <div
      className={cn(
        'flex items-center gap-1.5 px-2.5 py-1.5 rounded-full border shadow-sm',
        'transition-all cursor-pointer',
        typeConfig.bgClass,
        typeConfig.borderClass,
        selected && 'ring-2 ring-accent-500 shadow-md',
        highlighted && 'ring-2 ring-accent-400 shadow-lg shadow-accent-200/50 dark:shadow-accent-800/30',
        isDimmed && 'opacity-30',
      )}
    >
      <Handle type="target" position={Position.Top} className="!w-0 !h-0 !border-0 !bg-transparent" />
      <NodeTypeIcon path={typeConfig.icon} className={cn('w-3 h-3 shrink-0', typeConfig.textClass)} />
      <span className={cn('text-xs font-medium truncate max-w-[100px]', typeConfig.textClass)}>
        {graphNode.content.slice(0, 30)}
      </span>
      <Handle type="source" position={Position.Bottom} className="!w-0 !h-0 !border-0 !bg-transparent" />
    </div>
  );
}

// ── Summary Card (medium zoom) ───────────────────────────────

function SummaryCard({
  graphNode,
  typeConfig,
  statusConfig,
  selected,
  highlighted,
  isDimmed,
}: {
  graphNode: GraphNode;
  typeConfig: typeof NODE_TYPE_CONFIG[keyof typeof NODE_TYPE_CONFIG];
  statusConfig: typeof NODE_STATUS_CONFIG[keyof typeof NODE_STATUS_CONFIG];
  selected?: boolean;
  highlighted?: boolean;
  isDimmed?: boolean;
}) {
  return (
    <div
      className={cn(
        'rounded-lg border shadow-sm p-2.5 min-w-[180px] max-w-[220px]',
        'transition-all cursor-pointer',
        typeConfig.bgClass,
        typeConfig.borderClass,
        selected && 'ring-2 ring-accent-500 shadow-md',
        highlighted && 'ring-2 ring-accent-400 shadow-lg shadow-accent-200/50 dark:shadow-accent-800/30',
        isDimmed && 'opacity-30',
      )}
    >
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !border-2 !border-neutral-300 dark:!border-neutral-600 !bg-white dark:!bg-neutral-800" />

      {/* Type + Status row */}
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-xs font-semibold uppercase tracking-wider', typeConfig.badgeBg, typeConfig.badgeText)}>
          <NodeTypeIcon path={typeConfig.icon} className="w-2.5 h-2.5" />
          {typeConfig.label}
        </span>
        <span className="flex items-center gap-1 ml-auto">
          <span className={cn('w-1.5 h-1.5 rounded-full', statusConfig.dotColor)} />
          <span className={cn('text-xs', statusConfig.textClass)}>{statusConfig.label}</span>
        </span>
      </div>

      {/* Content */}
      <p className="text-xs leading-tight text-neutral-700 dark:text-neutral-300 line-clamp-3">
        {graphNode.content}
      </p>

      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !border-2 !border-neutral-300 dark:!border-neutral-600 !bg-white dark:!bg-neutral-800" />
    </div>
  );
}

// ── Detail Card (close zoom) ─────────────────────────────────

function DetailCard({
  graphNode,
  typeConfig,
  statusConfig,
  selected,
  highlighted,
  isDimmed,
}: {
  graphNode: GraphNode;
  typeConfig: typeof NODE_TYPE_CONFIG[keyof typeof NODE_TYPE_CONFIG];
  statusConfig: typeof NODE_STATUS_CONFIG[keyof typeof NODE_STATUS_CONFIG];
  selected?: boolean;
  highlighted?: boolean;
  isDimmed?: boolean;
}) {
  const confidence = graphNode.confidence;
  const isLoadBearing = graphNode.properties?.load_bearing;
  const severity = graphNode.properties?.severity;
  const sourceTitle = graphNode.source_document_title;

  return (
    <div
      className={cn(
        'rounded-xl border shadow-sm p-3 min-w-[240px] max-w-[280px]',
        'transition-all cursor-pointer',
        typeConfig.bgClass,
        typeConfig.borderClass,
        selected && 'ring-2 ring-accent-500 shadow-lg',
        highlighted && 'ring-2 ring-accent-400 shadow-lg shadow-accent-200/50 dark:shadow-accent-800/30',
        isDimmed && 'opacity-30',
      )}
    >
      <Handle type="target" position={Position.Top} className="!w-2.5 !h-2.5 !border-2 !border-neutral-300 dark:!border-neutral-600 !bg-white dark:!bg-neutral-800" />

      {/* Type badge + status + flags */}
      <div className="flex items-center gap-1.5 mb-2">
        <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-xs font-semibold uppercase tracking-wider', typeConfig.badgeBg, typeConfig.badgeText)}>
          <NodeTypeIcon path={typeConfig.icon} className="w-2.5 h-2.5" />
          {typeConfig.label}
        </span>
        <span className="flex items-center gap-1">
          <span className={cn('w-1.5 h-1.5 rounded-full', statusConfig.dotColor)} />
          <span className={cn('text-xs', statusConfig.textClass)}>{statusConfig.label}</span>
        </span>
        {isLoadBearing && (
          <span className="ml-auto px-1 py-0.5 rounded text-[8px] font-bold uppercase bg-warning-200 dark:bg-warning-900/50 text-warning-800 dark:text-warning-300">
            Load-bearing
          </span>
        )}
        {severity && (
          <span className={cn(
            'ml-auto px-1 py-0.5 rounded text-[8px] font-bold uppercase',
            severity === 'high' ? 'bg-rose-200 dark:bg-rose-900/50 text-rose-800 dark:text-rose-300' :
            severity === 'medium' ? 'bg-warning-200 dark:bg-warning-900/50 text-warning-800 dark:text-warning-300' :
            'bg-neutral-200 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300'
          )}>
            {severity}
          </span>
        )}
      </div>

      {/* Content */}
      <p className="text-xs leading-relaxed text-neutral-700 dark:text-neutral-300 mb-2">
        {graphNode.content}
      </p>

      {/* Analysis badges (from CaseGraphView analysis flags injection) */}
      {(graphNode.properties?._analysisFlags?.unsupported || graphNode.properties?._analysisFlags?.untestedLoadBearing) && (
        <div className="flex items-center gap-1.5 mb-2">
          {graphNode.properties._analysisFlags.unsupported && (
            <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded font-medium">
              Unsupported
            </span>
          )}
          {graphNode.properties._analysisFlags.untestedLoadBearing && (
            <span className="text-[10px] px-1.5 py-0.5 bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-300 rounded font-medium">
              Untested
            </span>
          )}
        </div>
      )}

      {/* Confidence bar */}
      <div className="mb-2">
        <div className="flex items-center justify-between mb-0.5">
          <span className="text-xs text-neutral-500 dark:text-neutral-400">Confidence</span>
          <span className="text-xs font-medium text-neutral-600 dark:text-neutral-300">{Math.round(confidence * 100)}%</span>
        </div>
        <div className="h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all',
              confidence >= 0.7 ? 'bg-success-500' :
              confidence >= 0.4 ? 'bg-warning-500' :
              'bg-rose-500'
            )}
            style={{ width: `${confidence * 100}%` }}
          />
        </div>
      </div>

      {/* Source provenance */}
      {sourceTitle && (
        <div className="flex items-center gap-1 text-xs text-neutral-400 dark:text-neutral-500">
          <svg className="w-2.5 h-2.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <path d="M14 2v6h6" />
          </svg>
          <span className="truncate">{sourceTitle}</span>
        </div>
      )}

      {/* Scope indicator */}
      {graphNode.scope === 'case' && (
        <div className="mt-1.5 flex items-center gap-1 text-xs text-accent-500 dark:text-accent-400">
          <svg className="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
            <path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16" />
          </svg>
          <span>Case-local</span>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!w-2.5 !h-2.5 !border-2 !border-neutral-300 dark:!border-neutral-600 !bg-white dark:!bg-neutral-800" />
    </div>
  );
}

// ── Shared icon component ────────────────────────────────────

function NodeTypeIcon({ path, className }: { path: string; className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d={path} />
    </svg>
  );
}
