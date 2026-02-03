/**
 * Page transition template
 * Provides smooth animations between route changes
 */

'use client';

import { motion } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { easingCurves, transitionDurations } from '@/lib/motion-config';

export default function Template({ children }: { children: React.ReactNode }) {
  const prefersReducedMotion = useReducedMotion();

  // Skip animations if user prefers reduced motion
  if (prefersReducedMotion) {
    return <>{children}</>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: transitionDurations.normal,
        ease: easingCurves.easeOutExpo,
      }}
    >
      {children}
    </motion.div>
  );
}
