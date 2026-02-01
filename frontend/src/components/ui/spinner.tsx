/**
 * Spinner component - loading indicator
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'default' | 'lg';
}

export function Spinner({ size = 'default', className, ...props }: SpinnerProps) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn('inline-block animate-spin rounded-full border-2 border-current border-t-transparent', {
        'h-4 w-4 border-2': size === 'sm',
        'h-6 w-6 border-2': size === 'default',
        'h-8 w-8 border-[3px]': size === 'lg',
      }, className)}
      {...props}
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
}
