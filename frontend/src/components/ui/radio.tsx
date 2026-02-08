/**
 * Radio component - consistent radio button styling
 *
 * Subtle scale pop on selection via Framer Motion spring.
 * Falls back to static rendering when `prefers-reduced-motion` is active.
 */

'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { springConfig } from '@/lib/motion-config';

export interface RadioProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
}

const Radio = React.forwardRef<HTMLInputElement, RadioProps>(
  ({ className, label, id, checked, defaultChecked, onChange, ...props }, ref) => {
    const radioId = id || `radio-${React.useId()}`;
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
        type="radio"
        id={radioId}
        className={cn(
          // Base styles
          'h-4 w-4 rounded-full border transition-colors',
          // Default state
          'border-primary-300 bg-white',
          // Dark mode
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
            htmlFor={radioId}
            className="ml-2 text-sm text-primary-700 dark:text-primary-200 cursor-pointer select-none"
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
