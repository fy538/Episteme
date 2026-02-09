/**
 * RecentDecisionCard
 *
 * Shows the user's most recently active decision as a wider card
 * below the hero input on the home page. Clicking navigates to the case.
 */

'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import type { RecentDecision } from '@/hooks/useHomeDashboard';
import type { CaseStage } from '@/lib/types/plan';

interface RecentDecisionCardProps {
  decision: RecentDecision;
}

const STAGE_CONFIG: Record<CaseStage, { label: string; color: string }> = {
  exploring: {
    label: 'Exploring',
    color: 'bg-neutral-400',
  },
  investigating: {
    label: 'Investigating',
    color: 'bg-info-500',
  },
  synthesizing: {
    label: 'Synthesizing',
    color: 'bg-warning-500',
  },
  ready: {
    label: 'Ready',
    color: 'bg-success-500',
  },
};

export function RecentDecisionCard({ decision }: RecentDecisionCardProps) {
  const stage = STAGE_CONFIG[decision.stage];
  const hasInquiries = decision.inquiryProgress.total > 0;
  const hasCriteria = decision.criteriaProgress.total > 0;

  return (
    <Link
      href={`/cases/${decision.caseId}`}
      className={cn(
        'block w-full rounded-lg border p-4',
        'border-neutral-200 dark:border-neutral-800',
        'bg-neutral-50 dark:bg-neutral-900/50',
        'hover:border-accent-300 dark:hover:border-accent-700',
        'hover:bg-accent-50/50 dark:hover:bg-accent-900/30',
        'transition-all duration-150',
        'group'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <div className={cn('w-2 h-2 rounded-full shrink-0', stage.color)} />
            <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
              {stage.label}
            </span>
          </div>
          <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
            {decision.title}
          </h3>
          <div className="flex items-center gap-3 mt-1.5 text-xs text-neutral-500 dark:text-neutral-400">
            {hasInquiries && (
              <span>
                {decision.inquiryProgress.resolved}/{decision.inquiryProgress.total} inquiries
              </span>
            )}
            {hasCriteria && (
              <span>
                {decision.criteriaProgress.met}/{decision.criteriaProgress.total} criteria
              </span>
            )}
            <span>{formatRelativeTime(decision.updatedAt)}</span>
          </div>
        </div>

        <span
          className={cn(
            'text-xs font-medium px-2.5 py-1 rounded-md shrink-0',
            'text-accent-700 dark:text-accent-300',
            'bg-accent-100 dark:bg-accent-900/40',
            'opacity-0 group-hover:opacity-100 transition-opacity duration-150'
          )}
        >
          Resume
        </span>
      </div>
    </Link>
  );
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);

  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
