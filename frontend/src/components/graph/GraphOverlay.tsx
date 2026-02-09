/**
 * GraphOverlay — Full-viewport graph overlay within the page content area.
 *
 * Renders GraphCanvas in an absolute overlay that covers the main content
 * but leaves the global sidebar visible. Supports focused node via citation click.
 */

'use client';

import { useEffect, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { GraphCanvas } from './GraphCanvas';
import type { GraphNode, GraphEdge, BackendCluster, ClusterQuality } from '@/lib/types/graph';

interface GraphOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];
  projectId: string;
  focusedNodeId: string | null;
  backendClusters?: BackendCluster[];
  clusterQuality?: ClusterQuality;
}

export function GraphOverlay({
  isOpen,
  onClose,
  graphNodes,
  graphEdges,
  projectId,
  focusedNodeId,
  backendClusters,
  clusterQuality,
}: GraphOverlayProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        e.preventDefault();
        onClose();
      }
    },
    [isOpen, onClose]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="absolute inset-0 z-40 bg-white dark:bg-neutral-950 flex flex-col"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          {/* Header bar */}
          <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200/60 dark:border-neutral-800/60 shrink-0">
            <h2 className="text-sm font-medium text-neutral-700 dark:text-neutral-200">
              Knowledge Graph
            </h2>
            <button
              onClick={onClose}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
            >
              <CloseIcon className="w-3.5 h-3.5" />
              Close
              <kbd className="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono ml-1">Esc</kbd>
            </button>
          </div>

          {/* Graph canvas fills remaining space */}
          <div className="flex-1 min-h-0">
            <GraphCanvas
              key={focusedNodeId ?? 'default'}
              graphNodes={graphNodes}
              graphEdges={graphEdges}
              projectId={projectId}
              layoutMode="clustered"
              focusedNodeId={focusedNodeId}
              backendClusters={backendClusters}
              clusterQuality={clusterQuality}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
