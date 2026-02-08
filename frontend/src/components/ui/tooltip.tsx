/**
 * Tooltip component - hover information
 *
 * Uses Framer Motion for smooth scale + fade entrance from the anchor direction.
 * Falls back to instant show/hide when `prefers-reduced-motion` is active.
 */

'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { easingCurves, transitionDurations } from '@/lib/motion-config';

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: 'top' | 'right' | 'bottom' | 'left';
}

const originMap = {
  top: { originX: 0.5, originY: 1 },
  bottom: { originX: 0.5, originY: 0 },
  left: { originX: 1, originY: 0.5 },
  right: { originX: 0, originY: 0.5 },
};

export function Tooltip({ content, children, side = 'top' }: TooltipProps) {
  const [isVisible, setIsVisible] = React.useState(false);
  const prefersReducedMotion = useReducedMotion();
  const origin = originMap[side];

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onFocus={() => setIsVisible(true)}
        onBlur={() => setIsVisible(false)}
      >
        {children}
      </div>

      <AnimatePresence>
        {isVisible && (
          <motion.div
            className={cn(
              'absolute z-50 px-3 py-2 text-sm text-white bg-primary-900 rounded-md shadow-lg whitespace-nowrap',
              {
                'bottom-full left-1/2 -translate-x-1/2 mb-2': side === 'top',
                'top-full left-1/2 -translate-x-1/2 mt-2': side === 'bottom',
                'left-full top-1/2 -translate-y-1/2 ml-2': side === 'right',
                'right-full top-1/2 -translate-y-1/2 mr-2': side === 'left',
              }
            )}
            style={{ originX: origin.originX, originY: origin.originY }}
            initial={prefersReducedMotion ? { opacity: 1 } : { opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.92 }}
            transition={{
              duration: transitionDurations.fast,
              ease: easingCurves.easeOutExpo,
            }}
          >
            {content}
            {/* Arrow */}
            <div
              className={cn('absolute w-2 h-2 bg-primary-900 transform rotate-45', {
                'top-full left-1/2 -translate-x-1/2 -mt-1': side === 'top',
                'bottom-full left-1/2 -translate-x-1/2 -mb-1': side === 'bottom',
                'top-1/2 right-full -translate-y-1/2 -mr-1': side === 'right',
                'top-1/2 left-full -translate-y-1/2 -ml-1': side === 'left',
              })}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
