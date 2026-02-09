/**
 * Graph visual configuration — colors, sizes, and style mappings
 * for each node type, status, and edge type.
 */

import type { NodeType, NodeStatus, EdgeType } from '@/lib/types/graph';

// ── Node type visual config ──────────────────────────────────

export interface NodeTypeConfig {
  label: string;
  bgClass: string;
  borderClass: string;
  textClass: string;
  badgeBg: string;
  badgeText: string;
  icon: string; // SVG path data
}

export const NODE_TYPE_CONFIG: Record<NodeType, NodeTypeConfig> = {
  claim: {
    label: 'Claim',
    bgClass: 'bg-blue-50 dark:bg-blue-950/40',
    borderClass: 'border-blue-200 dark:border-blue-800/60',
    textClass: 'text-blue-700 dark:text-blue-300',
    badgeBg: 'bg-blue-100 dark:bg-blue-900/60',
    badgeText: 'text-blue-700 dark:text-blue-300',
    icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z', // check-circle
  },
  evidence: {
    label: 'Evidence',
    bgClass: 'bg-emerald-50 dark:bg-emerald-950/40',
    borderClass: 'border-emerald-200 dark:border-emerald-800/60',
    textClass: 'text-emerald-700 dark:text-emerald-300',
    badgeBg: 'bg-emerald-100 dark:bg-emerald-900/60',
    badgeText: 'text-emerald-700 dark:text-emerald-300',
    icon: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
  },
  assumption: {
    label: 'Assumption',
    bgClass: 'bg-amber-50 dark:bg-amber-950/40',
    borderClass: 'border-amber-200 dark:border-amber-800/60',
    textClass: 'text-amber-700 dark:text-amber-300',
    badgeBg: 'bg-amber-100 dark:bg-amber-900/60',
    badgeText: 'text-amber-700 dark:text-amber-300',
    icon: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z',
  },
  tension: {
    label: 'Tension',
    bgClass: 'bg-rose-50 dark:bg-rose-950/40',
    borderClass: 'border-rose-200 dark:border-rose-800/60',
    textClass: 'text-rose-700 dark:text-rose-300',
    badgeBg: 'bg-rose-100 dark:bg-rose-900/60',
    badgeText: 'text-rose-700 dark:text-rose-300',
    icon: 'M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z', // bolt
  },
};

// ── Node status visual config ────────────────────────────────

export interface NodeStatusConfig {
  label: string;
  dotColor: string;
  textClass: string;
}

export const NODE_STATUS_CONFIG: Record<NodeStatus, NodeStatusConfig> = {
  // Claim statuses
  supported: { label: 'Supported', dotColor: 'bg-emerald-500', textClass: 'text-emerald-600 dark:text-emerald-400' },
  contested: { label: 'Contested', dotColor: 'bg-amber-500', textClass: 'text-amber-600 dark:text-amber-400' },
  unsubstantiated: { label: 'Unsubstantiated', dotColor: 'bg-neutral-400', textClass: 'text-neutral-500 dark:text-neutral-400' },
  // Evidence statuses
  confirmed: { label: 'Confirmed', dotColor: 'bg-emerald-500', textClass: 'text-emerald-600 dark:text-emerald-400' },
  uncertain: { label: 'Uncertain', dotColor: 'bg-amber-500', textClass: 'text-amber-600 dark:text-amber-400' },
  disputed: { label: 'Disputed', dotColor: 'bg-rose-500', textClass: 'text-rose-600 dark:text-rose-400' },
  // Assumption statuses
  untested: { label: 'Untested', dotColor: 'bg-neutral-400', textClass: 'text-neutral-500 dark:text-neutral-400' },
  assumption_confirmed: { label: 'Confirmed', dotColor: 'bg-emerald-500', textClass: 'text-emerald-600 dark:text-emerald-400' },
  challenged: { label: 'Challenged', dotColor: 'bg-amber-500', textClass: 'text-amber-600 dark:text-amber-400' },
  refuted: { label: 'Refuted', dotColor: 'bg-rose-500', textClass: 'text-rose-600 dark:text-rose-400' },
  // Tension statuses
  surfaced: { label: 'Surfaced', dotColor: 'bg-rose-500', textClass: 'text-rose-600 dark:text-rose-400' },
  acknowledged: { label: 'Acknowledged', dotColor: 'bg-amber-500', textClass: 'text-amber-600 dark:text-amber-400' },
  resolved: { label: 'Resolved', dotColor: 'bg-emerald-500', textClass: 'text-emerald-600 dark:text-emerald-400' },
};

// ── Edge type visual config ──────────────────────────────────

export interface EdgeTypeConfig {
  label: string;
  strokeColor: string;
  strokeDasharray?: string;
  markerEnd: string;
  animated: boolean;
}

export const EDGE_TYPE_CONFIG: Record<EdgeType, EdgeTypeConfig> = {
  supports: {
    label: 'Supports',
    strokeColor: '#10b981', // emerald-500
    markerEnd: 'supports-arrow',
    animated: false,
  },
  contradicts: {
    label: 'Contradicts',
    strokeColor: '#f43f5e', // rose-500
    strokeDasharray: '6 3',
    markerEnd: 'contradicts-arrow',
    animated: false,
  },
  depends_on: {
    label: 'Depends on',
    strokeColor: '#94a3b8', // slate-400
    strokeDasharray: '3 3',
    markerEnd: 'depends-arrow',
    animated: false,
  },
};

// ── Zoom level thresholds ────────────────────────────────────

export const ZOOM_THRESHOLDS = {
  /** Below this: compact pill rendering */
  compact: 0.4,
  /** Below this: summary card (type + status + truncated content) */
  summary: 0.75,
  /** Above this: full detail card */
  // detail: implied (> summary)
} as const;

// ── Node sizing by importance ────────────────────────────────

export const NODE_DIMENSIONS = {
  compact: { width: 140, height: 36 },
  summary: { width: 220, height: 80 },
  detail: { width: 280, height: 120 },
} as const;

// Importance determines which zoom level a node appears at
export const IMPORTANCE_VISIBILITY: Record<number, number> = {
  3: 0,       // Always visible
  2: 0.35,    // Visible at medium zoom
  1: 0.65,    // Visible only at close zoom
};

// ── Cluster config ───────────────────────────────────────────

export const CLUSTER_CONFIG = {
  /** Padding inside cluster boundary */
  padding: 24,
  /** Border radius for cluster background */
  borderRadius: 16,
  /** How many nodes before we collapse to cluster summary */
  collapseThreshold: 8,
  /** Super-node sizing for collapsed clusters */
  superNodeMinWidth: 180,
  superNodeMinHeight: 120,
  superNodeMaxWidth: 300,
} as const;

// ── Hull overlay config ──────────────────────────────────────

export const HULL_CONFIG = {
  padding: 25,
  fillOpacity: 0.08,
  strokeOpacity: 0.25,
  strokeWidth: 1.5,
  labelFontSize: 11,
} as const;

// ── Node type hex colors (for hulls, minimap, etc.) ──────────

export const NODE_TYPE_HEX: Record<NodeType, string> = {
  claim: '#3b82f6',
  evidence: '#10b981',
  assumption: '#f59e0b',
  tension: '#f43f5e',
};
