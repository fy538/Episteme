/**
 * CitationBadge — small inline pill that replaces [N] markers in rendered markdown.
 *
 * Hover: tooltip with document title + excerpt preview.
 * Click: navigates to the source document chunk.
 * Built on @floating-ui/react, matching CitationPopover pattern.
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
import type { SourceChunk } from '@/lib/types/chat';

interface CitationBadgeProps {
  /** Citation number (1-indexed for display) */
  index: number;
  /** The source chunk metadata */
  chunk: SourceChunk;
  /** Called when badge is clicked */
  onClick?: (chunk: SourceChunk) => void;
}

export function CitationBadge({ index, chunk, onClick }: CitationBadgeProps) {
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

  return (
    <>
      <button
        ref={refs.setReference}
        {...getReferenceProps({
          onClick: () => onClick?.(chunk),
        })}
        className="inline-flex items-center justify-center min-w-[1.25rem] h-[1.125rem] px-1 text-[10px] font-semibold leading-none rounded-full bg-accent-100 text-accent-700 hover:bg-accent-200 dark:bg-accent-900/50 dark:text-accent-300 dark:hover:bg-accent-800/60 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent-600 dark:focus-visible:outline-accent-400 cursor-pointer transition-colors align-super -mt-1 mx-0.5"
        aria-label={`Source ${index}: ${chunk.document_title}`}
      >
        {index}
      </button>
      {isOpen && (
        <FloatingPortal>
          <div
            ref={refs.setFloating}
            style={floatingStyles}
            {...getFloatingProps()}
            className="z-50 w-72 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-lg p-3 text-left"
          >
            {/* Document badge */}
            <div className="flex items-center gap-1.5">
              <span className="inline-block text-xs font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-accent-100 text-accent-800 dark:bg-accent-900/40 dark:text-accent-300">
                Source {index}
              </span>
              {chunk.similarity != null && (
                <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
                  {Math.round(chunk.similarity * 100)}% match
                </span>
              )}
            </div>

            {/* Document title */}
            <p className="mt-1.5 text-xs font-medium text-neutral-800 dark:text-neutral-200 truncate">
              {chunk.document_title}
            </p>

            {/* Excerpt preview */}
            <p className="mt-1 text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed line-clamp-3">
              {chunk.excerpt}
            </p>

            {/* Chunk location */}
            <p className="mt-1.5 text-[10px] text-neutral-400 dark:text-neutral-500">
              Chunk {chunk.chunk_index}
            </p>
          </div>
        </FloatingPortal>
      )}
    </>
  );
}
