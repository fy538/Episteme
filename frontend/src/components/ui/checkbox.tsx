/**
 * Checkbox component - consistent checkbox styling
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, id, ...props }, ref) => {
    const checkboxId = id || `checkbox-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div className="flex items-center">
        <input
          type="checkbox"
          id={checkboxId}
          className={cn(
            // Base styles
            'h-4 w-4 rounded border transition-colors',
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
            htmlFor={checkboxId}
            className="ml-2 text-sm text-primary-700 cursor-pointer select-none"
          >
            {label}
          </label>
        )}
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';

export { Checkbox };
