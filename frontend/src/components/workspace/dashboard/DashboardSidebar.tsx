/**
 * Dashboard Sidebar
 *
 * Collapsible left navigation showing all projects and cases.
 * Provides exhaustive navigation while main content stays focused.
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { Project } from '@/lib/types/project';
import type { Case, Inquiry } from '@/lib/types/case';

interface CaseWithInquiries extends Case {
  inquiries: Inquiry[];
  readinessScore: number;
  tensionsCount: number;
  blindSpotsCount: number;
}

interface ProjectWithCases extends Project {
  cases: CaseWithInquiries[];
}

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

  return (
    <aside
      className={cn(
        'h-screen bg-neutral-50 dark:bg-neutral-900 border-r border-neutral-200 dark:border-neutral-800',
        'flex flex-col transition-all duration-200 ease-in-out',
        isCollapsed ? 'w-14' : 'w-64',
        className
      )}
    >
      {/* Header with logo and collapse toggle */}
      <div className="flex items-center justify-between p-3 border-b border-neutral-200 dark:border-neutral-800">
        {!isCollapsed && (
          <Link href="/workspace" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-accent-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">E</span>
            </div>
            <span className="font-semibold text-primary-900 dark:text-primary-50">
              Episteme
            </span>
          </Link>
        )}
        <button
          onClick={onToggleCollapse}
          className={cn(
            'p-1.5 rounded-md hover:bg-neutral-200 dark:hover:bg-neutral-800 transition-colors',
            isCollapsed && 'mx-auto'
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

      {/* Search (expanded only) */}
      {!isCollapsed && (
        <div className="p-3">
          <div className="relative">
            <SearchIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <input
              type="text"
              placeholder="Search..."
              className="w-full pl-8 pr-3 py-1.5 text-sm bg-neutral-100 dark:bg-neutral-800 border-0 rounded-md placeholder:text-neutral-400 focus:ring-2 focus:ring-accent-500 focus:outline-none"
            />
          </div>
        </div>
      )}

      {/* Collapsed search icon */}
      {isCollapsed && (
        <div className="p-3 flex justify-center">
          <button className="p-1.5 rounded-md hover:bg-neutral-200 dark:hover:bg-neutral-800">
            <SearchIcon className="w-4 h-4 text-neutral-600 dark:text-neutral-400" />
          </button>
        </div>
      )}

      {/* Projects list */}
      <nav className="flex-1 overflow-y-auto py-2">
        {!isCollapsed && (
          <div className="px-3 mb-2">
            <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
              Projects
            </span>
          </div>
        )}

        <div className="space-y-1 px-2">
          {projects.map((project) => (
            <ProjectNavItem
              key={project.id}
              project={project}
              isCollapsed={isCollapsed}
              currentPath={pathname}
            />
          ))}
        </div>
      </nav>

      {/* New Project button */}
      <div className="p-3 border-t border-neutral-200 dark:border-neutral-800">
        {isCollapsed ? (
          <button
            onClick={onCreateProject}
            className="w-full p-1.5 rounded-md hover:bg-neutral-200 dark:hover:bg-neutral-800 flex items-center justify-center"
            title="New Project"
          >
            <PlusIcon className="w-4 h-4 text-neutral-600 dark:text-neutral-400" />
          </button>
        ) : (
          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={onCreateProject}
          >
            <PlusIcon className="w-4 h-4 mr-2" />
            New Project
          </Button>
        )}
      </div>
    </aside>
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
  const isActive = currentPath === `/workspace/projects/${project.id}`;

  if (isCollapsed) {
    return (
      <Link
        href={`/workspace/projects/${project.id}`}
        className={cn(
          'flex items-center justify-center p-1.5 rounded-md transition-colors',
          isActive
            ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400'
            : 'hover:bg-neutral-200 dark:hover:bg-neutral-800'
        )}
        title={project.title}
      >
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
              'w-3.5 h-3.5 text-neutral-400 transition-transform',
              expanded && 'rotate-90'
            )}
          />
        </button>
        <Link
          href={`/workspace/projects/${project.id}`}
          className={cn(
            'flex-1 flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors',
            isActive
              ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400'
              : 'hover:bg-neutral-200 dark:hover:bg-neutral-800 text-primary-900 dark:text-primary-50'
          )}
        >
          <FolderIcon className="w-4 h-4 text-accent-500" />
          <span className="truncate font-medium">{project.title}</span>
        </Link>
      </div>

      {/* Cases */}
      {expanded && project.cases.length > 0 && (
        <div className="ml-5 mt-1 space-y-0.5">
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
  const isActive = currentPath === `/workspace/cases/${caseItem.id}`;
  const isReady = caseItem.readinessScore >= 90 && caseItem.tensionsCount === 0;
  const hasIssues = caseItem.tensionsCount > 0 || caseItem.blindSpotsCount > 0;

  return (
    <Link
      href={`/workspace/cases/${caseItem.id}`}
      className={cn(
        'flex items-center gap-2 px-2 py-1 rounded-md text-sm transition-colors',
        isActive
          ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400'
          : 'hover:bg-neutral-200 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300'
      )}
    >
      {isReady ? (
        <CheckCircleIcon className="w-3.5 h-3.5 text-success-500 flex-shrink-0" />
      ) : hasIssues ? (
        <AlertCircleIcon className="w-3.5 h-3.5 text-warning-500 flex-shrink-0" />
      ) : (
        <CircleIcon className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0" />
      )}
      <span className="truncate">{caseItem.title}</span>
    </Link>
  );
}

// Icons
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

export default DashboardSidebar;
