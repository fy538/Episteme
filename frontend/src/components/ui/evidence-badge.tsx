/**
 * Evidence Badge - specialized badge for evidence types
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export type EvidenceType = 'metric' | 'benchmark' | 'fact' | 'claim' | 'quote';

export interface EvidenceBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  type: EvidenceType;
}

const evidenceStyles: Record<EvidenceType, string> = {
  metric: 'bg-primary-100 text-primary-700 border-primary-200 dark:bg-primary-900/50 dark:text-primary-300 dark:border-primary-700',
  benchmark: 'bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900/50 dark:text-purple-300 dark:border-purple-700',
  fact: 'bg-success-100 text-success-700 border-success-200 dark:bg-success-900/50 dark:text-success-300 dark:border-success-700',
  claim: 'bg-warning-100 text-warning-700 border-warning-200 dark:bg-warning-900/50 dark:text-warning-300 dark:border-warning-700',
  quote: 'bg-pink-100 text-pink-700 border-pink-200 dark:bg-pink-900/50 dark:text-pink-300 dark:border-pink-700',
};

const evidenceLabels: Record<EvidenceType, string> = {
  metric: 'Metric',
  benchmark: 'Benchmark',
  fact: 'Fact',
  claim: 'Claim',
  quote: 'Quote',
};

function EvidenceBadge({ type, className, children, ...props }: EvidenceBadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
        evidenceStyles[type],
        className
      )}
      {...props}
    >
      {children || evidenceLabels[type]}
    </div>
  );
}

export { EvidenceBadge };
