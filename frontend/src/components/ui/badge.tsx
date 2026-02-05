/**
 * Badge component - labels and status indicators
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'neutral' | 'outline';
}

function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
        'focus:outline-none focus:ring-2 focus:ring-offset-2',
        {
          'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300': variant === 'default',
          'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300': variant === 'success',
          'bg-warning-100 text-warning-700 dark:bg-warning-900 dark:text-warning-300': variant === 'warning',
          'bg-error-100 text-error-700 dark:bg-error-900 dark:text-error-300': variant === 'error',
          'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300': variant === 'neutral',
          'border border-neutral-300 bg-white text-neutral-700 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300': variant === 'outline',
        },
        className
      )}
      {...props}
    />
  );
}

export { Badge };
