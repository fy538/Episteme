/**
 * SidebarPanel
 *
 * The 240px sidebar panel with integrated tabs, logo, and utility footer.
 * Replaces the previous IconRail + SidebarPanel two-tier architecture.
 *
 * Layout:
 *   ┌─────────────────────────┐
 *   │ E (logo)                │  Header
 *   │─────────────────────────│
 *   │ [Decisions] [Threads]   │  Tab switcher
 *   │─────────────────────────│
 *   │                         │
 *   │  (tab content area)     │  flex-1, scrollable
 *   │                         │
 *   │─────────────────────────│
 *   │  🔍 Search    ⚙️  [FY]  │  Footer: utilities
 *   └─────────────────────────┘
 *
 * Within the 'decisions' tab, supports a drill-down pattern:
 *   - No active case → case list (CasesPanelContent)
 *   - Active case → case structure (CaseStructurePanelContent)
 * Transitions between these with a horizontal slide animation.
 */

'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { ConversationsPanelContent } from './panels/ConversationsPanelContent';
import { CasesPanelContent } from './panels/CasesPanelContent';
import { CaseStructurePanelContent } from './panels/CaseStructurePanelContent';
import { SettingsModal } from '@/components/settings/SettingsModal';
import { useNavigation } from './NavigationProvider';
import { useCaseWorkspaceContext } from '@/components/workspace/CaseWorkspaceProvider';
import { cn } from '@/lib/utils';
import type { SidebarTab, PanelMode } from '@/lib/types/navigation';

/** Duration in seconds for the drill-down slide animation. */
const DRILLDOWN_DURATION = 0.2;

/** Easing curve for drill-down transitions. */
const DRILLDOWN_EASE: [number, number, number, number] = [0.32, 0.72, 0, 1];

interface SidebarPanelProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  className?: string;
}

export function SidebarPanel({ isCollapsed, onToggleCollapse, className }: SidebarPanelProps) {
  const nav = useNavigation();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [userInitials, setUserInitials] = useState('U');

  // Load user info from localStorage (migrated from IconRail)
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

          {/* ─── Tab Switcher ─── */}
          <TabSwitcher activeTab={nav.activeTab} onTabChange={nav.setActiveTab} />

          {/* ─── Tab Content ─── */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <TabContent activeTab={nav.activeTab} panelMode={nav.panelMode} />
          </div>

          {/* ─── Footer: Utilities ─── */}
          <div className="shrink-0 border-t border-neutral-200 dark:border-neutral-800 px-3 py-2 flex items-center gap-1">
            {/* Search */}
            <button
              onClick={nav.navigateToSearch}
              className={cn(
                'flex items-center gap-1.5 px-2 py-1.5 rounded-md flex-1',
                'text-xs text-neutral-500 dark:text-neutral-400',
                'hover:bg-neutral-100 dark:hover:bg-neutral-800',
                'hover:text-neutral-700 dark:hover:text-neutral-200',
                'transition-colors duration-150'
              )}
              title="Search (⌘K)"
            >
              <SearchIcon className="w-3.5 h-3.5" />
              <span>Search</span>
              <kbd className="ml-auto text-[10px] text-neutral-400 dark:text-neutral-500 font-mono">⌘K</kbd>
            </button>

            {/* Settings */}
            <button
              onClick={() => setSettingsOpen(true)}
              className={cn(
                'flex items-center justify-center w-7 h-7 rounded-md',
                'text-neutral-500 dark:text-neutral-400',
                'hover:bg-neutral-100 dark:hover:bg-neutral-800',
                'hover:text-neutral-700 dark:hover:text-neutral-200',
                'transition-colors duration-150'
              )}
              title="Settings"
            >
              <SettingsIcon className="w-3.5 h-3.5" />
            </button>

            {/* User avatar */}
            <div
              className={cn(
                'flex items-center justify-center w-7 h-7 rounded-full',
                'bg-accent-100 dark:bg-accent-900/50',
                'text-accent-700 dark:text-accent-300',
                'text-[10px] font-medium'
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

// ─── Tab Switcher ──────────────────────────────────────────────

const TABS: { id: SidebarTab; label: string }[] = [
  { id: 'decisions', label: 'Decisions' },
  { id: 'threads', label: 'Threads' },
];

function TabSwitcher({
  activeTab,
  onTabChange,
}: {
  activeTab: SidebarTab;
  onTabChange: (tab: SidebarTab) => void;
}) {
  return (
    <div className="flex items-center border-b border-neutral-200 dark:border-neutral-800 px-4">
      {TABS.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              'relative px-3 py-2 text-xs font-medium transition-colors duration-150',
              isActive
                ? 'text-accent-700 dark:text-accent-300'
                : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200'
            )}
          >
            {tab.label}
            {/* Active underline indicator */}
            {isActive && (
              <motion.div
                layoutId="sidebar-tab-indicator"
                className="absolute bottom-0 left-3 right-3 h-[2px] bg-accent-500 rounded-full"
                transition={{ duration: 0.2, ease: [0.32, 0.72, 0, 1] }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}

// ─── Tab Content ──────────────────────────────────────────────

function TabContent({
  activeTab,
  panelMode,
}: {
  activeTab: SidebarTab;
  panelMode: PanelMode;
}) {
  switch (activeTab) {
    case 'decisions':
      return <CasesDrilldownContent panelMode={panelMode} />;

    case 'threads':
      return (
        <ConversationsPanelContent
          activeThreadId={
            panelMode.section === 'conversations' && 'activeThreadId' in panelMode
              ? panelMode.activeThreadId
              : undefined
          }
        />
      );

    default:
      return null;
  }
}

// ─── Cases Drill-down ──────────────────────────────────────────

/**
 * Cases section with drill-down: slides between case list and case structure.
 *
 * The back button ("← Decisions") sets showCaseList=true to slide back to the
 * case list without navigating away from the current page. When the user clicks
 * a different case from the list, the URL changes, activeCaseId updates, and
 * the override resets automatically.
 */
function CasesDrilldownContent({ panelMode }: { panelMode: PanelMode }) {
  const workspace = useCaseWorkspaceContext();
  const activeCaseId = panelMode.section === 'cases' && 'activeCaseId' in panelMode ? panelMode.activeCaseId : undefined;

  // Override: user clicked "← Decisions" to show case list while staying on a case page
  const [showCaseList, setShowCaseList] = useState(false);

  // Reset override when activeCaseId changes (user navigated to a different case or left)
  const prevCaseId = useRef(activeCaseId);
  useEffect(() => {
    if (prevCaseId.current !== activeCaseId) {
      setShowCaseList(false);
      prevCaseId.current = activeCaseId;
    }
  }, [activeCaseId]);

  const handleBack = useCallback(() => setShowCaseList(true), []);

  const hasCaseData = !!(activeCaseId && workspace && (workspace.caseData || workspace.loading));
  const isDrilldown = hasCaseData && !showCaseList;

  return (
    <div className="h-full relative overflow-hidden">
      <AnimatePresence mode="wait" initial={false}>
        {isDrilldown ? (
          <motion.div
            key="case-structure"
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ duration: DRILLDOWN_DURATION, ease: DRILLDOWN_EASE }}
            className="absolute inset-0"
          >
            <CaseStructurePanelContent onBack={handleBack} />
          </motion.div>
        ) : (
          <motion.div
            key="case-list"
            initial={{ x: '-100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '-100%', opacity: 0 }}
            transition={{ duration: DRILLDOWN_DURATION, ease: DRILLDOWN_EASE }}
            className="absolute inset-0"
          >
            <CasesPanelContent
              activeCaseId={activeCaseId}
              activeProjectId={panelMode.section === 'cases' && 'activeProjectId' in panelMode ? panelMode.activeProjectId : undefined}
            />
          </motion.div>
        )}
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
