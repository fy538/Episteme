/**
 * Micro-interactions Library
 * Small delightful animations for feedback
 */

'use client';

import { motion } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { springConfig } from '@/lib/motion-config';

interface PulseProps {
  children: React.ReactNode;
  trigger?: boolean;
  color?: string;
}

export function Pulse({ children, trigger, color = '#14b8a6' }: PulseProps) {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return <>{children}</>;
  }

  return (
    <motion.div
      animate={
        trigger
          ? {
              scale: [1, 1.05, 1],
              boxShadow: [
                '0 0 0 0px rgba(20, 184, 166, 0)',
                '0 0 0 8px rgba(20, 184, 166, 0.3)',
                '0 0 0 0px rgba(20, 184, 166, 0)',
              ],
            }
          : {}
      }
      transition={{ duration: 0.6 }}
    >
      {children}
    </motion.div>
  );
}

interface WobbleProps {
  children: React.ReactNode;
  trigger?: boolean;
}

export function Wobble({ children, trigger }: WobbleProps) {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return <>{children}</>;
  }

  return (
    <motion.div
      animate={
        trigger
          ? {
              rotate: [0, -10, 10, -10, 10, 0],
              transition: { duration: 0.5 },
            }
          : {}
      }
    >
      {children}
    </motion.div>
  );
}

interface BounceProps {
  children: React.ReactNode;
  trigger?: boolean;
}

export function Bounce({ children, trigger }: BounceProps) {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return <>{children}</>;
  }

  return (
    <motion.div
      animate={
        trigger
          ? {
              y: [0, -20, 0],
              transition: springConfig.bouncy,
            }
          : {}
      }
    >
      {children}
    </motion.div>
  );
}

interface ShakeProps {
  children: React.ReactNode;
  trigger?: boolean;
}

export function Shake({ children, trigger }: ShakeProps) {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return <>{children}</>;
  }

  return (
    <motion.div
      animate={
        trigger
          ? {
              x: [0, -10, 10, -10, 10, 0],
              transition: { duration: 0.4 },
            }
          : {}
      }
    >
      {children}
    </motion.div>
  );
}

interface GlowProps {
  children: React.ReactNode;
  active?: boolean;
  color?: string;
}

export function Glow({ children, active, color = '#14b8a6' }: GlowProps) {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return <>{children}</>;
  }

  return (
    <motion.div
      animate={{
        boxShadow: active
          ? `0 0 20px ${color}40, 0 0 40px ${color}20`
          : '0 0 0px rgba(0, 0, 0, 0)',
      }}
      transition={{ duration: 0.3 }}
    >
      {children}
    </motion.div>
  );
}

// Hook for triggering micro-interactions
export function useMicroInteraction() {
  const [trigger, setTrigger] = React.useState(false);

  const fire = () => {
    setTrigger(true);
    setTimeout(() => setTrigger(false), 100);
  };

  return { trigger, fire };
}

// Add missing React import
import * as React from 'react';
