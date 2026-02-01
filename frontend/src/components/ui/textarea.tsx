/**
 * Textarea component - multi-line text inputs
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          // Base styles
          'flex min-h-[80px] w-full rounded-md border px-3 py-2',
          'text-sm transition-colors',
          'placeholder:text-neutral-400',
          'resize-y',
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

Textarea.displayName = 'Textarea';

export { Textarea };
