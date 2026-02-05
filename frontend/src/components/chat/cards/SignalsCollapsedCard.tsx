/**
 * SignalsCollapsedCard - Collapsed view of extracted signals after a message
 *
 * Shows a compact preview of signals that can be expanded.
 */

'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import type { InlineActionCard, SignalsCollapsedData } from '@/lib/types/chat';

interface SignalsCollapsedCardProps {
  card: InlineActionCard;
  onExpand?: () => void;
  onSignalClick?: (signalText: string) => void;
}

const SIGNAL_TYPE_COLORS: Record<string, string> = {
  Assumption: 'text-amber-600 dark:text-amber-400',
  Question: 'text-purple-600 dark:text-purple-400',
  Claim: 'text-blue-600 dark:text-blue-400',
  Goal: 'text-green-600 dark:text-green-400',
  Constraint: 'text-red-600 dark:text-red-400',
  DecisionIntent: 'text-cyan-600 dark:text-cyan-400',
  EvidenceMention: 'text-indigo-600 dark:text-indigo-400',
};

export function SignalsCollapsedCard({
  card,
  onExpand,
  onSignalClick,
}: SignalsCollapsedCardProps) {
  const [expanded, setExpanded] = useState(false);
  const data = card.data as unknown as SignalsCollapsedData;
  const { signals, totalCount } = data;

  const previewSignals = signals.slice(0, 3);
  const remainingCount = totalCount - previewSignals.length;

  const handleToggle = () => {
    setExpanded(!expanded);
    if (!expanded && onExpand) {
      onExpand();
    }
  };

  return (
    <div className="my-2 mx-4">
      <div
        className={cn(
          'border rounded-md bg-neutral-50 dark:bg-primary-900/50',
          'border-neutral-200 dark:border-neutral-700',
          'transition-all duration-200'
        )}
      >
        {/* Header - always visible */}
        <button
          onClick={handleToggle}
          className="w-full px-3 py-2 flex items-center justify-between hover:bg-neutral-100 dark:hover:bg-primary-800/50 transition-colors rounded-t-md"
        >
          <div className="flex items-center gap-2">
            <span className="text-neutral-500 dark:text-neutral-400 text-sm">
              #
            </span>
            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Signals
            </span>
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              ({totalCount})
            </span>
          </div>
          <span className="text-xs text-neutral-400">
            {expanded ? '[-]' : '[+]'}
          </span>
        </button>

        {/* Collapsed preview */}
        {!expanded && (
          <div className="px-3 pb-2">
            <div className="flex flex-wrap gap-1.5 text-xs">
              {previewSignals.map((signal, i) => (
                <button
                  key={i}
                  onClick={() => onSignalClick?.(signal.text)}
                  className={cn(
                    'px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-primary-800',
                    'hover:bg-neutral-200 dark:hover:bg-primary-700',
                    'transition-colors truncate max-w-[150px]',
                    SIGNAL_TYPE_COLORS[signal.type] || 'text-neutral-600'
                  )}
                  title={signal.text}
                >
                  {signal.text.length > 20 ? signal.text.slice(0, 20) + '...' : signal.text}
                </button>
              ))}
              {remainingCount > 0 && (
                <span className="px-2 py-0.5 text-neutral-500 dark:text-neutral-400">
                  +{remainingCount} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Expanded full list */}
        {expanded && (
          <div className="px-3 pb-3 space-y-1 max-h-48 overflow-y-auto">
            {signals.map((signal, i) => (
              <button
                key={i}
                onClick={() => onSignalClick?.(signal.text)}
                className={cn(
                  'w-full text-left px-2 py-1.5 rounded text-sm',
                  'bg-neutral-100 dark:bg-primary-800',
                  'hover:bg-neutral-200 dark:hover:bg-primary-700',
                  'transition-colors'
                )}
              >
                <div className="flex items-start gap-2">
                  <span className={cn('text-xs font-medium', SIGNAL_TYPE_COLORS[signal.type])}>
                    [{signal.type}]
                  </span>
                  <span className="text-neutral-700 dark:text-neutral-300 flex-1">
                    {signal.text}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
