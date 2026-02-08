/**
 * Switch component - toggle switch for boolean options
 *
 * Uses Framer Motion spring physics for a bouncy thumb transition.
 * Falls back to CSS translate when `prefers-reduced-motion` is active.
 */

import * as React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { springConfig } from '@/lib/motion-config';

export interface SwitchProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  onCheckedChange?: (checked: boolean) => void;
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, label, id, onCheckedChange, onChange, checked, defaultChecked, ...props }, ref) => {
    const switchId = id || `switch-${React.useId()}`;
    const prefersReducedMotion = useReducedMotion();

    // Track checked state locally so Framer Motion can animate the thumb.
    // Supports both controlled (`checked` prop) and uncontrolled (`defaultChecked`) modes.
    const [isChecked, setIsChecked] = React.useState(defaultChecked ?? checked ?? false);

    React.useEffect(() => {
      if (checked !== undefined) {
        setIsChecked(checked);
      }
    }, [checked]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setIsChecked(e.target.checked);
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
            checked={checked}
            defaultChecked={checked === undefined ? defaultChecked : undefined}
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
            {prefersReducedMotion ? (
              /* Reduced motion: instant CSS translate */
              <span
                className={cn(
                  'inline-block h-5 w-5 rounded-full bg-white shadow-sm',
                  'mt-0.5',
                  isChecked ? 'translate-x-[1.375rem]' : 'translate-x-0.5'
                )}
              />
            ) : (
              /* Full motion: spring-animated thumb */
              <motion.span
                className="inline-block h-5 w-5 rounded-full bg-white shadow-sm mt-0.5"
                animate={{ x: isChecked ? 22 : 2 }}
                transition={springConfig.bouncy}
              />
            )}
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
