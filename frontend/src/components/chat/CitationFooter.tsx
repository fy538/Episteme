/**
 * CitationFooter — collapsible source list rendered below assistant messages.
 *
 * Collapsed: one-line "Sources: Doc A, Doc B" summary.
 * Expanded: each source with excerpt, document title, similarity score.
 * Each source is clickable for navigation.
 */

'use client';

import * as React from 'react';
import type { SourceChunk } from '@/lib/types/chat';

interface CitationFooterProps {
  chunks: SourceChunk[];
  /** Called when a source chunk is clicked (e.g. navigate to document) */
  onChunkClick?: (chunk: SourceChunk) => void;
}

export function CitationFooter({ chunks, onChunkClick }: CitationFooterProps) {
  const [expanded, setExpanded] = React.useState(false);

  if (!chunks.length) return null;

  // Deduplicate by document title for the collapsed summary
  const uniqueDocTitles = [...new Set(chunks.map((c) => c.document_title))];
  const summaryText = uniqueDocTitles.length <= 3
    ? uniqueDocTitles.join(', ')
    : `${uniqueDocTitles.slice(0, 2).join(', ')} +${uniqueDocTitles.length - 2} more`;

  return (
    <div className="mt-2 rounded-md border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900 text-xs">
      {/* Collapsed header — always visible */}
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-neutral-100 dark:hover:bg-neutral-800 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent-600 rounded-md transition-colors"
        aria-expanded={expanded}
        aria-label={`${expanded ? 'Collapse' : 'Expand'} ${chunks.length} source${chunks.length > 1 ? 's' : ''}`}
      >
        <svg
          className={`w-3.5 h-3.5 text-neutral-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <span className="font-medium text-neutral-500 dark:text-neutral-400">
          Grounded in {chunks.length} source{chunks.length > 1 ? 's' : ''}
        </span>
        <span className="text-neutral-400 dark:text-neutral-500 truncate">
          {summaryText}
        </span>
      </button>

      {/* Expanded source list */}
      {expanded && (
        <div className="px-3 pb-2 space-y-1.5">
          {chunks.map((chunk) => (
            <button
              key={chunk.chunk_id}
              onClick={() => onChunkClick?.(chunk)}
              className="w-full text-left rounded-md px-2.5 py-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors group"
            >
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center justify-center min-w-[1.25rem] h-[1.125rem] px-1 text-[10px] font-semibold leading-none rounded-full bg-accent-100 text-accent-700 dark:bg-accent-900/50 dark:text-accent-300">
                  {chunk.index + 1}
                </span>
                <span className="font-medium text-neutral-700 dark:text-neutral-300 truncate">
                  {chunk.document_title}
                </span>
                {chunk.similarity != null && (
                  <span className="ml-auto text-[10px] text-neutral-400 dark:text-neutral-500 shrink-0">
                    {Math.round(chunk.similarity * 100)}%
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-neutral-500 dark:text-neutral-400 line-clamp-2 pl-6">
                {chunk.excerpt}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
