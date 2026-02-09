/**
 * ClusterHulls — Semi-transparent convex hull overlays behind cluster nodes.
 *
 * For each cluster, gathers positioned node bounding boxes, computes
 * a convex hull with padding, smooths to cubic bezier curves, and
 * renders as SVG with pointer-events: none (fully transparent to clicks).
 *
 * Color is based on the dominant node type in the cluster.
 */

'use client';

import { useMemo } from 'react';
import type { Node as FlowNode } from '@xyflow/react';
import type { ClusterInfo } from './useGraphLayout';
import type { NodeType } from '@/lib/types/graph';
import { HULL_CONFIG, NODE_TYPE_HEX } from './graph-config';

interface ClusterHullsProps {
  clusters: ClusterInfo[];
  nodes: FlowNode[];
  /** Node type counts per cluster from backend */
  clusterNodeTypes?: Record<string, number>[];
}

export function ClusterHulls({ clusters, nodes, clusterNodeTypes }: ClusterHullsProps) {
  const hullData = useMemo(() => {
    const nodePositions = new Map<string, { x: number; y: number; width: number; height: number }>();
    for (const node of nodes) {
      nodePositions.set(node.id, {
        x: node.position.x,
        y: node.position.y,
        width: node.measured?.width ?? node.width ?? 200,
        height: node.measured?.height ?? node.height ?? 60,
      });
    }

    return clusters
      .filter(cluster => cluster.nodeIds.length >= 2)
      .map((cluster, idx) => {
        // Gather all corner points with padding
        const points: [number, number][] = [];
        for (const nodeId of cluster.nodeIds) {
          const pos = nodePositions.get(nodeId);
          if (!pos) continue;

          const pad = HULL_CONFIG.padding;
          points.push(
            [pos.x - pad, pos.y - pad],
            [pos.x + pos.width + pad, pos.y - pad],
            [pos.x + pos.width + pad, pos.y + pos.height + pad],
            [pos.x - pad, pos.y + pos.height + pad],
          );
        }

        if (points.length < 3) return null;

        const hull = convexHull(points);
        const smoothPath = hullToSmoothPath(hull);

        // Determine dominant node type for color
        let dominantType: NodeType = 'claim';
        if (clusterNodeTypes && clusterNodeTypes[idx]) {
          const types = clusterNodeTypes[idx];
          let maxCount = 0;
          for (const [type, count] of Object.entries(types)) {
            if (count > maxCount) {
              maxCount = count;
              dominantType = type as NodeType;
            }
          }
        }

        // Label position: top-center of hull bounding box
        let minX = Infinity, minY = Infinity, maxX = -Infinity;
        for (const [px, py] of hull) {
          if (px < minX) minX = px;
          if (px > maxX) maxX = px;
          if (py < minY) minY = py;
        }

        return {
          id: cluster.id,
          label: cluster.label,
          path: smoothPath,
          color: NODE_TYPE_HEX[dominantType],
          labelX: (minX + maxX) / 2,
          labelY: minY - 4,
        };
      })
      .filter(Boolean) as Array<{
        id: string;
        label: string;
        path: string;
        color: string;
        labelX: number;
        labelY: number;
      }>;
  }, [clusters, nodes, clusterNodeTypes]);

  if (hullData.length === 0) return null;

  // Rendered as a child of <ReactFlow> — the viewport transform is applied
  // automatically by React Flow's internal wrapper, so no manual transform needed.
  return (
    <svg
      className="absolute inset-0 overflow-visible"
      style={{ pointerEvents: 'none', zIndex: -1, width: '100%', height: '100%' }}
    >
      {hullData.map(hull => (
        <g key={hull.id}>
          <path
            d={hull.path}
            fill={hull.color}
            fillOpacity={HULL_CONFIG.fillOpacity}
            stroke={hull.color}
            strokeOpacity={HULL_CONFIG.strokeOpacity}
            strokeWidth={HULL_CONFIG.strokeWidth}
          />
          <text
            x={hull.labelX}
            y={hull.labelY}
            textAnchor="middle"
            fill={hull.color}
            fillOpacity={0.6}
            fontSize={HULL_CONFIG.labelFontSize}
            fontWeight={500}
          >
            {hull.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

// ── Convex hull (Andrew's monotone chain) ────────────────────

function convexHull(points: [number, number][]): [number, number][] {
  const sorted = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (sorted.length <= 2) return sorted;

  const cross = (
    o: [number, number],
    a: [number, number],
    b: [number, number]
  ) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);

  // Lower hull
  const lower: [number, number][] = [];
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) {
      lower.pop();
    }
    lower.push(p);
  }

  // Upper hull
  const upper: [number, number][] = [];
  for (let i = sorted.length - 1; i >= 0; i--) {
    const p = sorted[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) {
      upper.pop();
    }
    upper.push(p);
  }

  // Remove last point of each half (it's repeated at the beginning of the other)
  lower.pop();
  upper.pop();

  return lower.concat(upper);
}

// ── Smooth hull with Catmull-Rom → cubic bezier ──────────────

function hullToSmoothPath(hull: [number, number][]): string {
  if (hull.length < 3) {
    return `M${hull.map(p => `${p[0]},${p[1]}`).join('L')}Z`;
  }

  const n = hull.length;
  const parts: string[] = [];

  // Move to first point
  parts.push(`M${hull[0][0]},${hull[0][1]}`);

  // For each segment, compute Catmull-Rom control points and convert to cubic bezier
  for (let i = 0; i < n; i++) {
    const p0 = hull[(i - 1 + n) % n];
    const p1 = hull[i];
    const p2 = hull[(i + 1) % n];
    const p3 = hull[(i + 2) % n];

    // Catmull-Rom → cubic bezier conversion (alpha = 0.5)
    const tension = 6;
    const cp1x = p1[0] + (p2[0] - p0[0]) / tension;
    const cp1y = p1[1] + (p2[1] - p0[1]) / tension;
    const cp2x = p2[0] - (p3[0] - p1[0]) / tension;
    const cp2y = p2[1] - (p3[1] - p1[1]) / tension;

    parts.push(`C${cp1x},${cp1y} ${cp2x},${cp2y} ${p2[0]},${p2[1]}`);
  }

  parts.push('Z');
  return parts.join(' ');
}
