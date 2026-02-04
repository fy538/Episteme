/**
 * Loading Progress Bar
 * YouTube-style top bar for async operations
 */

'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface LoadingBarProps {
  isLoading: boolean;
  duration?: number; // How long to reach 90% (ms)
}

export function LoadingBar({ isLoading, duration = 2000 }: LoadingBarProps) {
  const [progress, setProgress] = useState(0);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (!isLoading) {
      // Complete to 100% then hide
      setProgress(100);
      const timer = setTimeout(() => setProgress(0), 300);
      return () => clearTimeout(timer);
    }

    // Start loading
    setProgress(0);
    
    // Gradually increase to 90% (never 100% until done)
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) return 90;
        // Exponential slowdown as we approach 90%
        const increment = (90 - prev) * 0.1;
        return prev + increment;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [isLoading]);

  if (progress === 0 && !isLoading) return null;

  if (prefersReducedMotion) {
    return (
      <div className="fixed top-0 left-0 right-0 z-[100] h-1 bg-neutral-200 dark:bg-neutral-800">
        <div
          className="h-full bg-gradient-to-r from-accent-500 to-accent-600 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
    );
  }

  return (
    <AnimatePresence>
      {(isLoading || progress > 0) && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed top-0 left-0 right-0 z-[100] h-1 bg-neutral-200 dark:bg-neutral-800"
        >
          <motion.div
            className="h-full bg-gradient-to-r from-accent-500 via-accent-600 to-accent-500 shadow-lg"
            style={{
              width: `${progress}%`,
              boxShadow: '0 0 10px rgba(20, 184, 166, 0.5)',
            }}
            initial={{ width: '0%' }}
            animate={{ width: `${progress}%` }}
            transition={{
              duration: 0.3,
              ease: 'easeOut',
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Hook for managing loading bar state
export function useLoadingBar() {
  const [isLoading, setIsLoading] = useState(false);

  const startLoading = useCallback(() => setIsLoading(true), []);
  const stopLoading = useCallback(() => setIsLoading(false), []);

  return { isLoading, startLoading, stopLoading };
}
