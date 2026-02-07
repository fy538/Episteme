/**
 * Action Item Card
 *
 * Highlights the top priority next step on the home page.
 * Shows heading, reason, impact, and a link to the relevant case.
 */

'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import type { BriefActionItem } from '@/hooks/useTodaysBrief';

interface ActionItemCardProps {
  item: BriefActionItem;
  className?: string;
}

const severityStyles = {
  high: {
    border: 'border-warning-200/60 dark:border-warning-800/40',
    bg: 'bg-warning-50/40 dark:bg-warning-950/20',
    icon: 'text-warning-500 dark:text-warning-400',
    label: 'text-warning-600 dark:text-warning-400',
  },
  medium: {
    border: 'border-accent-200/60 dark:border-accent-800/40',
    bg: 'bg-accent-50/30 dark:bg-accent-950/20',
    icon: 'text-accent-500 dark:text-accent-400',
    label: 'text-accent-600 dark:text-accent-400',
  },
  low: {
    border: 'border-neutral-200/60 dark:border-neutral-700/40',
    bg: 'bg-neutral-50/50 dark:bg-neutral-800/30',
    icon: 'text-neutral-400 dark:text-neutral-500',
    label: 'text-neutral-500 dark:text-neutral-400',
  },
};

export function ActionItemCard({ item, className }: ActionItemCardProps) {
  const styles = severityStyles[item.severity];

  return (
    <Link
      href={`/cases/${item.caseId}`}
      className={cn(
        'group block rounded-lg border p-4 transition-colors',
        styles.border,
        styles.bg,
        'hover:border-neutral-300/80 dark:hover:border-neutral-600/60',
        className
      )}
    >
      {/* Top row: icon + heading + case title */}
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0">
          {item.type === 'tension' ? (
            <WarningIcon className={cn('w-4 h-4', styles.icon)} />
          ) : item.type === 'blind_spot' ? (
            <EyeIcon className={cn('w-4 h-4', styles.icon)} />
          ) : (
            <PlayIcon className={cn('w-4 h-4', styles.icon)} />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <h3 className="text-sm font-medium text-primary-900 dark:text-primary-50">
              {item.heading}
            </h3>
            {item.caseTitle && item.type !== 'continue' && (
              <span className="text-xs text-neutral-400 dark:text-neutral-500 truncate">
                {item.caseTitle}
              </span>
            )}
          </div>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
            {item.reason}
          </p>
          <div className="flex items-center justify-between mt-2">
            <span className={cn('text-[11px] font-medium', styles.label)}>
              {item.impact}
            </span>
            <span className="text-xs text-neutral-400 dark:text-neutral-500 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors flex items-center gap-1">
              Open case
              <ArrowRightIcon className="w-3 h-3" />
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}

// --- Icons ---

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 9v4M12 17h.01" strokeLinecap="round" />
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    </svg>
  );
}

function EyeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
    </svg>
  );
}

function PlayIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}

function ArrowRightIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
