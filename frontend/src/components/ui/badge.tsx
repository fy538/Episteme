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
          'bg-primary-100 text-primary-700': variant === 'default',
          'bg-success-100 text-success-700': variant === 'success',
          'bg-warning-100 text-warning-700': variant === 'warning',
          'bg-error-100 text-error-700': variant === 'error',
          'bg-neutral-100 text-neutral-700': variant === 'neutral',
          'border border-neutral-300 bg-white text-neutral-700': variant === 'outline',
        },
        className
      )}
      {...props}
    />
  );
}

export { Badge };
