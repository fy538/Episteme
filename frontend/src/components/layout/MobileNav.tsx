/**
 * Mobile Navigation Component
 * Responsive drawer/hamburger menu for mobile
 */

'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useIsMobile } from '@/hooks/useResponsive';
import { cn } from '@/lib/utils';

interface MobileNavProps {
  children: React.ReactNode;
  position?: 'left' | 'right';
}

export function MobileNav({ children, position = 'left' }: MobileNavProps) {
  const [isOpen, setIsOpen] = useState(false);
  const prefersReducedMotion = useReducedMotion();
  const isMobile = useIsMobile();

  // Close on desktop
  useEffect(() => {
    if (!isMobile && isOpen) {
      setIsOpen(false);
    }
  }, [isMobile, isOpen]);

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isMobile) {
    return null; // Only render on mobile
  }

  return (
    <>
      {/* Hamburger Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors lg:hidden"
        aria-label="Open menu"
      >
        <svg
          className="h-6 w-6 text-neutral-700 dark:text-neutral-300"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-black/50"
              onClick={() => setIsOpen(false)}
            />

            {/* Drawer */}
            <motion.div
              initial={
                prefersReducedMotion
                  ? {}
                  : {
                      x: position === 'left' ? '-100%' : '100%',
                    }
              }
              animate={{ x: 0 }}
              exit={
                prefersReducedMotion
                  ? {}
                  : {
                      x: position === 'left' ? '-100%' : '100%',
                    }
              }
              transition={{
                type: 'spring',
                stiffness: 300,
                damping: 30,
              }}
              className={cn(
                'fixed top-0 bottom-0 z-50 w-80 bg-white dark:bg-neutral-900 shadow-xl overflow-y-auto',
                position === 'left' ? 'left-0' : 'right-0'
              )}
            >
              {/* Close button */}
              <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-800">
                <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  Menu
                </h2>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors"
                  aria-label="Close menu"
                >
                  <svg
                    className="h-5 w-5 text-neutral-600 dark:text-neutral-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              {/* Content */}
              <div className="p-4">{children}</div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
