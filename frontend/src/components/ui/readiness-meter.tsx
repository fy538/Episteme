/**
 * Readiness Meter
 *
 * Visual progress indicator for case readiness.
 * Shows score, inquiry breakdown, and blocker counts.
 */

'use client';

import { cn } from '@/lib/utils';

interface ReadinessMeterProps {
  score: number; // 0-100
  inquiries: {
    total: number;
    resolved: number;
    investigating?: number;
    open?: number;
  };
  tensionsCount?: number;
  blindSpotsCount?: number;
  variant?: 'full' | 'compact' | 'minimal';
  className?: string;
}

export function ReadinessMeter({
  score,
  inquiries,
  tensionsCount = 0,
  blindSpotsCount = 0,
  variant = 'full',
  className,
}: ReadinessMeterProps) {
  const isReady = score >= 90 && tensionsCount === 0;

  // Color based on score
  const getScoreColor = () => {
    if (isReady) return 'bg-success-500';
    if (score >= 70) return 'bg-success-500';
    if (score >= 40) return 'bg-warning-500';
    return 'bg-error-500';
  };

  const getScoreTextColor = () => {
    if (isReady) return 'text-success-600 dark:text-success-400';
    if (score >= 70) return 'text-success-600 dark:text-success-400';
    if (score >= 40) return 'text-warning-600 dark:text-warning-400';
    return 'text-error-600 dark:text-error-400';
  };

  // Minimal variant - just dots
  if (variant === 'minimal') {
    return (
      <div className={cn('flex items-center gap-1', className)}>
        {Array.from({ length: 4 }).map((_, i) => {
          const threshold = (i + 1) * 25;
          const filled = score >= threshold;
          return (
            <div
              key={i}
              className={cn(
                'w-2 h-2 rounded-full',
                filled ? getScoreColor() : 'bg-neutral-200 dark:bg-neutral-700'
              )}
            />
          );
        })}
      </div>
    );
  }

  // Compact variant - bar + percentage
  if (variant === 'compact') {
    return (
      <div className={cn('flex items-center gap-3', className)}>
        <div className="flex-1 h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
          <div
            className={cn('h-full transition-all duration-500', getScoreColor())}
            style={{ width: `${score}%` }}
          />
        </div>
        <span className={cn('text-sm font-medium tabular-nums', getScoreTextColor())}>
          {score}%
        </span>
      </div>
    );
  }

  // Full variant - bar + breakdown
  return (
    <div className={cn('space-y-3', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
          Readiness
        </h3>
        <div className="flex items-center gap-2">
          {/* Dots */}
          <div className="flex items-center gap-1">
            {Array.from({ length: 4 }).map((_, i) => {
              const threshold = (i + 1) * 25;
              const filled = score >= threshold;
              return (
                <div
                  key={i}
                  className={cn(
                    'w-2.5 h-2.5 rounded-full transition-colors',
                    filled ? getScoreColor() : 'bg-neutral-200 dark:bg-neutral-700'
                  )}
                />
              );
            })}
          </div>
          {/* Percentage */}
          <span className={cn('text-lg font-semibold tabular-nums', getScoreTextColor())}>
            {score}%
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-all duration-500 rounded-full', getScoreColor())}
          style={{ width: `${score}%` }}
        />
      </div>

      {/* Breakdown */}
      <div className="flex items-center gap-4 text-sm text-neutral-600 dark:text-neutral-400">
        <span>
          {inquiries.resolved}/{inquiries.total} inquiries
        </span>
        {tensionsCount > 0 && (
          <span className="flex items-center gap-1 text-warning-600 dark:text-warning-400">
            <TensionIcon className="w-3.5 h-3.5" />
            {tensionsCount} tension{tensionsCount !== 1 ? 's' : ''}
          </span>
        )}
        {blindSpotsCount > 0 && (
          <span className="flex items-center gap-1 text-accent-600 dark:text-accent-400">
            <BlindSpotIcon className="w-3.5 h-3.5" />
            {blindSpotsCount} blind spot{blindSpotsCount !== 1 ? 's' : ''}
          </span>
        )}
      </div>
    </div>
  );
}

// Small icons for breakdown
function TensionIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M8 2v8M8 12v2" strokeLinecap="round" />
      <path d="M4 6l4-4 4 4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function BlindSpotIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5v3M8 10v1" strokeLinecap="round" />
    </svg>
  );
}

export default ReadinessMeter;
