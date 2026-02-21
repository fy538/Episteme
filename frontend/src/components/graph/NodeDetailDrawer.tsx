/**
 * NodeDetailDrawer — Slide-in panel on the right when a node is selected.
 *
 * Shows:
 *   - Full node content
 *   - Type, status, confidence
 *   - Source provenance (document, chunk)
 *   - Connected edges with neighbor previews
 *   - Actions: change status, edit content (future)
 */

'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { GraphNode, GraphEdge, NodeType } from '@/lib/types/graph';
import { NODE_TYPE_CONFIG, NODE_STATUS_CONFIG, EDGE_TYPE_CONFIG } from './graph-config';

interface NodeDetailDrawerProps {
  node: GraphNode;
  edges: GraphEdge[];
  neighbors: GraphNode[];
  projectId: string;
  onClose: () => void;
  onNavigateToNode: (nodeId: string) => void;
  /** When provided, renders an "Ask about this" button that bridges to the chat panel */
  onAskAboutNode?: (node: GraphNode) => void;
}

export function NodeDetailDrawer({
  node,
  edges,
  neighbors,
  projectId,
  onClose,
  onNavigateToNode,
  onAskAboutNode,
}: NodeDetailDrawerProps) {
  const typeConfig = NODE_TYPE_CONFIG[node.node_type];
  const statusConfig = NODE_STATUS_CONFIG[node.status];
  const neighborMap = new Map(neighbors.map(n => [n.id, n]));

  // Group edges by type
  const supportingEdges = edges.filter(e => e.edge_type === 'supports');
  const contradictingEdges = edges.filter(e => e.edge_type === 'contradicts');
  const dependencyEdges = edges.filter(e => e.edge_type === 'depends_on');

  return (
    <motion.aside
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 360, opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      transition={{ duration: 0.2, ease: [0.25, 1, 0.5, 1] }}
      className="h-full border-l border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 overflow-hidden flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200/60 dark:border-neutral-800/60">
        <div className="flex items-center gap-2">
          <span className={cn(
            'inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold uppercase tracking-wider',
            typeConfig.badgeBg, typeConfig.badgeText,
          )}>
            <NodeTypeIcon path={typeConfig.icon} className="w-3 h-3" />
            {typeConfig.label}
          </span>
          <span className="flex items-center gap-1">
            <span className={cn('w-2 h-2 rounded-full', statusConfig.dotColor)} />
            <span className={cn('text-xs font-medium', statusConfig.textClass)}>
              {statusConfig.label}
            </span>
          </span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="h-7 w-7 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
          aria-label="Close detail panel"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" />
          </svg>
        </Button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        {/* Content */}
        <section>
          <SectionLabel>Content</SectionLabel>
          <p className="text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
            {node.content}
          </p>
        </section>

        {/* Confidence */}
        <section>
          <SectionLabel>Confidence</SectionLabel>
          <div className="flex items-center gap-3">
            <div className="flex-1 h-2 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all',
                  node.confidence >= 0.7 ? 'bg-success-500' :
                  node.confidence >= 0.4 ? 'bg-warning-500' :
                  'bg-rose-500'
                )}
                style={{ width: `${node.confidence * 100}%` }}
              />
            </div>
            <span className="text-sm font-medium text-neutral-600 dark:text-neutral-300 w-10 text-right">
              {Math.round(node.confidence * 100)}%
            </span>
          </div>
        </section>

        {/* Properties */}
        {node.properties && Object.keys(node.properties).length > 0 && (
          <section>
            <SectionLabel>Properties</SectionLabel>
            <div className="space-y-1">
              {node.properties.importance && (
                <PropertyRow label="Importance" value={`${node.properties.importance}/3`} />
              )}
              {node.properties.document_role && (
                <PropertyRow label="Role" value={node.properties.document_role} />
              )}
              {node.properties.load_bearing !== undefined && (
                <PropertyRow label="Load-bearing" value={node.properties.load_bearing ? 'Yes' : 'No'} />
              )}
              {node.properties.severity && (
                <PropertyRow label="Severity" value={node.properties.severity} />
              )}
              {node.properties.tension_type && (
                <PropertyRow label="Type" value={node.properties.tension_type} />
              )}
              {node.properties.evidence_type && (
                <PropertyRow label="Evidence type" value={node.properties.evidence_type} />
              )}
            </div>
          </section>
        )}

        {/* Source provenance */}
        {node.source_document_title && (
          <section>
            <SectionLabel>Source</SectionLabel>
            <div className="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
              <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <path d="M14 2v6h6" />
              </svg>
              <span>{node.source_document_title}</span>
            </div>
            <div className="mt-1 text-xs text-neutral-400 dark:text-neutral-500">
              {node.source_type.replace('_', ' ')} &middot; {node.scope}
            </div>
          </section>
        )}

        {/* Ask about this — bridges graph exploration to chat */}
        {onAskAboutNode && (
          <section>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onAskAboutNode(node)}
              className={cn(
                'w-full flex items-center justify-center gap-2 text-sm font-medium',
                'text-accent-700 dark:text-accent-300',
                'bg-accent-50 dark:bg-accent-900/30',
                'hover:bg-accent-100 dark:hover:bg-accent-900/50',
                'border-accent-200/60 dark:border-accent-800/40',
              )}
            >
              <ChatIcon className="w-3.5 h-3.5" />
              Ask about this
            </Button>
          </section>
        )}

        {/* Connected edges */}
        {edges.length > 0 && (
          <section>
            <SectionLabel>Connections ({edges.length})</SectionLabel>
            <div className="space-y-3">
              {supportingEdges.length > 0 && (
                <EdgeGroup
                  label="Supports"
                  edges={supportingEdges}
                  currentNodeId={node.id}
                  neighborMap={neighborMap}
                  color="emerald"
                  onNavigate={onNavigateToNode}
                />
              )}
              {contradictingEdges.length > 0 && (
                <EdgeGroup
                  label="Contradicts"
                  edges={contradictingEdges}
                  currentNodeId={node.id}
                  neighborMap={neighborMap}
                  color="rose"
                  onNavigate={onNavigateToNode}
                />
              )}
              {dependencyEdges.length > 0 && (
                <EdgeGroup
                  label="Depends on"
                  edges={dependencyEdges}
                  currentNodeId={node.id}
                  neighborMap={neighborMap}
                  color="slate"
                  onNavigate={onNavigateToNode}
                />
              )}
            </div>
          </section>
        )}

        {/* Metadata */}
        <section className="pt-2 border-t border-neutral-200/60 dark:border-neutral-800/60">
          <div className="text-xs text-neutral-400 dark:text-neutral-500 space-y-0.5">
            <div>Created: {new Date(node.created_at).toLocaleDateString()}</div>
            <div>Updated: {new Date(node.updated_at).toLocaleDateString()}</div>
            <div className="font-mono">{node.id.slice(0, 8)}...</div>
          </div>
        </section>
      </div>
    </motion.aside>
  );
}

// ── Sub-components ───────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs uppercase tracking-wider font-semibold text-neutral-400 dark:text-neutral-500 mb-2">
      {children}
    </h3>
  );
}

function PropertyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-neutral-500 dark:text-neutral-400">{label}</span>
      <span className="font-medium text-neutral-700 dark:text-neutral-300 capitalize">{value}</span>
    </div>
  );
}

function EdgeGroup({
  label,
  edges,
  currentNodeId,
  neighborMap,
  color,
  onNavigate,
}: {
  label: string;
  edges: GraphEdge[];
  currentNodeId: string;
  neighborMap: Map<string, GraphNode>;
  color: 'emerald' | 'rose' | 'slate';
  onNavigate: (nodeId: string) => void;
}) {
  const colorClasses = {
    emerald: 'text-success-600 dark:text-success-400 border-success-200 dark:border-success-800/50',
    rose: 'text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-800/50',
    slate: 'text-neutral-600 dark:text-neutral-400 border-neutral-200 dark:border-neutral-700',
  };

  return (
    <div>
      <span className={cn('text-xs font-medium uppercase tracking-wider', colorClasses[color].split(' ').slice(0, 2).join(' '))}>
        {label} ({edges.length})
      </span>
      <div className="mt-1 space-y-1">
        {edges.map(edge => {
          const neighborId = edge.source_node === currentNodeId ? edge.target_node : edge.source_node;
          const neighbor = neighborMap.get(neighborId);
          if (!neighbor) return null;

          const neighborType = NODE_TYPE_CONFIG[neighbor.node_type];

          return (
            <Button
              key={edge.id}
              variant="outline"
              size="sm"
              onClick={() => onNavigate(neighborId)}
              className={cn(
                'w-full flex items-start gap-2 p-2 h-auto justify-start',
                'hover:bg-neutral-50 dark:hover:bg-neutral-800/50',
                colorClasses[color],
              )}
            >
              <span className={cn('mt-0.5 shrink-0', neighborType.textClass)}>
                <NodeTypeIcon path={neighborType.icon} className="w-3 h-3" />
              </span>
              <span className="text-xs text-neutral-700 dark:text-neutral-300 line-clamp-2 leading-tight text-left">
                {neighbor.content}
              </span>
            </Button>
          );
        })}
      </div>
    </div>
  );
}

function NodeTypeIcon({ path, className }: { path: string; className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d={path} />
    </svg>
  );
}

function ChatIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
