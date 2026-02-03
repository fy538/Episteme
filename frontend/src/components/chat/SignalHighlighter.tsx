/**
 * Signal Highlighter - Inline signal highlighting in chat messages
 * 
 * Highlights assumptions, questions, and evidence as they're detected by AI.
 * Provides quick actions to convert signals into inquiries.
 */

import { useState } from 'react';
import { useFloating, offset, flip, shift, autoUpdate } from '@floating-ui/react';

export interface HighlightedSignal {
  id: string;
  type: 'assumption' | 'question' | 'evidence' | 'claim';
  start: number;
  end: number;
  text: string;
  confidence: number;
  evidence_count?: number;
  contradiction_count?: number;
}

interface SignalHighlighterProps {
  content: string;
  signals: HighlightedSignal[];
  onConvertToInquiry?: (signal: HighlightedSignal) => void;
  onDismiss?: (signalId: string) => void;
}

export function SignalHighlighter({
  content,
  signals,
  onConvertToInquiry,
  onDismiss
}: SignalHighlighterProps) {
  const [activeSignal, setActiveSignal] = useState<string | null>(null);
  const { refs, floatingStyles } = useFloating({
    open: activeSignal !== null,
    onOpenChange: (open) => {
      if (!open) setActiveSignal(null);
    },
    middleware: [offset(8), flip(), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
  });

  // Sort signals by position to handle overlaps
  const sortedSignals = [...signals].sort((a, b) => a.start - b.start);

  // Build segments: plain text and highlighted signals
  const segments: Array<{ type: 'text' | 'signal'; content: string; signal?: HighlightedSignal }> = [];
  let lastIndex = 0;

  sortedSignals.forEach(signal => {
    // Add plain text before signal
    if (signal.start > lastIndex) {
      segments.push({
        type: 'text',
        content: content.slice(lastIndex, signal.start)
      });
    }

    // Add highlighted signal
    segments.push({
      type: 'signal',
      content: content.slice(signal.start, signal.end),
      signal
    });

    lastIndex = signal.end;
  });

  // Add remaining plain text
  if (lastIndex < content.length) {
    segments.push({
      type: 'text',
      content: content.slice(lastIndex)
    });
  }

  const getSignalColor = (type: string) => {
    switch (type) {
      case 'assumption':
        return 'bg-warning-100 dark:bg-warning-900/30 border-b-2 border-warning-500';
      case 'question':
        return 'bg-accent-100 dark:bg-accent-900/30 border-b-2 border-accent-500';
      case 'evidence':
        return 'bg-success-100 dark:bg-success-900/30 border-b-2 border-success-500';
      case 'claim':
        return 'bg-neutral-100 dark:bg-neutral-800 border-b-2 border-neutral-400';
      default:
        return 'bg-neutral-100 dark:bg-neutral-800';
    }
  };

  const getSignalIcon = (type: string) => {
    switch (type) {
      case 'assumption':
        return '⚠️';
      case 'question':
        return '?';
      case 'evidence':
        return '📄';
      case 'claim':
        return '💬';
      default:
        return '';
    }
  };

  return (
    <div className="relative whitespace-pre-wrap">
      {segments.map((segment, index) => {
        if (segment.type === 'text') {
          return <span key={index}>{segment.content}</span>;
        }

        const signal = segment.signal!;
        const isActive = activeSignal === signal.id;

        return (
          <span
            key={index}
            ref={isActive ? refs.setReference : undefined}
            className={`${getSignalColor(signal.type)} cursor-pointer transition-all rounded-sm px-0.5 hover:shadow-sm relative group`}
            onClick={() => setActiveSignal(isActive ? null : signal.id)}
          >
            {segment.content}
            
            {/* Grounding badges - always visible for assumptions/claims */}
            {(signal.type === 'assumption' || signal.type === 'claim') && (
              <span className="ml-1 inline-flex items-center gap-1">
                {signal.evidence_count === 0 && (
                  <span className="inline-flex items-center px-1 py-0.5 text-[10px] font-medium bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-400 rounded">
                    ⚠ Ungrounded
                  </span>
                )}
                {signal.evidence_count! > 0 && (
                  <span className="inline-flex items-center px-1 py-0.5 text-[10px] font-medium bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-400 rounded">
                    ✓ {signal.evidence_count}
                  </span>
                )}
                {signal.contradiction_count! > 0 && (
                  <span className="inline-flex items-center px-1 py-0.5 text-[10px] font-medium bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-400 rounded">
                    ✕ {signal.contradiction_count}
                  </span>
                )}
              </span>
            )}
            
            {/* Hover indicator */}
            <span className="opacity-0 group-hover:opacity-100 transition-opacity ml-1 text-xs">
              {getSignalIcon(signal.type)}
            </span>

            {/* Floating action menu */}
            {isActive && (
              <div
                ref={refs.setFloating}
                style={floatingStyles}
                className="z-50 bg-white dark:bg-neutral-800 rounded-lg shadow-xl border border-neutral-200 dark:border-neutral-700 p-3 min-w-[250px]"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{getSignalIcon(signal.type)}</span>
                      <div>
                        <div className="font-medium text-sm capitalize">{signal.type}</div>
                        <div className="text-xs text-neutral-500">
                          {Math.round(signal.confidence * 100)}% confidence
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveSignal(null);
                      }}
                      className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="text-sm text-neutral-700 dark:text-neutral-300 py-2 border-t border-neutral-200 dark:border-neutral-700">
                    "{signal.text}"
                  </div>

                  <div className="flex flex-col gap-2 pt-2 border-t border-neutral-200 dark:border-neutral-700">
                    {onConvertToInquiry && signal.type === 'assumption' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onConvertToInquiry(signal);
                          setActiveSignal(null);
                        }}
                        className="w-full px-3 py-2 bg-accent-600 text-white rounded-md hover:bg-accent-700 transition-colors text-sm font-medium"
                      >
                        🔍 Investigate This
                      </button>
                    )}
                    
                    {onDismiss && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDismiss(signal.id);
                          setActiveSignal(null);
                        }}
                        className="w-full px-3 py-2 bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 rounded-md hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-colors text-sm"
                      >
                        Dismiss
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </span>
        );
      })}
    </div>
  );
}
