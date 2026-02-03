/**
 * Network Error Banner
 * Shows when API is unreachable with retry action
 */

'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Button } from './button';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface NetworkErrorBannerProps {
  isVisible: boolean;
  onRetry: () => void;
  message?: string;
}

export function NetworkErrorBanner({
  isVisible,
  onRetry,
  message = 'Connection lost. Check if the backend is running.',
}: NetworkErrorBannerProps) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={prefersReducedMotion ? {} : { y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={prefersReducedMotion ? {} : { y: -100, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="fixed top-0 left-0 right-0 z-[100] bg-error-600 dark:bg-error-700 text-white shadow-lg"
        >
          <div className="mx-auto max-w-7xl px-4 py-3">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <svg
                  className="h-5 w-5 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div>
                  <p className="text-sm font-medium">Network Error</p>
                  <p className="text-xs opacity-90">{message}</p>
                </div>
              </div>

              <Button
                size="sm"
                onClick={onRetry}
                className="bg-white text-error-700 hover:bg-neutral-100 dark:bg-neutral-100 dark:text-error-700 dark:hover:bg-neutral-200"
              >
                Retry Connection
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
