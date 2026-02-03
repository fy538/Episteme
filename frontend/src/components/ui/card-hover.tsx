/**
 * Enhanced Card with Hover Preview
 * Cards that expand and show more info on hover
 */

'use client';

import { motion } from 'framer-motion';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface HoverCardProps {
  children: React.ReactNode;
  hoverContent?: React.ReactNode;
  className?: string;
  expandOnHover?: boolean;
}

export function HoverCard({
  children,
  hoverContent,
  className,
  expandOnHover = true,
}: HoverCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return (
      <div className={cn('group', className)}>
        {children}
        {hoverContent && (
          <div className="hidden group-hover:block mt-2">
            {hoverContent}
          </div>
        )}
      </div>
    );
  }

  return (
    <motion.div
      className={cn('group cursor-pointer', className)}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      whileHover={expandOnHover ? { scale: 1.02, y: -2 } : {}}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 20,
      }}
    >
      {children}
      
      {hoverContent && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{
            opacity: isHovered ? 1 : 0,
            height: isHovered ? 'auto' : 0,
          }}
          transition={{ duration: 0.2 }}
          className="overflow-hidden"
        >
          <div className="pt-2 border-t border-neutral-200 dark:border-neutral-700 mt-2">
            {hoverContent}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}

// Utility for adding hover shadow effect
export function useHoverShadow() {
  const prefersReducedMotion = useReducedMotion();
  
  if (prefersReducedMotion) {
    return {
      whileHover: {},
      transition: {},
    };
  }

  return {
    whileHover: {
      boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)',
    },
    transition: {
      duration: 0.2,
    },
  };
}
