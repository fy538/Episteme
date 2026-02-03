/**
 * Optimistic Update Indicator
 * Visual feedback when operations are in progress
 */

'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface OptimisticIndicatorProps {
  isOptimistic: boolean;
  position?: 'top-right' | 'bottom-right' | 'top-left' | 'bottom-left';
}

export function OptimisticIndicator({
  isOptimistic,
  position = 'bottom-right',
}: OptimisticIndicatorProps) {
  const prefersReducedMotion = useReducedMotion();

  const positionClasses = {
    'top-right': 'top-2 right-2',
    'bottom-right': 'bottom-2 right-2',
    'top-left': 'top-2 left-2',
    'bottom-left': 'bottom-2 left-2',
  };

  if (!isOptimistic) return null;

  const indicator = (
    <div
      className={`absolute ${positionClasses[position]} flex items-center gap-1.5 px-2 py-1 bg-accent-100 dark:bg-accent-900/50 text-accent-700 dark:text-accent-300 rounded text-xs font-medium`}
    >
      <div className="w-1.5 h-1.5 bg-accent-600 rounded-full animate-pulse-subtle" />
      Saving...
    </div>
  );

  if (prefersReducedMotion) {
    return indicator;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ duration: 0.15 }}
      >
        {indicator}
      </motion.div>
    </AnimatePresence>
  );
}

// Wrapper component to show optimistic state on any element
export function WithOptimisticState({
  children,
  isOptimistic,
  className,
}: {
  children: React.ReactNode;
  isOptimistic: boolean;
  className?: string;
}) {
  return (
    <div className={`relative ${className || ''}`}>
      {children}
      <OptimisticIndicator isOptimistic={isOptimistic} />
    </div>
  );
}
