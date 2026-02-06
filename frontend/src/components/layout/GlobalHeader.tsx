/**
 * Global Header - consistent navigation across all pages
 * Provides spatial consistency and orientation
 */

'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Breadcrumbs, type BreadcrumbItem } from '@/components/ui/breadcrumbs';
import { cn } from '@/lib/utils';

interface GlobalHeaderProps {
  breadcrumbs?: BreadcrumbItem[];
  showNav?: boolean;
  rightActions?: React.ReactNode;
  onOpenSearch?: () => void;
}

export function GlobalHeader({
  breadcrumbs,
  showNav = true,
  rightActions,
  onOpenSearch,
}: GlobalHeaderProps) {
  const pathname = usePathname();
  const [isMac, setIsMac] = useState(true);

  // Detect OS for keyboard shortcut display
  useEffect(() => {
    setIsMac(navigator.platform.toUpperCase().indexOf('MAC') >= 0);
  }, []);

  const isActive = (path: string) => pathname?.startsWith(path);

  // Handle search button click - trigger global ⌘K
  const handleSearchClick = () => {
    if (onOpenSearch) {
      onOpenSearch();
    } else {
      // Dispatch keyboard event to trigger global handler
      const event = new KeyboardEvent('keydown', {
        key: 'k',
        metaKey: isMac,
        ctrlKey: !isMac,
        bubbles: true,
      });
      window.dispatchEvent(event);
    }
  };

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-neutral-200/50 dark:border-neutral-800/50 backdrop-blur-lg bg-white/90 dark:bg-primary-900/90">
        <div className="px-4 md:px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Left: Logo & Nav */}
            <div className="flex items-center gap-8">
              <Link href="/workspace" className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-accent-600 to-accent-700 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-lg">E</span>
                </div>
                <span className="text-xl font-display font-semibold tracking-tight text-primary-900 dark:text-primary-50">Episteme</span>
              </Link>

              {/* Search Button */}
              <button
                onClick={handleSearchClick}
                className="hidden md:flex items-center gap-2 px-3 py-1.5 text-sm text-neutral-500 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-lg transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <span>Search...</span>
                <kbd className="ml-2 px-1.5 py-0.5 text-xs font-medium bg-white dark:bg-neutral-900 rounded border border-neutral-300 dark:border-neutral-600">
                  {isMac ? '⌘' : 'Ctrl'}K
                </kbd>
              </button>

              {showNav && (
                <nav className="hidden md:flex items-center gap-1">
                  <Link href="/chat">
                    <Button
                      variant={isActive('/chat') ? 'default' : 'ghost'}
                      size="sm"
                      className={cn(!isActive('/chat') && 'text-primary-700 dark:text-primary-300')}
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                      Chat
                    </Button>
                  </Link>

                  <Link href="/workspace">
                    <Button
                      variant={isActive('/workspace') ? 'default' : 'ghost'}
                      size="sm"
                      className={cn(!isActive('/workspace') && 'text-primary-700 dark:text-primary-300')}
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Workspace
                    </Button>
                  </Link>
                </nav>
              )}
            </div>

            {/* Center: Breadcrumbs */}
            {breadcrumbs && breadcrumbs.length > 0 && (
              <div className="flex-1 flex justify-center">
                <Breadcrumbs items={breadcrumbs} />
              </div>
            )}

            {/* Right: Actions */}
            {rightActions && (
              <div className="flex items-center gap-2">
                {rightActions}
              </div>
            )}
          </div>
        </div>
      </header>
    </>
  );
}
