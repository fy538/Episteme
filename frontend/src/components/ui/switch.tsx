/**
 * Switch component - toggle switch for boolean options
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SwitchProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  onCheckedChange?: (checked: boolean) => void;
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, label, id, onCheckedChange, onChange, ...props }, ref) => {
    const switchId = id || `switch-${Math.random().toString(36).substr(2, 9)}`;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange?.(e);
      onCheckedChange?.(e.target.checked);
    };

    return (
      <div className="flex items-center">
        <label
          htmlFor={switchId}
          className={cn(
            'relative inline-flex h-6 w-11 cursor-pointer items-center rounded-full transition-colors',
            'focus-within:outline-none focus-within:ring-2 focus-within:ring-accent-500 focus-within:ring-offset-2',
            className
          )}
        >
          <input
            type="checkbox"
            id={switchId}
            className="peer sr-only"
            onChange={handleChange}
            ref={ref}
            {...props}
          />
          <span
            className={cn(
              'inline-block h-6 w-11 rounded-full transition-colors',
              'peer-checked:bg-accent-600',
              'peer-disabled:cursor-not-allowed peer-disabled:opacity-50',
              'bg-primary-300'
            )}
          >
            <span
              className={cn(
                'inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform',
                'translate-x-0.5',
                'peer-checked:translate-x-[1.375rem]'
              )}
            />
          </span>
        </label>
        {label && (
          <span className="ml-3 text-sm text-primary-700">{label}</span>
        )}
      </div>
    );
  }
);

Switch.displayName = 'Switch';

export { Switch };
