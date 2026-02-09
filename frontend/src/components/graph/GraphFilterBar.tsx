/**
 * GraphFilterBar — Filter chips for node types + layout mode toggle.
 *
 * Floats in the top-right of the graph canvas.
 * Click a type chip to toggle visibility of that node type.
 * Toggle between clustered and layered layout.
 */

'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import type { GraphNode, NodeType } from '@/lib/types/graph';
import { NODE_TYPE_CONFIG } from './graph-config';
import type { LayoutMode } from './useGraphLayout';

interface GraphFilterBarProps {
  nodes: GraphNode[];
  activeTypes: NodeType[] | undefined;
  onFilterChange: (types: NodeType[] | undefined) => void;
  layoutMode: LayoutMode;
  onLayoutToggle: () => void;
  showClusters?: boolean;
  onClusterToggle?: () => void;
  className?: string;
}

const ALL_TYPES: NodeType[] = ['claim', 'evidence', 'assumption', 'tension'];

export function GraphFilterBar({
  nodes,
  activeTypes,
  onFilterChange,
  layoutMode,
  onLayoutToggle,
  showClusters,
  onClusterToggle,
  className,
}: GraphFilterBarProps) {
  // Count nodes by type — memoized since nodes array is stable between interactions
  const counts = useMemo(() => {
    const c: Record<NodeType, number> = { claim: 0, evidence: 0, assumption: 0, tension: 0 };
    for (const node of nodes) {
      c[node.node_type]++;
    }
    return c;
  }, [nodes]);

  const isAllVisible = activeTypes === undefined;

  const toggleType = (type: NodeType) => {
    if (isAllVisible) {
      // Going from "all visible" to "all except this one"
      onFilterChange(ALL_TYPES.filter(t => t !== type));
    } else if (activeTypes!.includes(type)) {
      const next = activeTypes!.filter(t => t !== type);
      onFilterChange(next.length === 0 ? undefined : next);
    } else {
      const next = [...activeTypes!, type];
      onFilterChange(next.length === ALL_TYPES.length ? undefined : next);
    }
  };

  return (
    <div className={cn('flex items-center gap-1.5', className)}>
      {/* Type filter chips */}
      {ALL_TYPES.map(type => {
        const config = NODE_TYPE_CONFIG[type];
        const count = counts[type];
        const isActive = isAllVisible || activeTypes!.includes(type);

        return (
          <button
            key={type}
            onClick={() => toggleType(type)}
            className={cn(
              'inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium',
              'border transition-all',
              isActive
                ? cn(config.badgeBg, config.badgeText, config.borderClass)
                : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 dark:text-neutral-500 border-neutral-200 dark:border-neutral-700 opacity-50',
            )}
            title={`${isActive ? 'Hide' : 'Show'} ${config.label}s`}
          >
            {config.label}
            <span className={cn(
              'ml-0.5 text-[9px]',
              isActive ? 'opacity-70' : 'opacity-40',
            )}>
              {count}
            </span>
          </button>
        );
      })}

      {/* Divider */}
      <div className="w-px h-5 bg-neutral-200 dark:bg-neutral-700 mx-1" />

      {/* Layout mode toggle */}
      <button
        onClick={onLayoutToggle}
        className={cn(
          'inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium',
          'border border-neutral-200 dark:border-neutral-700',
          'bg-white dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400',
          'hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors',
        )}
        title={`Switch to ${layoutMode === 'clustered' ? 'tree' : 'clustered'} layout`}
      >
        {layoutMode === 'clustered' ? (
          <>
            <ClusteredIcon className="w-3.5 h-3.5" />
            Clustered
          </>
        ) : (
          <>
            <LayeredIcon className="w-3.5 h-3.5" />
            Tree
          </>
        )}
      </button>

      {/* Cluster hull toggle (only in clustered mode) */}
      {layoutMode === 'clustered' && onClusterToggle && (
        <button
          onClick={onClusterToggle}
          className={cn(
            'inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium',
            'border transition-colors',
            showClusters
              ? 'border-accent-300 dark:border-accent-700 bg-accent-50 dark:bg-accent-950/40 text-accent-700 dark:text-accent-300'
              : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-400 dark:text-neutral-500',
          )}
          title={showClusters ? 'Hide cluster boundaries' : 'Show cluster boundaries'}
        >
          <HullIcon className="w-3.5 h-3.5" />
          Clusters
        </button>
      )}
    </div>
  );
}

function HullIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 3C7 3 3 7 3 12s4 9 9 9 9-4 9-9-4-9-9-9z" strokeDasharray="4 2" />
      <circle cx="8" cy="10" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="14" cy="8" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="16" cy="14" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="10" cy="15" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

function ClusteredIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <circle cx="5" cy="6" r="2" />
      <circle cx="19" cy="6" r="2" />
      <circle cx="5" cy="18" r="2" />
      <circle cx="19" cy="18" r="2" />
      <path d="M9.5 10.5L6.5 7.5M14.5 10.5l3-3M9.5 13.5l-3 3M14.5 13.5l3 3" strokeLinecap="round" />
    </svg>
  );
}

function LayeredIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="2" width="6" height="4" rx="1" />
      <rect x="3" y="10" width="6" height="4" rx="1" />
      <rect x="15" y="10" width="6" height="4" rx="1" />
      <rect x="9" y="18" width="6" height="4" rx="1" />
      <path d="M12 6v4M6 14v2a2 2 0 002 2h4M18 14v2a2 2 0 01-2 2h-4" strokeLinecap="round" />
    </svg>
  );
}
