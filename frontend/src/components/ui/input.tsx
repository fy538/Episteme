/**
 * Input component - text inputs with consistent styling
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          // Base styles
          'flex h-10 w-full rounded-md border px-3 py-2',
          'text-sm transition-colors',
          'file:border-0 file:bg-transparent file:text-sm file:font-medium',
          'placeholder:text-neutral-400',
          // Focus styles
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
          // Default state
          'border-primary-300 bg-white',
          'focus-visible:ring-accent-500',
          // Error state
          error && 'border-error-500 focus-visible:ring-error-500',
          // Disabled state
          'disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-neutral-50',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';

export { Input };
