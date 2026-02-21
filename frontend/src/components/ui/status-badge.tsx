/**
 * Status Badge - specialized badge for assumption/investigation status
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export type StatusType = 'untested' | 'investigating' | 'validated';

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: StatusType;
}

const statusStyles: Record<StatusType, string> = {
  untested: 'bg-warning-100 text-warning-800 border-warning-300 dark:bg-warning-900/50 dark:text-warning-300 dark:border-warning-700',
  investigating: 'bg-info-100 text-info-800 border-info-300 dark:bg-info-900/50 dark:text-info-300 dark:border-info-700',
  validated: 'bg-success-100 text-success-800 border-success-300 dark:bg-success-900/50 dark:text-success-300 dark:border-success-700',
};

const statusLabels: Record<StatusType, string> = {
  untested: 'Untested',
  investigating: 'Investigating',
  validated: 'Validated',
};

const statusIcons: Record<StatusType, React.ReactNode> = {
  untested: (
    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  investigating: (
    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  validated: (
    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
};

function StatusBadge({ status, className, children, ...props }: StatusBadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        statusStyles[status],
        className
      )}
      {...props}
    >
      {statusIcons[status]}
      {children || statusLabels[status]}
    </div>
  );
}

export { StatusBadge };
