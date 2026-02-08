/**
 * Settings Shell — Reusable modal layout for all settings UIs
 *
 * Provides consistent layout: sidebar tabs + scrollable content area + footer.
 * Uses Framer Motion for backdrop fade, modal scale-in, and tab content crossfade.
 * Used by SettingsModal.
 */

'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { easingCurves, transitionDurations } from '@/lib/motion-config';

export interface SettingsTab {
  id: string;
  label: string;
  icon: React.ReactNode;
}

interface SettingsShellProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
  isSaving?: boolean;
  title: string;
  tabs: SettingsTab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  children: React.ReactNode;
  /** Smaller variant for project/case settings with fewer tabs */
  compact?: boolean;
}

export function SettingsShell({
  isOpen,
  onClose,
  onSave,
  isSaving = false,
  title,
  tabs,
  activeTab,
  onTabChange,
  children,
  compact = false,
}: SettingsShellProps) {
  const prefersReducedMotion = useReducedMotion();

  // Close on Escape
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, onClose]);

  const modalMaxWidth = compact ? 'max-w-2xl' : 'max-w-4xl';
  const sidebarWidth = compact ? 'w-44' : 'w-52';

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/50"
            initial={prefersReducedMotion ? { opacity: 1 } : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0 }}
            transition={{ duration: transitionDurations.fast }}
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            className={cn(
              'relative bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl w-full flex overflow-hidden',
              modalMaxWidth,
              compact ? 'max-h-[80vh]' : 'max-h-[90vh]'
            )}
            initial={prefersReducedMotion ? {} : { opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={prefersReducedMotion ? {} : { opacity: 0, scale: 0.96, y: 8 }}
            transition={{
              duration: transitionDurations.normal,
              ease: easingCurves.easeOutExpo,
            }}
          >
            {/* Sidebar */}
            <div className={cn(
              'flex-shrink-0 bg-neutral-50 dark:bg-neutral-800/50 border-r border-neutral-200 dark:border-neutral-700 flex flex-col',
              sidebarWidth
            )}>
              <div className="p-5 pb-3">
                <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
                  {title}
                </h2>
              </div>
              <nav className="flex-1 px-3 pb-4 space-y-0.5">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => onTabChange(tab.id)}
                    className={cn(
                      'w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 flex items-center gap-2.5',
                      activeTab === tab.id
                        ? 'bg-white dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100 shadow-sm ring-1 ring-neutral-200/50 dark:ring-neutral-600/50'
                        : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200 hover:bg-white/60 dark:hover:bg-neutral-700/40'
                    )}
                  >
                    <span className={cn(
                      'flex-shrink-0 transition-colors',
                      activeTab === tab.id
                        ? 'text-accent-600 dark:text-accent-400'
                        : ''
                    )}>
                      {tab.icon}
                    </span>
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>

            {/* Main content area */}
            <div className="flex-1 flex flex-col min-w-0">
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  {tabs.find(t => t.id === activeTab)?.label}
                </h3>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
                  aria-label="Close"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Tab content with crossfade */}
              <div className="flex-1 overflow-y-auto">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeTab}
                    className="p-6"
                    initial={prefersReducedMotion ? {} : { opacity: 0, x: 8 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={prefersReducedMotion ? {} : { opacity: 0, x: -8 }}
                    transition={{
                      duration: 0.2,
                      ease: easingCurves.easeOutExpo,
                    }}
                  >
                    {children}
                  </motion.div>
                </AnimatePresence>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50/50 dark:bg-neutral-800/30">
                <Button variant="ghost" size="sm" onClick={onClose}>
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={onSave}
                  isLoading={isSaving}
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
