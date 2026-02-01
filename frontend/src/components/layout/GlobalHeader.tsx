/**
 * Global Header - consistent navigation across all pages
 * Provides spatial consistency and orientation
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Breadcrumbs, type BreadcrumbItem } from '@/components/ui/breadcrumbs';
import { SettingsModal } from '@/components/settings/SettingsModal';
import { cn } from '@/lib/utils';

interface GlobalHeaderProps {
  breadcrumbs?: BreadcrumbItem[];
  showNav?: boolean;
  rightActions?: React.ReactNode;
}

export function GlobalHeader({
  breadcrumbs,
  showNav = true,
  rightActions,
}: GlobalHeaderProps) {
  const pathname = usePathname();
  const [settingsOpen, setSettingsOpen] = useState(false);

  const isActive = (path: string) => pathname?.startsWith(path);

  return (
    <>
      <header className="border-b border-neutral-200 bg-white">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Left: Logo & Nav */}
            <div className="flex items-center gap-8">
              <Link href="/workspace" className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-accent-600 to-accent-700 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-lg">E</span>
                </div>
                <span className="text-xl font-semibold text-primary-900">Episteme</span>
              </Link>

              {showNav && (
                <nav className="flex items-center gap-1">
                  <Link href="/chat">
                    <Button
                      variant={isActive('/chat') ? 'default' : 'ghost'}
                      size="sm"
                      className={cn(!isActive('/chat') && 'text-primary-700')}
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
                      className={cn(!isActive('/workspace') && 'text-primary-700')}
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

            {/* Right: Actions & Settings */}
            <div className="flex items-center gap-2">
              {rightActions}
              
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSettingsOpen(true)}
                aria-label="Settings"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
}
