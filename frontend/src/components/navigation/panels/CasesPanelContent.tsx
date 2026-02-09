/**
 * CasesPanelContent
 *
 * Sidebar panel content when Cases is the active rail section.
 * Shows a flat list of cases grouped by project name as section headers.
 * Simple, scannable — no expand/collapse tree or sub-view toggles.
 */

'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useProjectsQuery, type ProjectWithCases, type CaseWithInquiries } from '@/hooks/useProjectsQuery';
import { cn } from '@/lib/utils';

interface CasesPanelContentProps {
  activeCaseId?: string;
  activeProjectId?: string;
}

export function CasesPanelContent({ activeCaseId, activeProjectId }: CasesPanelContentProps) {
  const router = useRouter();
  const { data: projects = [], isLoading } = useProjectsQuery();
  const [search, setSearch] = useState('');

  // Flat list of cases grouped by project, filtered by search
  const groups = useMemo(() => {
    const result: { projectTitle: string; projectId: string; cases: CaseWithInquiries[] }[] = [];

    for (const project of projects) {
      const filtered = search
        ? project.cases.filter((c) =>
            c.title.toLowerCase().includes(search.toLowerCase())
          )
        : project.cases;

      if (filtered.length > 0) {
        result.push({
          projectTitle: project.title,
          projectId: project.id,
          cases: filtered.sort(
            (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
          ),
        });
      }
    }

    // When viewing a project page, sort that project's cases to the top
    if (activeProjectId) {
      result.sort((a, b) => {
        if (a.projectId === activeProjectId) return -1;
        if (b.projectId === activeProjectId) return 1;
        return 0;
      });
    }

    return result;
  }, [projects, search, activeProjectId]);

  const totalCases = groups.reduce((sum, g) => sum + g.cases.length, 0);

  return (
    <div className="flex flex-col h-full">
      {/* Header — compact search + new button */}
      <div className="px-3 py-2">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <SearchSmallIcon className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-neutral-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search..."
              className={cn(
                'w-full pl-7 pr-2 py-1 text-[11px] rounded-md',
                'bg-neutral-100 dark:bg-neutral-800',
                'text-neutral-900 dark:text-neutral-100',
                'placeholder:text-neutral-400 dark:placeholder:text-neutral-500',
                'border border-transparent',
                'focus:border-accent-300 dark:focus:border-accent-700 focus:outline-none',
                'transition-colors duration-150'
              )}
            />
          </div>
          <button
            onClick={() => router.push('/cases')}
            className={cn(
              'flex items-center gap-0.5 px-1.5 py-1 rounded-md text-[11px] font-medium shrink-0',
              'bg-accent-50 text-accent-700 dark:bg-accent-900/30 dark:text-accent-300',
              'hover:bg-accent-100 dark:hover:bg-accent-900/50',
              'transition-colors duration-150'
            )}
          >
            <PlusIcon className="w-3 h-3" />
            New
          </button>
        </div>
      </div>

      {/* Case list */}
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-4 h-4 border-2 border-accent-300 border-t-accent-600 rounded-full animate-spin" />
          </div>
        ) : totalCases === 0 ? (
          <div className="text-center py-8 px-4">
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              {search ? 'No cases found' : 'No cases yet'}
            </p>
            {!search && (
              <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
                Start a conversation to create your first case
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {groups.map((group) => {
              const isActiveProject = activeProjectId === group.projectId;
              return (
              <div key={group.projectId}>
                {/* Project name as clickable section header */}
                <Link
                  href={`/projects/${group.projectId}`}
                  className={cn(
                    'block text-[11px] font-medium uppercase tracking-wider mb-1 px-2 py-0.5 -mx-0.5 rounded',
                    'transition-colors duration-150',
                    isActiveProject
                      ? 'text-accent-600 dark:text-accent-400 bg-accent-50/50 dark:bg-accent-900/20'
                      : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                  )}
                >
                  {group.projectTitle}
                </Link>
                <div className="space-y-0.5">
                  {group.cases.map((caseItem) => (
                    <CaseItem
                      key={caseItem.id}
                      caseItem={caseItem}
                      isActive={caseItem.id === activeCaseId}
                    />
                  ))}
                </div>
              </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function CaseItem({ caseItem, isActive }: { caseItem: CaseWithInquiries; isActive: boolean }) {
  return (
    <Link
      href={`/cases/${caseItem.id}`}
      className={cn(
        'flex items-center gap-1.5 px-2 py-1 rounded-md',
        'transition-colors duration-150',
        isActive
          ? 'bg-accent-50 dark:bg-accent-900/30 text-accent-700 dark:text-accent-300'
          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800'
      )}
    >
      <CaseStatusIcon caseItem={caseItem} />
      <span className="text-xs truncate flex-1">{caseItem.title}</span>
      <span className="text-[11px] text-neutral-400 shrink-0">
        {formatCompactTime(caseItem.updated_at)}
      </span>
    </Link>
  );
}

function CaseStatusIcon({ caseItem }: { caseItem: CaseWithInquiries }) {
  if (caseItem.tensionsCount === 0 && caseItem.inquiries.length > 0 && caseItem.inquiries.every(i => i.status === 'resolved')) {
    return <CheckCircleIcon className="w-3 h-3 text-success-500 shrink-0" />;
  }
  if (caseItem.tensionsCount > 0 || caseItem.blindSpotsCount > 0) {
    return <AlertCircleIcon className="w-3 h-3 text-warning-500 shrink-0" />;
  }
  return <CircleIcon className="w-3 h-3 text-neutral-300 dark:text-neutral-600 shrink-0" />;
}

// --- Utility ---

function formatCompactTime(dateStr: string): string {
  const now = new Date();
  const then = new Date(dateStr);
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const weekStart = new Date(todayStart);
  weekStart.setDate(weekStart.getDate() - 6);

  if (then >= todayStart) {
    return then.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: false });
  }
  if (then >= weekStart) {
    return then.toLocaleDateString('en-US', { weekday: 'short' });
  }
  return then.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });
}

// --- Icons ---

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SearchSmallIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" strokeLinecap="round" />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 11.08V12a10 10 0 11-5.93-9.14" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="22 4 12 14.01 9 11.01" strokeLinecap="round" strokeLinejoin="round" />
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

function CircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
    </svg>
  );
}

