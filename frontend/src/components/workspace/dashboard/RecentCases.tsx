/**
 * Recent Cases
 *
 * Shows a focused list of recent/important cases (not exhaustive).
 * For full navigation, use the sidebar.
 */

'use client';

import Link from 'next/link';
import { ReadinessMeter } from '@/components/ui/readiness-meter';
import { cn } from '@/lib/utils';
import type { Case, Inquiry } from '@/lib/types/case';

interface CaseWithInquiries extends Case {
  inquiries: Inquiry[];
  readinessScore: number;
  tensionsCount: number;
  blindSpotsCount: number;
}

interface RecentCasesProps {
  cases: CaseWithInquiries[];
  maxItems?: number;
  className?: string;
}

export function RecentCases({
  cases,
  maxItems = 5,
  className,
}: RecentCasesProps) {
  // Sort by updated_at (most recent first) and take top items
  const sortedCases = [...cases]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, maxItems);

  if (sortedCases.length === 0) {
    return (
      <div className={cn('text-center py-8', className)}>
        <p className="text-neutral-500 dark:text-neutral-400 text-sm">
          No recent cases
        </p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {sortedCases.map((caseItem) => (
        <RecentCaseCard key={caseItem.id} caseItem={caseItem} />
      ))}
    </div>
  );
}

function RecentCaseCard({ caseItem }: { caseItem: CaseWithInquiries }) {
  const isReady = caseItem.readinessScore >= 90 && caseItem.tensionsCount === 0;
  const resolvedInquiries = caseItem.inquiries.filter(i => i.status === 'resolved').length;

  return (
    <Link
      href={`/workspace/cases/${caseItem.id}`}
      className="flex items-center justify-between p-3 border border-neutral-200 dark:border-neutral-800 rounded-lg hover:border-accent-300 dark:hover:border-accent-700 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors group"
    >
      <div className="flex items-center gap-3 min-w-0">
        {isReady ? (
          <CheckCircleIcon className="w-5 h-5 text-success-500 flex-shrink-0" />
        ) : (
          <CircleIcon className="w-5 h-5 text-neutral-300 dark:text-neutral-600 flex-shrink-0" />
        )}
        <div className="min-w-0">
          <h3 className="font-medium text-primary-900 dark:text-primary-50 truncate group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors">
            {caseItem.title}
          </h3>
          <div className="flex items-center gap-2 mt-0.5">
            {caseItem.tensionsCount > 0 && (
              <span className="text-xs text-warning-600 dark:text-warning-400">
                {caseItem.tensionsCount} tension{caseItem.tensionsCount !== 1 ? 's' : ''}
              </span>
            )}
            {caseItem.blindSpotsCount > 0 && (
              <span className="text-xs text-accent-600 dark:text-accent-400">
                {caseItem.blindSpotsCount} blind spot{caseItem.blindSpotsCount !== 1 ? 's' : ''}
              </span>
            )}
            {caseItem.tensionsCount === 0 && caseItem.blindSpotsCount === 0 && (
              <span className="text-xs text-neutral-500 dark:text-neutral-400">
                {resolvedInquiries}/{caseItem.inquiries.length} inquiries resolved
              </span>
            )}
          </div>
        </div>
      </div>

      <ReadinessMeter
        score={caseItem.readinessScore}
        inquiries={{
          total: caseItem.inquiries.length,
          resolved: resolvedInquiries,
        }}
        variant="minimal"
      />
    </Link>
  );
}

// Icons
function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
    </svg>
  );
}

export default RecentCases;
