/**
 * Responsive Layout Component
 * Handles mobile/tablet/desktop layouts
 */

'use client';

import { useState } from 'react';
import { useIsMobile } from '@/hooks/useResponsive';
import { MobileSidebar } from './MobileSidebar';
import { Button } from '@/components/ui/button';

interface ResponsiveLayoutProps {
  leftSidebar?: React.ReactNode;
  rightSidebar?: React.ReactNode;
  children: React.ReactNode;
  showLeftSidebar?: boolean;
  showRightSidebar?: boolean;
  onToggleLeftSidebar?: () => void;
  onToggleRightSidebar?: () => void;
}

export function ResponsiveLayout({
  leftSidebar,
  rightSidebar,
  children,
  showLeftSidebar = true,
  showRightSidebar = true,
  onToggleLeftSidebar,
  onToggleRightSidebar,
}: ResponsiveLayoutProps) {
  const isMobile = useIsMobile();
  const [mobileLeftOpen, setMobileLeftOpen] = useState(false);
  const [mobileRightOpen, setMobileRightOpen] = useState(false);

  if (isMobile) {
    return (
      <>
        {/* Mobile Header with menu buttons */}
        <div className="sticky top-0 z-30 flex items-center justify-between bg-white dark:bg-primary-900 border-b border-neutral-200 dark:border-neutral-800 px-4 py-3">
          {leftSidebar && (
            <button
              onClick={() => setMobileLeftOpen(true)}
              className="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
              aria-label="Open menu"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
          )}

          <div className="flex-1" />

          {rightSidebar && (
            <button
              onClick={() => setMobileRightOpen(true)}
              className="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
              aria-label="Open sidebar"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          )}
        </div>

        {/* Main content */}
        <div className="flex-1 overflow-hidden">{children}</div>

        {/* Mobile drawers */}
        {leftSidebar && (
          <MobileSidebar
            isOpen={mobileLeftOpen}
            onClose={() => setMobileLeftOpen(false)}
            position="left"
          >
            {leftSidebar}
          </MobileSidebar>
        )}

        {rightSidebar && (
          <MobileSidebar
            isOpen={mobileRightOpen}
            onClose={() => setMobileRightOpen(false)}
            position="right"
          >
            {rightSidebar}
          </MobileSidebar>
        )}
      </>
    );
  }

  // Desktop/Tablet layout
  return (
    <div className="flex h-full relative">
      {/* Left sidebar */}
      {leftSidebar && showLeftSidebar && (
        <div className="hidden lg:block relative">
          {leftSidebar}
          {/* Collapse button for left sidebar */}
          {onToggleLeftSidebar && (
            <button
              onClick={onToggleLeftSidebar}
              className="absolute top-1/2 -right-3 -translate-y-1/2 z-20 w-6 h-12 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-r-lg shadow-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-all flex items-center justify-center group"
              aria-label="Hide conversations"
            >
              <svg className="w-3 h-3 text-neutral-400 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          )}
        </div>
      )}
      
      {/* Collapsed left sidebar - show button */}
      {leftSidebar && !showLeftSidebar && onToggleLeftSidebar && (
        <button
          onClick={onToggleLeftSidebar}
          className="hidden lg:flex absolute left-0 top-1/2 -translate-y-1/2 z-20 w-6 h-12 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-r-lg shadow-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-all items-center justify-center group"
          aria-label="Show conversations"
        >
          <svg className="w-3 h-3 text-neutral-400 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      )}

      {/* Main content */}
      <div className="flex-1 overflow-hidden">{children}</div>

      {/* Right sidebar */}
      {rightSidebar && showRightSidebar && (
        <div className="hidden lg:block relative">
          {rightSidebar}
          {/* Collapse button for right sidebar */}
          {onToggleRightSidebar && (
            <button
              onClick={onToggleRightSidebar}
              className="absolute top-1/2 -left-3 -translate-y-1/2 z-20 w-6 h-12 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-l-lg shadow-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-all flex items-center justify-center group"
              aria-label="Hide structure"
            >
              <svg className="w-3 h-3 text-neutral-400 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </div>
      )}
      
      {/* Collapsed right sidebar - show button */}
      {rightSidebar && !showRightSidebar && onToggleRightSidebar && (
        <button
          onClick={onToggleRightSidebar}
          className="hidden lg:flex absolute right-0 top-1/2 -translate-y-1/2 z-20 w-6 h-12 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-l-lg shadow-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-all items-center justify-center group"
          aria-label="Show structure"
        >
          <svg className="w-3 h-3 text-neutral-400 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      )}
    </div>
  );
}
