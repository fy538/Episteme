/**
 * ProjectSidebarContent
 *
 * Sidebar content for PROJECT mode — the project navigation hub.
 *
 * Layout:
 *   ┌─────────────────────────┐
 *   │ ← Home                  │
 *   │─────────────────────────│
 *   │ Go-to-Market Strategy   │
 *   │─────────────────────────│
 *   │ 🏠 Home          active │
 *   │ 🧭 Explore              │
 *   │ 📄 Sources              │
 *   │ 📋 Cases                │
 *   │ 💬 Chat                 │
 *   │─────────────────────────│
 *   │ CASES                   │
 *   │    • Pivot to B2B?      │
 *   │    • Pricing risk       │
 *   │    + New case           │
 *   └─────────────────────────┘
 */

'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useProjectWorkspaceContext } from '@/components/workspace/ProjectWorkspaceProvider';
import { useNavigation } from '../NavigationProvider';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ArrowLeftIcon } from '@/components/ui/icons';
import { cn } from '@/lib/utils';
import type { Case } from '@/lib/types/case';

// ─── Nav Item Definitions ──────────────────────────

interface NavItem {
  key: string;
  label: string;
  subPage: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  {
    key: 'home',
    label: 'Home',
    subPage: 'home',
    icon: <HomeIcon className="w-3.5 h-3.5" />,
  },
  {
    key: 'explore',
    label: 'Explore',
    subPage: 'explore',
    icon: <CompassIcon className="w-3.5 h-3.5" />,
  },
  {
    key: 'sources',
    label: 'Sources',
    subPage: 'sources',
    icon: <DocIcon className="w-3.5 h-3.5" />,
  },
  {
    key: 'cases',
    label: 'Cases',
    subPage: 'cases',
    icon: <CasesIcon className="w-3.5 h-3.5" />,
  },
  {
    key: 'chat',
    label: 'Chat',
    subPage: 'chat',
    icon: <ChatIcon className="w-3.5 h-3.5" />,
  },
];

export function ProjectSidebarContent() {
  const router = useRouter();
  const workspace = useProjectWorkspaceContext();
  const nav = useNavigation();
  const activeSubPage = nav.activeProjectSubPage;
  const activeCaseId = nav.activeCaseId;

  const projectId = workspace?.project?.id;

  // Back button
  const backButton = (
    <Button
      variant="ghost"
      onClick={() => router.push('/')}
      className={cn(
        'flex items-center gap-1.5 px-3 py-2.5 w-full text-left justify-start h-auto rounded-none',
        'text-xs text-neutral-500 dark:text-neutral-400',
        'hover:text-neutral-700 dark:hover:text-neutral-300',
        'hover:bg-neutral-50 dark:hover:bg-neutral-800/50',
        'border-b border-neutral-200 dark:border-neutral-800'
      )}
    >
      <ArrowLeftIcon className="w-3.5 h-3.5" />
      <span>Home</span>
    </Button>
  );

  // Loading state
  if (!workspace || workspace.isLoading || !workspace.project) {
    return (
      <div className="flex flex-col h-full">
        {backButton}
        <div className="p-3 space-y-3">
          <Skeleton className="h-5 w-32" />
          <div className="mt-4 space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-6 w-full rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const { project, cases } = workspace;

  return (
    <div className="flex flex-col h-full">
      {backButton}

      {/* Project name */}
      <div className="px-3 py-2 border-b border-neutral-200 dark:border-neutral-800">
        <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 truncate">
          {project.title}
        </h2>
        {project.description && (
          <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate mt-0.5">
            {project.description}
          </p>
        )}
      </div>

      {/* Navigation + Cases */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
        {/* Primary navigation items */}
        {NAV_ITEMS.map((item) => {
          const href =
            item.subPage === 'home'
              ? `/projects/${project.id}`
              : `/projects/${project.id}/${item.subPage}`;

          const isActive = activeSubPage === item.subPage;

          return (
            <Link
              key={item.key}
              href={href}
              className={cn(
                'flex items-center gap-2 w-full px-2 py-1.5 rounded-md',
                'transition-colors duration-150',
                isActive
                  ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 font-medium'
                  : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 hover:text-neutral-800 dark:hover:text-neutral-200'
              )}
            >
              <span className={cn('shrink-0', isActive ? 'text-neutral-600 dark:text-neutral-300' : 'text-neutral-400 dark:text-neutral-500')}>
                {item.icon}
              </span>
              <span className="text-xs truncate">{item.label}</span>
            </Link>
          );
        })}

        {/* Cases section */}
        <div className="pt-3 mt-2 border-t border-neutral-200 dark:border-neutral-800">
          <h4 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1 px-2">
            Cases
          </h4>
          {cases.length === 0 ? (
            <div className="px-2 py-1">
              <p className="text-xs text-neutral-400 dark:text-neutral-500">
                No cases yet
              </p>
              <button
                onClick={() => router.push(`/projects/${project.id}/cases`)}
                className="text-xs text-accent-600 dark:text-accent-400 hover:text-accent-700 dark:hover:text-accent-300 mt-0.5"
              >
                + New case
              </button>
            </div>
          ) : (
            <div className="space-y-0.5">
              {cases
                .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
                .map((caseItem) => (
                  <CaseRow
                    key={caseItem.id}
                    caseItem={caseItem}
                    isActive={activeCaseId === caseItem.id}
                  />
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Case Row ──────────────────────────────────────────

function CaseRow({ caseItem, isActive }: { caseItem: Case; isActive: boolean }) {
  return (
    <Link
      href={`/cases/${caseItem.id}`}
      className={cn(
        'flex items-center gap-1.5 px-2 py-1 rounded-md',
        'transition-colors duration-150',
        isActive
          ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 font-medium'
          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800'
      )}
    >
      <CaseStageDot status={caseItem.status} />
      <span className="text-xs truncate flex-1">{caseItem.title}</span>
      <ChevronIcon className="w-3 h-3 text-neutral-300 dark:text-neutral-600 shrink-0" />
    </Link>
  );
}

// ─── Helpers ──────────────────────────────────────────

function CaseStageDot({ status }: { status: string }) {
  const color =
    status === 'decided'
      ? 'bg-success-500'
      : status === 'active'
        ? 'bg-accent-400'
        : 'bg-neutral-300 dark:bg-neutral-600';
  return <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', color)} />;
}

// ─── Icons ──────────────────────────────────────────

function HomeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CompassIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DocIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CasesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="9" y="3" width="6" height="4" rx="1" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChatIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
