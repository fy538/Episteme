/**
 * Card Preview Component
 * Shows expandable preview on hover with smooth animations
 */

'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface CardPreviewProps {
  children: React.ReactNode;
  preview: React.ReactNode;
  className?: string;
  expandOnHover?: boolean;
  showShadow?: boolean;
}

export function CardPreview({
  children,
  preview,
  className,
  expandOnHover = true,
  showShadow = true,
}: CardPreviewProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return (
      <div 
        className={cn('group', className)}
        onMouseEnter={() => setIsExpanded(true)}
        onMouseLeave={() => setIsExpanded(false)}
      >
        {children}
        {isExpanded && (
          <div className="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700">
            {preview}
          </div>
        )}
      </div>
    );
  }

  return (
    <motion.div
      className={cn('cursor-pointer', className)}
      onHoverStart={() => setIsExpanded(true)}
      onHoverEnd={() => setIsExpanded(false)}
      whileHover={
        expandOnHover
          ? {
              scale: 1.02,
              y: -4,
              boxShadow: showShadow
                ? '0 10px 30px rgba(0, 0, 0, 0.1)'
                : undefined,
            }
          : {}
      }
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 25,
      }}
    >
      {children}
      
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700">
              {preview}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
