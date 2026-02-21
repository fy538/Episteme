'use client';

import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';

interface OutcomeCheckBannerProps {
  caseTitle: string;
  outcomeCheckDate: string;  // ISO date string (YYYY-MM-DD)
  onAddNote: () => void;
  onDismiss: () => void;
}

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

/**
 * Sticky reminder banner shown when an outcome check date is approaching.
 *
 * Show when:
 * - case.status === 'decided'
 * - decision.outcome_check_date is within 7 days of today (or past due, up to 30 days)
 *
 * Amber background for upcoming, red for overdue.
 */
export function OutcomeCheckBanner({
  caseTitle,
  outcomeCheckDate,
  onAddNote,
  onDismiss,
}: OutcomeCheckBannerProps) {
  const days = daysUntil(outcomeCheckDate);
  const isOverdue = days < 0;
  const daysAbs = Math.abs(days);

  // Don't show if more than 7 days in the future or more than 30 days overdue
  if (days > 7 || days < -30) return null;

  const bgClass = isOverdue
    ? 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800'
    : 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800';

  const textClass = isOverdue
    ? 'text-red-800 dark:text-red-200'
    : 'text-amber-800 dark:text-amber-200';

  const message = isOverdue
    ? `Time to check: How did your decision on "${caseTitle}" turn out? (${daysAbs} day${daysAbs !== 1 ? 's' : ''} overdue)`
    : days === 0
    ? `Time to check: How did your decision on "${caseTitle}" turn out? (due today)`
    : `Time to check: How did your decision on "${caseTitle}" turn out? (in ${days} day${days !== 1 ? 's' : ''})`;

  return (
    <div className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${bgClass}`}>
      <span className="text-lg" aria-hidden="true">⏰</span>
      <p className={`flex-1 text-sm ${textClass}`}>
        {message}
      </p>
      <Button size="sm" variant="outline" onClick={onAddNote}>
        Add Note
      </Button>
      <button
        type="button"
        onClick={onDismiss}
        className="text-neutral-400 hover:text-neutral-600 dark:text-neutral-500 dark:hover:text-neutral-300 transition-colors p-1"
        aria-label="Dismiss reminder"
      >
        ✕
      </button>
    </div>
  );
}

/**
 * Hook to manage banner dismissal per session.
 * Uses sessionStorage so the banner reappears next session.
 */
export function useOutcomeCheckDismiss(caseId: string) {
  const storageKey = `outcome-check-dismissed-${caseId}`;
  const [isDismissed, setIsDismissed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return sessionStorage.getItem(storageKey) === 'true';
  });

  const dismiss = useCallback(() => {
    setIsDismissed(true);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem(storageKey, 'true');
    }
  }, [storageKey]);

  return { isDismissed, dismiss };
}
