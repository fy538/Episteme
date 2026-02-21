/**
 * SidebarPanel
 *
 * The 240px sidebar with three-mode progressive zoom navigation.
 * Replaces the previous tab-based (Decisions / Threads) architecture.
 *
 * Three modes:
 *   HOME    → project list + scratch threads
 *   PROJECT → project-scoped (landscape, threads, cases, sources)
 *   CASE    → case structure (plan, inquiries, assumptions, criteria)
 *
 * Layout:
 *   ┌─────────────────────────┐
 *   │ E (logo)                │  Header
 *   │─────────────────────────│
 *   │                         │
 *   │  (mode content area)    │  flex-1, animated transitions
 *   │                         │
 *   │─────────────────────────│
 *   │  🔍 Search    ⚙️  [FY]  │  Footer: utilities
 *   └─────────────────────────┘
 *
 * Transitions use horizontal slide animations matching the zoom direction:
 *   forward (zoom in): new content slides in from right
 *   back (zoom out): new content slides in from left
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { HomeSidebarContent } from './panels/HomeSidebarContent';
import { ProjectSidebarContent } from './panels/ProjectSidebarContent';
import { CaseStructurePanelContent } from './panels/CaseStructurePanelContent';
import { SettingsModal } from '@/components/settings/SettingsModal';
import { useNavigation } from './NavigationProvider';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

/** Duration in seconds for the mode slide animation. */
const SLIDE_DURATION = 0.2;

/** Easing curve for mode transitions. */
const SLIDE_EASE: [number, number, number, number] = [0.32, 0.72, 0, 1];

interface SidebarPanelProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  className?: string;
}

export function SidebarPanel({ isCollapsed, onToggleCollapse, className }: SidebarPanelProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [userInitials, setUserInitials] = useState('U');
  const nav = useNavigation();

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

  return (
    <>
      <div
        className={cn(
          'h-full border-r border-neutral-200 dark:border-neutral-800',
          'bg-white dark:bg-neutral-950',
          'transition-[width] duration-200 ease-out overflow-hidden shrink-0',
          isCollapsed ? 'w-0 border-r-0' : 'w-60',
          className
        )}
      >
        <div
          className={cn(
            'w-60 h-full flex flex-col transition-opacity duration-100',
            isCollapsed && 'opacity-0'
          )}
        >
          {/* ─── Header: Logo ─── */}
          <div className="px-4 pt-3 pb-1">
            <Link
              href="/"
              className="flex items-center gap-2 hover:opacity-80 transition-opacity"
              title="Episteme — Home"
            >
              <span className="text-sm font-bold text-accent-600 dark:text-accent-400">E</span>
              <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Episteme</span>
            </Link>
          </div>

          {/* ─── Mode Content (animated) ─── */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <SidebarModeContent />
          </div>

          {/* ─── Footer: Utilities ─── */}
          <div className="shrink-0 border-t border-neutral-200 dark:border-neutral-800 px-3 py-2 flex items-center gap-1">
            {/* Search */}
            <Button
              variant="ghost"
              size="sm"
              onClick={nav.navigateToSearch}
              className={cn(
                'flex items-center gap-1.5 px-2 py-1.5 rounded-md flex-1 h-auto',
                'text-xs text-neutral-500 dark:text-neutral-400',
                'hover:bg-neutral-100 dark:hover:bg-neutral-800',
                'hover:text-neutral-700 dark:hover:text-neutral-200',
                'transition-colors duration-150'
              )}
              title="Search (⌘K)"
            >
              <SearchIcon className="w-3.5 h-3.5" />
              <span>Search</span>
              <kbd className="ml-auto text-xs text-neutral-400 dark:text-neutral-500 font-mono">⌘K</kbd>
            </Button>

            {/* Settings */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSettingsOpen(true)}
              className={cn(
                'w-7 h-7',
                'text-neutral-500 dark:text-neutral-400',
                'hover:bg-neutral-100 dark:hover:bg-neutral-800',
                'hover:text-neutral-700 dark:hover:text-neutral-200',
                'transition-colors duration-150'
              )}
              title="Settings"
            >
              <SettingsIcon className="w-3.5 h-3.5" />
            </Button>

            {/* User avatar */}
            <div
              className={cn(
                'flex items-center justify-center w-7 h-7 rounded-full',
                'bg-accent-100 dark:bg-accent-900/50',
                'text-accent-700 dark:text-accent-300',
                'text-xs font-medium'
              )}
              title="Profile"
            >
              {userInitials}
            </div>
          </div>
        </div>
      </div>

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
}

// ─── Mode Content (animated three-way switch) ──────────────────

function SidebarModeContent() {
  const { sidebarMode, transitionDirection } = useNavigation();

  // Generate a unique key for AnimatePresence
  const modeKey =
    sidebarMode.mode === 'home'
      ? 'home'
      : sidebarMode.mode === 'project'
        ? `project-${sidebarMode.projectId}`
        : `case-${sidebarMode.caseId}`;

  // Animation direction: forward = slide from right, back = slide from left
  const slideIn = transitionDirection === 'back' ? '-100%' : '100%';
  const slideOut = transitionDirection === 'back' ? '100%' : '-100%';

  return (
    <div className="h-full relative overflow-hidden">
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={modeKey}
          initial={{ x: slideIn, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: slideOut, opacity: 0 }}
          transition={{ duration: SLIDE_DURATION, ease: SLIDE_EASE }}
          className="absolute inset-0"
        >
          {sidebarMode.mode === 'home' && <HomeSidebarContent />}
          {sidebarMode.mode === 'project' && <ProjectSidebarContent />}
          {sidebarMode.mode === 'case' && <CaseStructurePanelContent />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

// ─── Icons ──────────────────────────────────────────────

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
