/**
 * Radio component - consistent radio button styling
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface RadioProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
}

const Radio = React.forwardRef<HTMLInputElement, RadioProps>(
  ({ className, label, id, ...props }, ref) => {
    const radioId = id || `radio-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div className="flex items-center">
        <input
          type="radio"
          id={radioId}
          className={cn(
            // Base styles
            'h-4 w-4 rounded-full border transition-colors',
            // Default state
            'border-primary-300 bg-white',
            // Checked state
            'checked:bg-accent-600 checked:border-accent-600',
            // Focus state
            'focus:outline-none focus:ring-2 focus:ring-accent-500 focus:ring-offset-2',
            // Hover state
            'hover:border-primary-400',
            // Disabled state
            'disabled:cursor-not-allowed disabled:opacity-50',
            className
          )}
          ref={ref}
          {...props}
        />
        {label && (
          <label
            htmlFor={radioId}
            className="ml-2 text-sm text-primary-700 cursor-pointer select-none"
          >
            {label}
          </label>
        )}
      </div>
    );
  }
);

Radio.displayName = 'Radio';

export { Radio };
