/**
 * Home Page
 *
 * Route: /
 * The app entry point. Shows:
 *   1. Hero chat input for quick exploration (creates scratch thread)
 *   2. Needs-attention items across all projects
 *   3. Active projects grid with quick access
 *
 * The sidebar shows HOME mode (project list + scratch threads).
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { MessageInput } from '@/components/chat/MessageInput';
import { SuggestedActions } from '@/components/home/SuggestedActions';
import { StarterPrompts } from '@/components/home/StarterPrompts';
import { ProjectCard } from '@/components/home/ProjectCard';
import { NewProjectModal } from '@/components/home/NewProjectModal';
import { useHomeState } from '@/hooks/useHomeState';
import { useHomeDashboard } from '@/hooks/useHomeDashboard';
import { useProjectsQuery } from '@/hooks/useProjectsQuery';
import { cn } from '@/lib/utils';

export default function HomePage() {
  const router = useRouter();
  const homeState = useHomeState();
  const { actionItems, isLoading: dashboardLoading } = useHomeDashboard();
  const { data: projects = [], isLoading: projectsLoading } = useProjectsQuery();
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [userName, setUserName] = useState('');

  useEffect(() => {
    const name = localStorage.getItem('episteme_user_name') || '';
    if (name) {
      setUserName(name.split(/\s+/)[0]);
    }
  }, []);

  // Filter out synthetic "no-project" group
  const realProjects = projects.filter((p) => p.id !== 'no-project');
  const isLoading = dashboardLoading || projectsLoading;

  // First-time user: no projects and no case-based action items.
  // Guard on actionItems.length > 0 to avoid .every() returning true on an empty
  // array (which can happen if projectsLoading finishes before dashboardLoading).
  const isFirstTimeUser = !isLoading && realProjects.length === 0
    && actionItems.length > 0
    && actionItems.every(item => item.type === 'new_exploration');

  return (
    <>
      <div className="flex flex-col h-full bg-white dark:bg-neutral-950 overflow-y-auto">
        <div
          className={cn(
            'flex-1 flex flex-col items-center px-6 pt-[12vh] transition-all duration-200 ease-out',
            homeState.isTransitioning ? 'opacity-0 scale-[0.98] blur-[2px]' : 'opacity-100 scale-100'
          )}
        >
          {/* ─── Header ─── */}
          <div className="w-full max-w-3xl mb-5">
            <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100 tracking-tight">
              {userName ? `Welcome back, ${userName}` : 'What would you like to explore?'}
            </h1>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
              Start a conversation, or dive into a project.
            </p>
          </div>

          {/* ─── Hero Input ─── */}
          <div className="w-full max-w-3xl mb-6">
            <div className="rounded-lg border border-neutral-200/60 dark:border-neutral-700/50 overflow-hidden">
              <MessageInput
                variant="hero"
                onSend={homeState.handleHeroSend}
                placeholder={homeState.currentPlaceholder}
              />
            </div>
            {homeState.networkError && (
              <div className="mt-2 flex items-center gap-2 text-xs text-red-600 dark:text-red-400">
                <span>Failed to start conversation. Please try again.</span>
                <button
                  onClick={() => homeState.setNetworkError(false)}
                  className="underline hover:no-underline"
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>

          {/* ─── Starter Prompts (first-time users) ─── */}
          {isFirstTimeUser && (
            <div className="w-full max-w-3xl mb-6">
              <StarterPrompts onSelect={homeState.handleHeroSend} />
            </div>
          )}

          {/* ─── Needs Attention ─── */}
          {!isLoading && actionItems.length > 0 && !isFirstTimeUser && (
            <div className="w-full max-w-3xl mb-6">
              <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">
                Needs attention
              </h2>
              <SuggestedActions items={actionItems} />
            </div>
          )}

          {/* ─── Projects Grid ─── */}
          {!isLoading && (
            <div className="w-full max-w-3xl mb-8">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                  Projects
                </h2>
                <button
                  onClick={() => setShowNewProjectModal(true)}
                  className="text-xs text-accent-600 dark:text-accent-400 hover:text-accent-700 dark:hover:text-accent-300 font-medium transition-colors"
                >
                  + New project
                </button>
              </div>
              {realProjects.length === 0 ? (
                <button
                  onClick={() => setShowNewProjectModal(true)}
                  className={cn(
                    'w-full text-left p-6 rounded-lg border-2 border-dashed',
                    'border-neutral-200 dark:border-neutral-800',
                    'hover:border-accent-300 dark:hover:border-accent-700',
                    'transition-colors duration-150'
                  )}
                >
                  <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
                    Create your first project
                  </p>
                  <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
                    Upload documents and start organizing your research.
                  </p>
                </button>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {realProjects.map((project) => (
                    <ProjectCard
                      key={project.id}
                      project={project}
                      onClick={() => router.push(`/projects/${project.id}`)}
                    />
                  ))}
                </div>
              )}
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
