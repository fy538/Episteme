/**
 * ProjectWorkspaceProvider
 *
 * Shared context that provides project workspace data to the sidebar
 * and any component that needs project-level information.
 *
 * Resolves the active project ID from multiple sources:
 *   - project mode → uses that projectId directly
 *   - case mode → resolves projectId from the case data
 *   - home mode on /chat/:id → checks if the thread belongs to a project,
 *     and if so overrides sidebar to project mode
 *   - home mode otherwise → null (no fetch)
 */

'use client';

import { createContext, useContext, useEffect, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigation } from '@/components/navigation/NavigationProvider';
import { useProjectWorkspace, type ProjectWorkspaceState } from '@/hooks/useProjectWorkspace';
import { chatAPI } from '@/lib/api/chat';
import { casesAPI } from '@/lib/api/cases';

const ProjectWorkspaceContext = createContext<ProjectWorkspaceState | null>(null);

export function ProjectWorkspaceProvider({ children }: { children: ReactNode }) {
  const { sidebarMode, activeThreadId, activeCaseId, setSidebarModeOverride } = useNavigation();

  // --- Thread → Project detection (for /chat/:id routes) ---
  // When in home mode and viewing a thread, check if it belongs to a project
  const isOnThread = sidebarMode.mode === 'home' && !!activeThreadId;
  const { data: threadData } = useQuery({
    queryKey: ['thread', activeThreadId],
    queryFn: () => chatAPI.getThread(activeThreadId!),
    enabled: isOnThread,
    staleTime: 60_000,
  });

  // Override sidebar mode when thread has a project
  useEffect(() => {
    if (isOnThread && threadData?.project) {
      setSidebarModeOverride({ mode: 'project', projectId: threadData.project });
    } else if (isOnThread && threadData && !threadData.project) {
      // Thread loaded but has no project — ensure override is cleared
      setSidebarModeOverride(null);
    }
  }, [isOnThread, threadData?.project, setSidebarModeOverride, threadData]);

  // --- Case → Project resolution (for /cases/:id routes) ---
  // When in case mode, resolve the project ID from the case data
  const { data: caseData } = useQuery({
    queryKey: ['case-for-project', activeCaseId],
    queryFn: () => casesAPI.getCase(activeCaseId!),
    enabled: sidebarMode.mode === 'case' && !!activeCaseId,
    staleTime: 60_000,
  });

  // --- Determine the effective project ID ---
  let projectId: string | null = null;
  if (sidebarMode.mode === 'project') {
    projectId = sidebarMode.projectId;
  } else if (sidebarMode.mode === 'case' && caseData?.project) {
    projectId = caseData.project;
  }

  const workspace = useProjectWorkspace({ projectId });

  return (
    <ProjectWorkspaceContext.Provider value={projectId ? workspace : null}>
      {children}
    </ProjectWorkspaceContext.Provider>
  );
}

/** Returns project workspace state or null when not in project mode. */
export function useProjectWorkspaceContext(): ProjectWorkspaceState | null {
  return useContext(ProjectWorkspaceContext);
}
