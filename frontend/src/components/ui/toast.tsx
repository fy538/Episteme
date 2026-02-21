/**
 * Toast component - non-blocking notifications
 * Enhanced with smoother animations
 *
 * Icons bounce in with spring physics after the toast slides in.
 */

'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { easingCurves, transitionDurations, springConfig } from '@/lib/motion-config';

export interface Toast {
  id: string;
  title?: string;
  description?: string;
  variant?: 'default' | 'success' | 'error' | 'warning';
  duration?: number;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const addToast = React.useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newToast = { ...toast, id };
    setToasts((prev) => [...prev, newToast]);

    // Auto-remove after duration
    if (toast.duration !== 0) {
      setTimeout(() => {
        removeToast(id);
      }, toast.duration || 5000);
    }
  }, []);

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}

function ToastContainer({
  toasts,
  onRemove,
}: {
  toasts: Toast[];
  onRemove: (id: string) => void;
}) {
  return (
    <div className="fixed bottom-0 right-0 z-50 p-4 space-y-2 max-w-md w-full pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
        ))}
      </AnimatePresence>
    </div>
  );
}

/** Bouncy icon wrapper — pops in after the toast has slid into view */
function AnimatedIcon({
  children,
  shouldAnimate,
}: {
  children: React.ReactNode;
  shouldAnimate: boolean;
}) {
  if (!shouldAnimate) return <>{children}</>;
  return (
    <motion.div
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      transition={{
        ...springConfig.bouncy,
        delay: 0.15,
      }}
    >
      {children}
    </motion.div>
  );
}

function ToastItem({
  toast,
  onRemove,
}: {
  toast: Toast;
  onRemove: (id: string) => void;
}) {
  const prefersReducedMotion = useReducedMotion();

  const content = (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border p-4 shadow-xl pointer-events-auto',
        'backdrop-blur-md bg-white/95 dark:bg-primary-900/95',
        'border-neutral-200/50 dark:border-neutral-700/50',
        {
          'border-l-4 border-l-accent-600': toast.variant === 'default',
          'border-l-4 border-l-success-600': toast.variant === 'success',
          'border-l-4 border-l-error-600': toast.variant === 'error',
          'border-l-4 border-l-warning-600': toast.variant === 'warning',
        }
      )}
    >
      {/* Icon */}
      <div className="flex-shrink-0 mt-0.5">
        <AnimatedIcon shouldAnimate={!prefersReducedMotion}>
          {toast.variant === 'success' && (
            <svg className="w-5 h-5 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          )}
          {toast.variant === 'error' && (
            <svg className="w-5 h-5 text-error-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          )}
          {toast.variant === 'warning' && (
            <svg className="w-5 h-5 text-warning-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          )}
          {(!toast.variant || toast.variant === 'default') && (
            <svg className="w-5 h-5 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </AnimatedIcon>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {toast.title && (
          <p className="font-semibold text-primary-900 dark:text-primary-50">
            {toast.title}
          </p>
        )}
        {toast.description && (
          <p className="text-sm text-primary-600 dark:text-primary-400 mt-1">
            {toast.description}
          </p>
        )}
      </div>

      {/* Close button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => onRemove(toast.id)}
        className="flex-shrink-0 h-auto w-auto text-primary-400 hover:text-primary-600 dark:text-primary-500 dark:hover:text-primary-300"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </Button>
    </div>
  );

  if (prefersReducedMotion) {
    return content;
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.15 } }}
      transition={{
        duration: transitionDurations.normal,
        ease: easingCurves.easeOutCubic,
      }}
    >
      {content}
    </motion.div>
  );
}
