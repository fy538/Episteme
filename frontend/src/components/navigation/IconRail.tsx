/**
 * IconRail
 *
 * Persistent 48px vertical rail on the far left of the app.
 * Provides top-level mode switching between Chat and Cases.
 * Always visible on every screen for maximum orientation.
 *
 * Follows the VS Code Activity Bar / Discord server rail pattern.
 */

'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { SettingsModal } from '@/components/settings/SettingsModal';
import { cn } from '@/lib/utils';
import type { RailSection } from '@/lib/types/navigation';
import { RAIL_ITEMS } from '@/lib/types/navigation';

interface IconRailProps {
  activeSection: RailSection;
  onSearchClick?: () => void;
  className?: string;
}

/** Height of each nav item for indicator positioning */
const ITEM_HEIGHT = 48;

export function IconRail({ activeSection, onSearchClick, className }: IconRailProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [userInitials, setUserInitials] = useState('U');

  // Load user info from localStorage
  useEffect(() => {
    const name = localStorage.getItem('episteme_user_name') || '';
    if (name) {
      const parts = name.trim().split(/\s+/);
      setUserInitials(
        parts.length >= 2
          ? `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
          : name.slice(0, 2).toUpperCase()
      );
    }
  }, []);

  // Calculate indicator position based on active section index
  const activeIndex = useMemo(() => {
    return RAIL_ITEMS.findIndex((item) => item.id === activeSection);
  }, [activeSection]);

  return (
    <>
      <nav
        className={cn(
          'w-12 h-full flex flex-col items-center bg-neutral-50 dark:bg-neutral-900',
          'border-r border-neutral-200 dark:border-neutral-800',
          'shrink-0 select-none',
          className
        )}
      >
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center justify-center w-12 h-12 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
          title="Episteme"
        >
          <span className="text-sm font-bold text-accent-600 dark:text-accent-400">E</span>
        </Link>

        {/* Separator */}
        <div className="w-6 h-px bg-neutral-200 dark:bg-neutral-700 my-1" />

        {/* Navigation items with sliding indicator */}
        <div className="relative flex flex-col items-center gap-1">
          {/* Sliding active indicator */}
          {activeIndex >= 0 && (
            <div
              className="absolute left-0 w-[3px] h-8 rounded-r-full bg-accent-500 transition-transform duration-200"
              style={{
                transform: `translateY(${activeIndex * ITEM_HEIGHT + (ITEM_HEIGHT - 32) / 2}px)`,
              }}
            />
          )}

          {RAIL_ITEMS.map((item) => {
            const isActive = activeSection === item.id;

            return (
              <Link
                key={item.id}
                href={item.href}
                className={cn(
                  'flex items-center justify-center w-10 h-10 rounded-lg',
                  'transition-colors duration-150',
                  isActive
                    ? 'text-accent-600 dark:text-accent-400 bg-accent-50 dark:bg-accent-900/30'
                    : 'text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-800 hover:text-neutral-700 dark:hover:text-neutral-200'
                )}
                title={item.label}
              >
                <RailIcon type={item.icon} className="w-5 h-5" />
              </Link>
            );
          })}
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Bottom utilities */}
        <div className="flex flex-col items-center gap-1 pb-3">
          {/* Search — opens command palette */}
          <button
            onClick={onSearchClick}
            className={cn(
              'flex items-center justify-center w-10 h-10 rounded-lg',
              'text-neutral-500 dark:text-neutral-400',
              'hover:bg-neutral-200 dark:hover:bg-neutral-800',
              'hover:text-neutral-700 dark:hover:text-neutral-200',
              'transition-colors duration-150'
            )}
            title="Search (⌘K)"
          >
            <SearchIcon className="w-5 h-5" />
          </button>

          {/* Settings */}
          <button
            onClick={() => setSettingsOpen(true)}
            className={cn(
              'flex items-center justify-center w-10 h-10 rounded-lg',
              'text-neutral-500 dark:text-neutral-400',
              'hover:bg-neutral-200 dark:hover:bg-neutral-800',
              'hover:text-neutral-700 dark:hover:text-neutral-200',
              'transition-colors duration-150'
            )}
            title="Settings"
          >
            <SettingsIcon className="w-5 h-5" />
          </button>

          {/* User avatar */}
          <div
            className={cn(
              'flex items-center justify-center w-8 h-8 rounded-full',
              'bg-accent-100 dark:bg-accent-900/50',
              'text-accent-700 dark:text-accent-300',
              'text-xs font-medium'
            )}
            title="Profile"
          >
            {userInitials}
          </div>
        </div>
      </nav>

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
}

// --- Icons ---

function RailIcon({ type, className }: { type: string; className?: string }) {
  switch (type) {
    case 'conversations':
      return <ChatIcon className={className} />;
    case 'cases':
      return <FolderIcon className={className} />;
    default:
      return null;
  }
}

function ChatIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path
        d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FolderIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path
        d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" strokeLinecap="round" />
    </svg>
  );
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path
        d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
