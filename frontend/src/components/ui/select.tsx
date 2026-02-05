/**
 * Select component - dropdown with consistent styling
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, error, children, ...props }, ref) => {
    return (
      <select
        className={cn(
          // Base styles
          'flex h-10 w-full rounded-md border px-3 py-2',
          'text-sm transition-colors',
          // Light mode
          'bg-white text-neutral-900',
          // Dark mode
          'dark:bg-primary-900 dark:text-primary-50 dark:border-neutral-700',
          // Focus styles
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
          'dark:focus-visible:ring-offset-primary-900',
          // Default state
          'border-primary-300',
          'focus-visible:ring-accent-500',
          // Error state
          error && 'border-error-500 focus-visible:ring-error-500',
          // Disabled state
          'disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-neutral-50',
          'dark:disabled:bg-neutral-800',
          // Appearance
          'appearance-none bg-no-repeat bg-right pr-10',
          // Custom arrow via background (light mode)
          `bg-[url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")]`,
          // Dark mode arrow
          `dark:bg-[url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%239ca3af' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")]`,
          'bg-[length:1.25rem] bg-[right_0.5rem_center]',
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </select>
    );
  }
);

Select.displayName = 'Select';

export { Select };
