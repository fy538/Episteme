/**
 * Checkbox component - consistent checkbox styling
 *
 * Subtle scale pop on check via Framer Motion spring.
 * Falls back to static rendering when `prefers-reduced-motion` is active.
 */

'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { springConfig } from '@/lib/motion-config';

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, id, checked, defaultChecked, onChange, ...props }, ref) => {
    const checkboxId = id || `checkbox-${React.useId()}`;
    const prefersReducedMotion = useReducedMotion();

    const [isChecked, setIsChecked] = React.useState(defaultChecked ?? checked ?? false);

    React.useEffect(() => {
      if (checked !== undefined) {
        setIsChecked(checked);
      }
    }, [checked]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setIsChecked(e.target.checked);
      onChange?.(e);
    };

    const inputElement = (
      <input
        type="checkbox"
        id={checkboxId}
        className={cn(
          // Base styles
          'h-4 w-4 rounded border transition-colors',
          // Default state - light mode
          'border-primary-300 bg-white',
          // Default state - dark mode
          'dark:border-neutral-600 dark:bg-neutral-900',
          // Checked state
          'checked:bg-accent-600 checked:border-accent-600',
          'dark:checked:bg-accent-500 dark:checked:border-accent-500',
          // Focus state
          'focus:outline-none focus:ring-2 focus:ring-accent-500 focus:ring-offset-2',
          'dark:focus:ring-offset-neutral-900',
          // Hover state
          'hover:border-primary-400 dark:hover:border-neutral-500',
          // Disabled state
          'disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        ref={ref}
        checked={checked}
        defaultChecked={checked === undefined ? defaultChecked : undefined}
        onChange={handleChange}
        {...props}
      />
    );

    return (
      <div className="flex items-center">
        {prefersReducedMotion ? (
          inputElement
        ) : (
          <motion.span
            style={{ display: 'inline-flex' }}
            animate={isChecked ? { scale: [1, 1.2, 1] } : { scale: 1 }}
            transition={springConfig.bouncy}
          >
            {inputElement}
          </motion.span>
        )}
        {label && (
          <label
            htmlFor={checkboxId}
            className="ml-2 text-sm text-primary-700 dark:text-primary-200 cursor-pointer select-none"
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
