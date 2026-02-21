/**
 * CitationPopover — hover popover for inline citation buttons.
 *
 * Shows node type, content preview, and source document on hover.
 * Built on @floating-ui/react, matching the existing Popover pattern.
 */

'use client';

import * as React from 'react';
import {
  useFloating,
  useInteractions,
  useHover,
  useDismiss,
  useRole,
  FloatingPortal,
  offset,
  flip,
  shift,
  autoUpdate,
} from '@floating-ui/react';
import type { GraphNode, NodeType } from '@/lib/types/graph';

const TYPE_LABELS: Record<NodeType, string> = {
  claim: 'Claim',
  evidence: 'Evidence',
  assumption: 'Assumption',
  tension: 'Tension',
};

const TYPE_COLORS: Record<NodeType, string> = {
  claim: 'bg-info-100 text-info-800 dark:bg-info-900/40 dark:text-info-300',
  evidence: 'bg-success-100 text-success-800 dark:bg-success-900/40 dark:text-success-300',
  assumption: 'bg-warning-100 text-warning-800 dark:bg-warning-900/40 dark:text-warning-300',
  tension: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
};

interface CitationPopoverProps {
  node: GraphNode | undefined;
  nodeId: string;
  onClick: () => void;
  /** The rendered citation badge */
  children: React.ReactElement;
}

export function CitationPopover({ node, nodeId, onClick, children }: CitationPopoverProps) {
  const [isOpen, setIsOpen] = React.useState(false);

  const { refs, floatingStyles, context } = useFloating({
    open: isOpen,
    onOpenChange: setIsOpen,
    placement: 'top',
    middleware: [offset(6), flip(), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
  });

  const hover = useHover(context, { delay: { open: 300, close: 100 } });
  const dismiss = useDismiss(context);
  const role = useRole(context, { role: 'tooltip' });

  const { getReferenceProps, getFloatingProps } = useInteractions([
    hover,
    dismiss,
    role,
  ]);

  const nodeType = node?.node_type ?? 'claim';

  return (
    <>
      {React.cloneElement(children, {
        ref: refs.setReference,
        ...getReferenceProps({ onClick }),
      })}
      {isOpen && node && (
        <FloatingPortal>
          <div
            ref={refs.setFloating}
            style={floatingStyles}
            {...getFloatingProps()}
            className="z-50 w-64 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-lg p-3 text-left"
          >
            {/* Type badge */}
            <span className={`inline-block text-xs font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded ${TYPE_COLORS[nodeType]}`}>
              {TYPE_LABELS[nodeType]}
            </span>

            {/* Content preview */}
            <p className="mt-1.5 text-xs text-neutral-700 dark:text-neutral-300 leading-relaxed line-clamp-3">
              {node.content}
            </p>

            {/* Source document */}
            {node.source_document_title && (
              <p className="mt-1.5 text-xs text-neutral-400 dark:text-neutral-500 truncate">
                Source: {node.source_document_title}
              </p>
            )}

            {/* Status */}
            {node.status && node.status !== 'supported' && (
              <span className="mt-1 inline-block text-xs text-neutral-400 dark:text-neutral-500">
                Status: {node.status}
              </span>
            )}
          </div>
        </FloatingPortal>
      )}
    </>
  );
}
