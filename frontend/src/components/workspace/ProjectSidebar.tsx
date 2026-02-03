/**
 * Project Sidebar - Left navigation for workspace
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ProjectSidebarSkeleton } from '@/components/ui/skeleton';
import type { Project } from '@/lib/types/project';
import { cn } from '@/lib/utils';
import { SettingsModal } from '@/components/settings/SettingsModal';

interface ProjectSidebarProps {
  projects: Project[];
  selectedProjectId?: string | null;
  onSelectProject: (projectId: string | null) => void;
  onCreateProject: () => void;
  isCreatingProject: boolean;
  isLoading?: boolean;
}

export function ProjectSidebar({
  projects,
  selectedProjectId,
  onSelectProject,
  onCreateProject,
  isCreatingProject,
  isLoading,
}: ProjectSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Show skeleton during initial load
  if (isLoading) {
    return <ProjectSidebarSkeleton />;
  }

  if (collapsed) {
    return (
      <div className="w-16 bg-white dark:bg-primary-900 border-r border-neutral-200 dark:border-neutral-800 flex flex-col">
        <button
          onClick={() => setCollapsed(false)}
          className="p-4 hover:bg-neutral-50 dark:hover:bg-primary-800 transition-colors"
          title="Expand sidebar"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="w-80 bg-white dark:bg-primary-900 border-r border-neutral-200 dark:border-neutral-800 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-neutral-200 dark:border-neutral-800">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-primary-900 dark:text-primary-50">
            Workspace
          </h2>
          <button
            onClick={() => setCollapsed(true)}
            className="p-1 hover:bg-neutral-100 dark:hover:bg-primary-800 rounded transition-colors"
            title="Collapse sidebar"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <Button
          onClick={onCreateProject}
          disabled={isCreatingProject}
          className="w-full"
          size="sm"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Project
        </Button>
      </div>

      {/* All Projects View */}
      <button
        onClick={() => onSelectProject(null)}
        className={cn(
          'px-4 py-3 text-left border-b border-neutral-200 dark:border-neutral-800 transition-colors',
          selectedProjectId === null
            ? 'bg-accent-50 dark:bg-accent-900/20 border-l-4 border-l-accent-600'
            : 'hover:bg-neutral-50 dark:hover:bg-primary-800'
        )}
      >
        <div className="flex items-center gap-3">
          <svg className="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm text-primary-900 dark:text-primary-50">
              All Projects
            </div>
            <div className="text-xs text-neutral-600 dark:text-neutral-400">
              Overview
            </div>
          </div>
        </div>
      </button>

      {/* Projects List */}
      <div className="flex-1 overflow-y-auto">
        {projects.length === 0 ? (
          <div className="p-4 text-center text-sm text-neutral-500 dark:text-neutral-400">
            No projects yet. Create one to get started.
          </div>
        ) : (
          <div className="py-2">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => onSelectProject(project.id)}
                className={cn(
                  'w-full px-4 py-3 text-left transition-colors',
                  selectedProjectId === project.id
                    ? 'bg-accent-50 dark:bg-accent-900/20 border-l-4 border-l-accent-600'
                    : 'hover:bg-neutral-50 dark:hover:bg-primary-800 border-l-4 border-l-transparent'
                )}
              >
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-neutral-600 dark:text-neutral-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm text-primary-900 dark:text-primary-50 truncate">
                      {project.title}
                    </div>
                    {project.description && (
                      <div className="text-xs text-neutral-600 dark:text-neutral-400 truncate mt-0.5">
                        {project.description}
                      </div>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-neutral-200 dark:border-neutral-800">
        <div className="space-y-1">
          <Link
            href="/chat"
            className="flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-primary-800 rounded transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            All Conversations
          </Link>
          <Link
            href="/workspace/cases"
            className="flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-primary-800 rounded transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            All Cases
          </Link>
          <Link
            href="/workspace/inquiries"
            className="flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-primary-800 rounded transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            All Inquiries
          </Link>
          
          <div className="pt-2 mt-2 border-t border-neutral-200 dark:border-neutral-800">
            <button
              onClick={() => setSettingsOpen(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-primary-800 rounded transition-colors w-full"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Settings
            </button>
          </div>
        </div>
      </div>

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
