/**
 * Button component - primary interactive element
 * Enhanced with framer-motion for smooth micro-interactions
 *
 * Supports `isLoading` prop for a shimmer overlay effect.
 */

'use client';

import * as React from 'react';
import { motion, AnimatePresence, type MotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { springConfig } from '@/lib/motion-config';

export interface ButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onAnimationStart' | 'onDragStart' | 'onDragEnd' | 'onDrag'> {
  variant?: 'default' | 'outline' | 'ghost' | 'destructive' | 'success';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', isLoading = false, children, ...props }, ref) => {
    const prefersReducedMotion = useReducedMotion();

    const buttonClasses = cn(
      // Base styles
      'relative overflow-hidden inline-flex items-center justify-center rounded-md font-medium transition-all duration-200',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2',
      'disabled:pointer-events-none disabled:opacity-50',
      // Variant styles
      {
        'bg-gradient-to-br from-accent-600 to-accent-700 text-white hover:from-accent-700 hover:to-accent-800 shadow-md hover:shadow-lg dark:from-accent-700 dark:to-accent-800 dark:hover:from-accent-800 dark:hover:to-accent-900': variant === 'default',
        'border border-primary-300 bg-white text-primary-700 hover:bg-primary-50 dark:border-neutral-700 dark:bg-primary-900 dark:text-primary-200 dark:hover:bg-primary-800': variant === 'outline',
        'text-primary-700 hover:bg-primary-100 dark:text-primary-200 dark:hover:bg-primary-800': variant === 'ghost',
        'bg-error-600 text-white hover:bg-error-700 shadow-sm dark:bg-error-700 dark:hover:bg-error-800': variant === 'destructive',
        'bg-success-600 text-white hover:bg-success-700 shadow-sm dark:bg-success-700 dark:hover:bg-success-800': variant === 'success',
      },
      // Size styles
      {
        'h-10 px-4 py-2 text-sm': size === 'default',
        'h-8 px-3 text-xs': size === 'sm',
        'h-12 px-6 text-base': size === 'lg',
        'h-9 w-9': size === 'icon',
      },
      // Loading state
      isLoading && 'cursor-wait opacity-70',
      className
    );

    const shimmerOverlay = (
      <>
        <AnimatePresence>
          {isLoading && !prefersReducedMotion && (
            <motion.div
              className="absolute inset-0 rounded-md overflow-hidden pointer-events-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                animate={{ x: ['-100%', '100%'] }}
                transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
              />
            </motion.div>
          )}
        </AnimatePresence>
        {isLoading && prefersReducedMotion && (
          <div className="absolute inset-0 rounded-md bg-white/10 pointer-events-none" />
        )}
      </>
    );

    // Use regular button if reduced motion is preferred
    if (prefersReducedMotion) {
      return (
        <button
          className={buttonClasses}
          ref={ref}
          disabled={isLoading || props.disabled}
          {...props}
        >
          {children}
          {shimmerOverlay}
        </button>
      );
    }

    return (
      <motion.button
        className={buttonClasses}
        ref={ref}
        whileHover={isLoading ? {} : { scale: 1.02 }}
        whileTap={isLoading ? {} : { scale: 0.98 }}
        transition={springConfig.bouncy}
        disabled={isLoading || props.disabled}
        {...props}
      >
        {children}
        {shimmerOverlay}
      </motion.button>
    );
  }
);

Button.displayName = 'Button';

export { Button };
