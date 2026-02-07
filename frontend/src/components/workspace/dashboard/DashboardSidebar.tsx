/**
 * Dashboard Sidebar
 *
 * 5-zone collapsible left navigation:
 * 1. Workspace header (logo + collapse)
 * 2. Search trigger (Cmd+K)
 * 3. Primary navigation (Home, Cases, Inquiries)
 * 4. Project tree (scrollable)
 * 5. Bottom utility (Settings + user avatar)
 */

'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { SettingsModal } from '@/components/settings/SettingsModal';
import type { ProjectWithCases, CaseWithInquiries } from '@/hooks/useProjectsQuery';

interface DashboardSidebarProps {
  projects: ProjectWithCases[];
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onCreateProject?: () => void;
  className?: string;
}

export function DashboardSidebar({
  projects,
  isCollapsed,
  onToggleCollapse,
  onCreateProject,
  className,
}: DashboardSidebarProps) {
  const pathname = usePathname();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [userInitials, setUserInitials] = useState('U');
  const [userName, setUserName] = useState('');
  const [isMac, setIsMac] = useState(true);

  useEffect(() => {
    setIsMac(navigator.platform.toUpperCase().indexOf('MAC') >= 0);
    const name = localStorage.getItem('episteme_user_name') || '';
    setUserName(name);
    if (name) {
      const parts = name.trim().split(/\s+/);
      setUserInitials(
        parts.length > 1
          ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
          : name[0].toUpperCase()
      );
    }
  }, []);

  const handleSearchClick = () => {
    window.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'k',
        metaKey: isMac,
        ctrlKey: !isMac,
        bubbles: true,
      })
    );
  };

  const isNavActive = (path: string) => {
    if (path === '/') return pathname === '/';
    return pathname?.startsWith(path) ?? false;
  };

  return (
    <>
      <aside
        className={cn(
          'h-screen bg-neutral-50 dark:bg-neutral-900 border-r border-neutral-200 dark:border-neutral-800',
          'flex flex-col transition-all duration-200 ease-in-out',
          isCollapsed ? 'w-14' : 'w-64',
          className
        )}
      >
        {/* Zone 1: Workspace Header */}
        <div
          className={cn(
            'group/header flex items-center border-b border-neutral-200 dark:border-neutral-800',
            isCollapsed ? 'flex-col gap-1 py-3 px-2' : 'justify-between p-3'
          )}
        >
          <Link
            href="/"
            className={cn(
              'flex items-center gap-2',
              isCollapsed && 'justify-center'
            )}
            title="Episteme Home"
          >
            <div className="w-7 h-7 rounded-lg bg-accent-600 flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold text-sm">E</span>
            </div>
            {!isCollapsed && (
              <span className="font-semibold text-primary-900 dark:text-primary-50">
                Episteme
              </span>
            )}
          </Link>
          <button
            onClick={onToggleCollapse}
            className={cn(
              'p-2 rounded-md hover:bg-neutral-200 dark:hover:bg-neutral-800 transition-all',
              !isCollapsed && 'opacity-0 group-hover/header:opacity-100'
            )}
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRightIcon className="w-4 h-4 text-neutral-600 dark:text-neutral-400" />
            ) : (
              <ChevronLeftIcon className="w-4 h-4 text-neutral-600 dark:text-neutral-400" />
            )}
          </button>
        </div>

        {/* Zone 2: Search Trigger */}
        <div className={cn('px-2 pt-3 pb-1', isCollapsed && 'px-1.5')}>
          {isCollapsed ? (
            <div className="flex justify-center">
              <button
                onClick={handleSearchClick}
                className="p-2 rounded-md hover:bg-neutral-200 dark:hover:bg-neutral-800 transition-colors"
                title={`Search (${isMac ? '⌘' : 'Ctrl'}K)`}
              >
                <SearchIcon className="w-4 h-4 text-neutral-600 dark:text-neutral-400" />
              </button>
            </div>
          ) : (
            <button
              onClick={handleSearchClick}
              className="w-full flex items-center gap-2 px-2.5 py-2 text-sm text-neutral-500 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-md transition-colors"
            >
              <SearchIcon className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1 text-left">Search...</span>
              <kbd className="px-1.5 py-0.5 text-xs font-medium bg-white dark:bg-neutral-900 rounded border border-neutral-300 dark:border-neutral-600">
                {isMac ? '⌘' : 'Ctrl'}K
              </kbd>
            </button>
          )}
        </div>

        {/* Zone 3: Primary Navigation */}
        <nav
          className={cn(
            'border-b border-neutral-200 dark:border-neutral-800',
            isCollapsed ? 'px-1.5 py-2' : 'px-2 py-2'
          )}
        >
          <div className={cn(isCollapsed ? 'flex flex-col items-center gap-1' : 'space-y-0.5')}>
            <NavLink
              href="/"
              icon={<HomeIcon className="w-4 h-4" />}
              label="Home"
              isActive={isNavActive('/')}
              isCollapsed={isCollapsed}
            />
            <NavLink
              href="/cases"
              icon={<CasesIcon className="w-4 h-4" />}
              label="Cases"
              isActive={isNavActive('/cases')}
              isCollapsed={isCollapsed}
            />
            <NavLink
              href="/inquiries"
              icon={<InquiriesIcon className="w-4 h-4" />}
              label="Inquiries"
              isActive={isNavActive('/inquiries')}
              isCollapsed={isCollapsed}
            />
          </div>
        </nav>

        {/* Zone 4: Project Tree (scrollable) */}
        <div className="flex-1 relative overflow-hidden">
        <div className="h-full overflow-y-auto py-3">
          {!isCollapsed && (
            <div className="flex items-center justify-between px-3 mb-2">
              <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
                Projects
              </span>
              {onCreateProject && (
                <button
                  onClick={onCreateProject}
                  className="p-1 rounded hover:bg-neutral-200 dark:hover:bg-neutral-800 transition-colors"
                  title="New Project"
                >
                  <PlusIcon className="w-3.5 h-3.5 text-neutral-500 dark:text-neutral-400" />
                </button>
              )}
            </div>
          )}

          <div
            className={cn(
              isCollapsed
                ? 'flex flex-col items-center gap-1 px-1.5'
                : 'space-y-1 px-2'
            )}
          >
            {isCollapsed && onCreateProject && (
              <button
                onClick={onCreateProject}
                className="p-2 rounded-md hover:bg-neutral-200 dark:hover:bg-neutral-800 transition-colors"
                title="New Project"
              >
                <PlusIcon className="w-4 h-4 text-neutral-600 dark:text-neutral-400" />
              </button>
            )}
            {projects.map((project) => (
              <ProjectNavItem
                key={project.id}
                project={project}
                isCollapsed={isCollapsed}
                currentPath={pathname}
              />
            ))}
          </div>
        </div>
        {/* Scroll fade masks */}
        <div className="absolute top-0 left-0 right-0 h-4 bg-gradient-to-b from-neutral-50 dark:from-neutral-900 to-transparent pointer-events-none" />
        <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-neutral-50 dark:from-neutral-900 to-transparent pointer-events-none" />
        </div>

        {/* Zone 5: Bottom Utility */}
        <div className="border-t border-neutral-200 dark:border-neutral-800 p-2">
          {isCollapsed ? (
            <div className="flex flex-col items-center gap-1">
              <button
                onClick={() => setSettingsOpen(true)}
                className="p-2 rounded-md hover:bg-neutral-200 dark:hover:bg-neutral-800 transition-colors"
                title="Settings"
              >
                <SettingsIcon className="w-4 h-4 text-neutral-600 dark:text-neutral-400" />
              </button>
              <div
                className="w-7 h-7 rounded-full bg-accent-100 dark:bg-accent-900/50 flex items-center justify-center"
                title={userName || 'User'}
              >
                <span className="text-xs font-medium text-accent-700 dark:text-accent-300">
                  {userInitials}
                </span>
              </div>
            </div>
          ) : (
            <div className="space-y-0.5">
              <button
                onClick={() => setSettingsOpen(true)}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-800 transition-colors"
              >
                <SettingsIcon className="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
                <span className="font-medium">Settings</span>
              </button>
              <div className="flex items-center gap-2.5 px-2.5 py-2 rounded-md">
                <div className="w-7 h-7 rounded-full bg-accent-100 dark:bg-accent-900/50 flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-medium text-accent-700 dark:text-accent-300">
                    {userInitials}
                  </span>
                </div>
                <span className="text-sm text-neutral-700 dark:text-neutral-300 truncate">
                  {userName || 'Set up profile'}
                </span>
              </div>
            </div>
          )}
        </div>
      </aside>

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
}

// --- Helper Components ---

function NavLink({
  href,
  icon,
  label,
  isActive,
  isCollapsed,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  isCollapsed: boolean;
}) {
  if (isCollapsed) {
    return (
      <Link
        href={href}
        className={cn(
          'relative flex items-center justify-center p-2 rounded-md transition-colors',
          isActive
            ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400'
            : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-800'
        )}
        title={label}
      >
        {isActive && (
          <span className="absolute left-0 top-1 bottom-1 w-[3px] rounded-r-full bg-accent-500" />
        )}
        {icon}
      </Link>
    );
  }

  return (
    <Link
      href={href}
      className={cn(
        'relative flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm font-medium transition-colors',
        isActive
          ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400'
          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-800'
      )}
    >
      {isActive && (
        <span className="absolute left-0 top-1 bottom-1 w-[3px] rounded-r-full bg-accent-500" />
      )}
      {icon}
      <span>{label}</span>
    </Link>
  );
}

function ProjectNavItem({
  project,
  isCollapsed,
  currentPath,
}: {
  project: ProjectWithCases;
  isCollapsed: boolean;
  currentPath: string;
}) {
  const [expanded, setExpanded] = useState(true);
  const isActive = currentPath === `/projects/${project.id}`;

  if (isCollapsed) {
    return (
      <Link
        href={`/projects/${project.id}`}
        className={cn(
          'relative flex items-center justify-center p-2 rounded-md transition-colors',
          isActive
            ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400'
            : 'hover:bg-neutral-200 dark:hover:bg-neutral-800 text-neutral-600 dark:text-neutral-400'
        )}
        title={project.title}
      >
        {isActive && (
          <span className="absolute left-0 top-1 bottom-1 w-[3px] rounded-r-full bg-accent-500" />
        )}
        <FolderIcon className="w-4 h-4" />
      </Link>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-0.5 rounded hover:bg-neutral-200 dark:hover:bg-neutral-800"
        >
          <ChevronIcon
            className={cn(
              'w-3.5 h-3.5 text-neutral-400 transition-transform duration-200',
              expanded && 'rotate-90'
            )}
          />
        </button>
        <Link
          href={`/projects/${project.id}`}
          className={cn(
            'relative flex-1 flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] transition-colors',
            isActive
              ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400'
              : 'hover:bg-neutral-200 dark:hover:bg-neutral-800 text-primary-900 dark:text-primary-50'
          )}
        >
          {isActive && (
            <span className="absolute left-0 top-0.5 bottom-0.5 w-[3px] rounded-r-full bg-accent-500" />
          )}
          <FolderIcon className="w-4 h-4 text-accent-500" />
          <span className="truncate font-medium">{project.title}</span>
        </Link>
      </div>

      {expanded && project.cases.length > 0 && (
        <div className="ml-5 mt-1 space-y-1">
          {project.cases.map((caseItem) => (
            <CaseNavItem
              key={caseItem.id}
              caseItem={caseItem}
              currentPath={currentPath}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CaseNavItem({
  caseItem,
  currentPath,
}: {
  caseItem: CaseWithInquiries;
  currentPath: string;
}) {
  const isActive = currentPath === `/cases/${caseItem.id}`;
  const isReady = caseItem.readinessScore >= 90 && caseItem.tensionsCount === 0;
  const hasIssues = caseItem.tensionsCount > 0 || caseItem.blindSpotsCount > 0;

  return (
    <Link
      href={`/cases/${caseItem.id}`}
      className={cn(
        'relative flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] transition-colors',
        isActive
          ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400'
          : 'hover:bg-neutral-200 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300'
      )}
    >
      {isActive && (
        <span className="absolute left-0 top-0.5 bottom-0.5 w-[3px] rounded-r-full bg-accent-500" />
      )}
      {isReady ? (
        <CheckCircleIcon className="w-3.5 h-3.5 text-success-500 flex-shrink-0" />
      ) : hasIssues ? (
        <AlertCircleIcon className="w-3.5 h-3.5 text-warning-500 flex-shrink-0" />
      ) : (
        <CircleIcon className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0" />
      )}
      <span className="flex-1 truncate">{caseItem.title}</span>
      <span className="text-[11px] text-neutral-400 dark:text-neutral-500 shrink-0 tabular-nums">
        {formatSidebarTime(caseItem.updated_at)}
      </span>
    </Link>
  );
}

/** Short timestamp for sidebar: "6:58" today, "Thu" this week, "7/2" older */
function formatSidebarTime(dateStr: string): string {
  const now = new Date();
  const then = new Date(dateStr);

  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterdayStart = new Date(todayStart);
  yesterdayStart.setDate(yesterdayStart.getDate() - 1);
  const weekStart = new Date(todayStart);
  weekStart.setDate(weekStart.getDate() - 6);

  if (then >= todayStart) {
    // Today — show time like "6:58"
    return then.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: false });
  }
  if (then >= yesterdayStart) {
    return 'Yesterday';
  }
  if (then >= weekStart) {
    // This week — show day name like "Thu"
    return then.toLocaleDateString('en-US', { weekday: 'short' });
  }
  // Older — show compact date like "7/2"
  return `${then.getMonth() + 1}/${then.getDate()}`;
}

// --- Icons ---

function ChevronLeftIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <path d="M21 21l-4.35-4.35" strokeLinecap="round" />
    </svg>
  );
}

function FolderIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
    </svg>
  );
}

function AlertCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" strokeLinecap="round" />
      <line x1="12" y1="16" x2="12.01" y2="16" strokeLinecap="round" />
    </svg>
  );
}

function HomeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="9 22 9 12 15 12 15 22" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CasesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="16" y1="13" x2="8" y2="13" strokeLinecap="round" />
      <line x1="16" y1="17" x2="8" y2="17" strokeLinecap="round" />
    </svg>
  );
}

function InquiriesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="12" y1="17" x2="12.01" y2="17" strokeLinecap="round" />
    </svg>
  );
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export default DashboardSidebar;
