/**
 * Spinner component - loading indicator
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: 'xs' | 'sm' | 'default' | 'md' | 'lg';
}

export function Spinner({ size = 'default', className, ...props }: SpinnerProps) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn('inline-block animate-spin rounded-full border-current border-t-transparent', {
        'h-3 w-3 border-[1.5px]': size === 'xs',
        'h-3.5 w-3.5 border-2': size === 'sm',
        'h-4 w-4 border-2': size === 'default',
        'h-5 w-5 border-2': size === 'md',
        'h-8 w-8 border-[3px]': size === 'lg',
      }, className)}
      {...props}
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
}
