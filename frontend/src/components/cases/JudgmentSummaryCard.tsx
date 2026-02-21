'use client';

import { useQuery } from '@tanstack/react-query';
import { casesAPI } from '@/lib/api/cases';
import { cn } from '@/lib/utils';

interface JudgmentSummaryCardProps {
  caseId: string;
}

const CONFIDENCE_LABELS: Record<number, { label: string; color: string }> = {
  1: { label: 'Low', color: 'text-error-500' },
  2: { label: 'Doubts', color: 'text-warning-500' },
  3: { label: 'Moderate', color: 'text-info-500' },
  4: { label: 'High', color: 'text-success-500' },
};

const GROUNDING_LABELS: Record<string, { label: string; color: string }> = {
  empty: { label: 'No evidence', color: 'text-neutral-400' },
  weak: { label: 'Weak', color: 'text-warning-500' },
  moderate: { label: 'Some evidence', color: 'text-info-500' },
  strong: { label: 'Strong', color: 'text-success-500' },
  conflicted: { label: 'Conflicted', color: 'text-error-500' },
};

export function JudgmentSummaryCard({ caseId }: JudgmentSummaryCardProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['section-judgment-summary', caseId],
    queryFn: () => casesAPI.getSectionJudgmentSummary(caseId),
    staleTime: 10_000,
  });

  if (isLoading) return null;
  if (isError) return (
    <p className="text-xs text-error-500" role="alert">Failed to load judgment summary.</p>
  );
  if (!data || data.rated_count === 0) return null;

  return (
    <div className="space-y-3">
      {/* Per-section comparison */}
      <div className="space-y-1">
        {data.sections.map(section => {
          const conf = section.user_confidence ? CONFIDENCE_LABELS[section.user_confidence] : null;
          const grounding = GROUNDING_LABELS[section.grounding_status] || GROUNDING_LABELS.empty;
          const hasMismatch = data.mismatches.some(m => m.section_id === section.section_id);

          return (
            <div
              key={section.section_id}
              className={cn(
                'flex items-center justify-between px-3 py-2 rounded-lg text-sm',
                hasMismatch
                  ? 'bg-warning-50/80 dark:bg-warning-900/20 border border-warning-200/60 dark:border-warning-800/60'
                  : 'bg-neutral-50/50 dark:bg-neutral-900/30'
              )}
            >
              <span className="text-neutral-700 dark:text-neutral-300 truncate flex-1 mr-3">
                {section.heading}
              </span>
              <div className="flex items-center gap-4 shrink-0">
                <div className="text-xs">
                  <span className="text-neutral-400 mr-1">You:</span>
                  {conf ? (
                    <span className={conf.color}>{conf.label}</span>
                  ) : (
                    <span className="text-neutral-300 dark:text-neutral-600">-</span>
                  )}
                </div>
                <div className="text-xs">
                  <span className="text-neutral-400 mr-1">Evidence:</span>
                  <span className={grounding.color}>{grounding.label}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Mismatches */}
      {data.mismatches.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-warning-600 dark:text-warning-400 uppercase tracking-wide">
            Worth noting
          </p>
          {data.mismatches.map(m => (
            <div
              key={m.section_id}
              className="text-xs text-warning-700 dark:text-warning-300 px-3 py-2 rounded bg-warning-50 dark:bg-warning-900/20"
            >
              <span className="font-medium">{m.heading}:</span> {m.description}
            </div>
          ))}
        </div>
      )}

      {/* Progress */}
      <p className="text-xs text-neutral-400">
        {data.rated_count} of {data.total_count} sections rated
      </p>
    </div>
  );
}
