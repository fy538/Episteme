/**
 * Dialog component - reusable modal
 * Enhanced with smooth animations
 */

'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from './button';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { easingCurves, transitionDurations } from '@/lib/motion-config';

export interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  showClose?: boolean;
}

export function Dialog({
  isOpen,
  onClose,
  title,
  description,
  children,
  size = 'md',
  showClose = true,
}: DialogProps) {
  // Close on escape
  React.useEffect(() => {
    if (!isOpen) return;

    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }

    // Prevent body scroll when dialog is open
    document.body.classList.add('dialog-open');

    window.addEventListener('keydown', handleEscape);
    return () => {
      window.removeEventListener('keydown', handleEscape);
      document.body.classList.remove('dialog-open');
    };
  }, [isOpen, onClose]);

  const prefersReducedMotion = useReducedMotion();

  if (!isOpen) return null;

  const dialogContent = (
    <div
      className={cn(
        'bg-white dark:bg-primary-900 rounded-lg shadow-xl w-full',
        {
          'max-w-sm': size === 'sm',
          'max-w-md': size === 'md',
          'max-w-2xl': size === 'lg',
          'max-w-4xl': size === 'xl',
          'max-w-full m-4': size === 'full',
        }
      )}
      onClick={(e) => e.stopPropagation()}
    >
        {/* Header */}
        {(title || showClose) && (
          <div className="flex items-center justify-between p-6 border-b border-neutral-200">
            <div>
              {title && (
                <h2 className="text-xl font-display font-semibold tracking-tight text-primary-900">{title}</h2>
              )}
              {description && (
                <p className="text-sm text-primary-600 mt-1">{description}</p>
              )}
            </div>
            {showClose && (
              <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </Button>
            )}
          </div>
        )}

        {/* Content */}
        <div className="p-6">{children}</div>
      </div>
  );

  if (prefersReducedMotion) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
        onClick={onClose}
      >
        {dialogContent}
      </div>
    );
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: transitionDurations.fast }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{
            duration: transitionDurations.normal,
            ease: easingCurves.easeOutCubic,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {dialogContent}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export interface DialogFooterProps extends React.HTMLAttributes<HTMLDivElement> {}

export function DialogFooter({ className, ...props }: DialogFooterProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-end gap-3 border-t border-neutral-200 bg-neutral-50 px-6 py-4 -mx-6 -mb-6 mt-6',
        className
      )}
      {...props}
    />
  );
}
