/**
 * HomeSidebarContent
 *
 * Sidebar content for HOME mode (zoomed out).
 * Shows all projects as compact rows + "Scratch" section for unscoped threads.
 *
 * Layout:
 *   ┌─────────────────────────┐
 *   │ PROJECTS      [+ New]   │
 *   │  Go-to-Market   3 cases │
 *   │  Fundraising    1 case  │
 *   │─────────────────────────│
 *   │ RECENT                  │
 *   │  "pricing chat"   2:30  │
 *   │  "market sizing"  Mon   │
 *   └─────────────────────────┘
 */

'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useProjectsQuery } from '@/hooks/useProjectsQuery';
import { useThreadsListQuery } from '@/hooks/useThreadsQuery';
import { formatThreadTime } from '@/hooks/useThreadsQuery';
import { NewProjectModal } from '@/components/home/NewProjectModal';
import { Spinner } from '@/components/ui/spinner';
import { Button } from '@/components/ui/button';
import { PlusIcon } from '@/components/ui/icons';
import { cn } from '@/lib/utils';
import { useNavigation } from '../NavigationProvider';
import type { ChatThread } from '@/lib/types/chat';

export function HomeSidebarContent() {
  const router = useRouter();
  const nav = useNavigation();
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showAllThreads, setShowAllThreads] = useState(false);

  const { data: projects = [], isLoading: projectsLoading } = useProjectsQuery();
  const { data: allThreads = [], isLoading: threadsLoading } = useThreadsListQuery();

  // Scratch threads: threads not assigned to any project
  const scratchThreads = allThreads.filter((t) => !t.project);

  const isLoading = projectsLoading;

  // Filter out the synthetic "Ungrouped Cases" project
  const realProjects = projects.filter((p) => p.id !== 'no-project');

  return (
    <>
      <div className="flex flex-col h-full">
        {/* Projects section */}
        <div className="px-3 py-2">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
              Projects
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowNewProjectModal(true)}
              className="flex items-center gap-0.5 px-1.5 py-1 h-auto text-xs font-medium shrink-0 bg-accent-50 text-accent-700 dark:bg-accent-900/30 dark:text-accent-300 hover:bg-accent-100 dark:hover:bg-accent-900/50"
            >
              <PlusIcon className="w-3 h-3" />
              New
            </Button>
          </div>
        </div>

        {/* Project list */}
        <div className="flex-1 min-h-0 overflow-y-auto px-2">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Spinner className="text-accent-600" />
            </div>
          ) : realProjects.length === 0 ? (
            <div className="text-center py-8 px-4">
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                No projects yet
              </p>
              <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
                Create a project to organize your research
              </p>
            </div>
          ) : (
            <div className="space-y-0.5">
              {realProjects.map((project) => (
                <ProjectRow
                  key={project.id}
                  title={project.title}
                  caseCount={project.cases.length}
                  isActive={false}
                  onClick={() => router.push(`/projects/${project.id}`)}
                />
              ))}
            </div>
          )}

          {/* Scratch threads */}
          {scratchThreads.length > 0 && (
            <div className="mt-4">
              <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1 px-2">
                Recent
              </h3>
              <div className="space-y-0.5">
                {(showAllThreads ? scratchThreads : scratchThreads.slice(0, 8)).map((thread) => (
                  <ScratchThreadRow
                    key={thread.id}
                    thread={thread}
                    isActive={thread.id === nav.activeThreadId}
                  />
                ))}
                {scratchThreads.length > 8 && !showAllThreads && (
                  <button
                    onClick={() => setShowAllThreads(true)}
                    className="text-xs text-accent-600 dark:text-accent-400 hover:text-accent-700 dark:hover:text-accent-300 px-2 py-1"
                  >
                    Show all {scratchThreads.length}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <NewProjectModal
        isOpen={showNewProjectModal}
        onClose={() => setShowNewProjectModal(false)}
        onCreated={(project) => {
          setShowNewProjectModal(false);
          router.push(`/projects/${project.id}`);
        }}
      />
    </>
  );
}

// ─── Project Row ──────────────────────────────────────────

function ProjectRow({
  title,
  caseCount,
  isActive,
  onClick,
}: {
  title: string;
  caseCount: number;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 w-full px-2 py-1.5 rounded-md text-left',
        'transition-colors duration-150',
        isActive
          ? 'bg-accent-50 dark:bg-accent-900/30 text-accent-700 dark:text-accent-300'
          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800'
      )}
    >
      <FolderIcon className="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 shrink-0" />
      <span className="text-xs truncate flex-1">{title}</span>
      <span className="text-xs text-neutral-400 dark:text-neutral-500 shrink-0">
        {caseCount}
      </span>
      <ChevronRightSmall className="w-3 h-3 text-neutral-300 dark:text-neutral-600 shrink-0" />
    </button>
  );
}

// ─── Scratch Thread Row ──────────────────────────────────

function ScratchThreadRow({ thread, isActive }: { thread: ChatThread; isActive: boolean }) {
  const title = thread.title || thread.latest_message?.content?.slice(0, 50) || 'New conversation';

  return (
    <Link
      href={`/chat/${thread.id}`}
      className={cn(
        'flex items-center gap-1.5 px-2 py-1 rounded-md',
        'transition-colors duration-150',
        isActive
          ? 'bg-accent-50 dark:bg-accent-900/30 text-accent-700 dark:text-accent-300'
          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800'
      )}
    >
      <span className="text-xs truncate flex-1">{title}</span>
      <span className="text-xs text-neutral-400 shrink-0">
        {formatThreadTime(thread.updated_at)}
      </span>
    </Link>
  );
}

// ─── Icons ──────────────────────────────────────────

function FolderIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronRightSmall({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
