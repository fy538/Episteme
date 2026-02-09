/**
 * Custom edge components for the three edge types.
 *
 * - SupportsEdge:    Solid green line with arrow
 * - ContradictsEdge: Dashed red line with bidirectional markers
 * - DependsOnEdge:   Dotted neutral line with arrow
 *
 * All use getBezierPath for smooth curves with proper edge routing.
 * Edge labels appear on hover at medium+ zoom.
 */

'use client';

import { memo, useState } from 'react';
import {
  BaseEdge,
  getBezierPath,
  EdgeLabelRenderer,
  useStore,
  type EdgeProps,
} from '@xyflow/react';
import { cn } from '@/lib/utils';
import type { GraphEdge as GraphEdgeType } from '@/lib/types/graph';
import { EDGE_TYPE_CONFIG, ZOOM_THRESHOLDS } from '../graph-config';

interface CustomEdgeData {
  graphEdge: GraphEdgeType;
}

// Stable selector reference — prevents re-subscription on every render
const zoomSelector = (s: { transform: [number, number, number] }) => s.transform[2];

// ── Supports Edge ────────────────────────────────────────────

export const SupportsEdge = memo(function SupportsEdge(props: EdgeProps) {
  return <GraphEdgeBase {...props} />;
});

// ── Contradicts Edge ─────────────────────────────────────────

export const ContradictsEdge = memo(function ContradictsEdge(props: EdgeProps) {
  return <GraphEdgeBase {...props} />;
});

// ── Depends On Edge ──────────────────────────────────────────

export const DependsOnEdge = memo(function DependsOnEdge(props: EdgeProps) {
  return <GraphEdgeBase {...props} />;
});

// ── Shared base edge ─────────────────────────────────────────

function GraphEdgeBase({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  style,
}: EdgeProps) {
  const [isHovered, setIsHovered] = useState(false);
  const zoom = useStore(zoomSelector);
  const graphEdge = (data as unknown as CustomEdgeData)?.graphEdge;
  const edgeType = graphEdge?.edge_type ?? 'supports';
  const config = EDGE_TYPE_CONFIG[edgeType];

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    curvature: 0.25,
  });

  const showLabel = (isHovered || selected) && zoom > ZOOM_THRESHOLDS.compact;
  const strength = graphEdge?.strength ?? 0.5;

  return (
    <>
      {/* Invisible wider path for hover target */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className="cursor-pointer"
      />

      {/* Visible edge */}
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: config.strokeColor,
          strokeWidth: Math.max(1.5, strength * 3),
          strokeDasharray: config.strokeDasharray,
          opacity: isHovered || selected ? 1 : 0.6,
          transition: 'opacity 0.15s, stroke-width 0.15s',
        }}
        markerEnd={`url(#${config.markerEnd})`}
      />

      {/* Label on hover */}
      {showLabel && (
        <EdgeLabelRenderer>
          <div
            className={cn(
              'absolute pointer-events-none',
              'px-2 py-0.5 rounded-md text-[9px] font-medium',
              'bg-white dark:bg-neutral-800 border shadow-sm',
              edgeType === 'supports' && 'border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300',
              edgeType === 'contradicts' && 'border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300',
              edgeType === 'depends_on' && 'border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400',
            )}
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
          >
            {config.label}
            {graphEdge?.provenance && (
              <span className="block text-[8px] text-neutral-400 dark:text-neutral-500 mt-0.5 max-w-[120px] truncate">
                {graphEdge.provenance}
              </span>
            )}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
