/**
 * useProjectWorkspace Hook
 *
 * Fetches the data needed for the PROJECT-mode sidebar:
 * project metadata, cases, threads, document count, insights, hierarchy status.
 *
 * Accepts a projectId (null when not in project/case mode).
 * Reuses existing React Query hooks for caching and deduplication.
 */

import { useQuery } from '@tanstack/react-query';
import { projectsAPI } from '@/lib/api/projects';
import { casesAPI } from '@/lib/api/cases';
import { chatAPI } from '@/lib/api/chat';
import type { Project } from '@/lib/types/project';
import type { Case } from '@/lib/types/case';
import type { ChatThread } from '@/lib/types/chat';

export interface ProjectWorkspaceState {
  project: Project | null;
  cases: Case[];
  threads: ChatThread[];
  documentCount: number;
  insightCount: number;
  hierarchyStatus: 'none' | 'building' | 'ready' | 'failed';
  isLoading: boolean;
}

interface UseProjectWorkspaceOptions {
  projectId: string | null;
}

async function fetchProjectWorkspace(projectId: string): Promise<{
  project: Project;
  cases: Case[];
  threads: ChatThread[];
  documentCount: number;
}> {
  const [project, allCases, threads] = await Promise.all([
    projectsAPI.getProject(projectId),
    casesAPI.listCases(),
    chatAPI.listThreads({ project_id: projectId, archived: 'false' }),
  ]);

  const cases = allCases.filter((c) => c.project === projectId);

  return {
    project,
    cases,
    threads,
    documentCount: project.total_documents ?? 0,
  };
}

export function useProjectWorkspace({ projectId }: UseProjectWorkspaceOptions): ProjectWorkspaceState {
  const query = useQuery({
    queryKey: ['project-workspace', projectId],
    queryFn: () => fetchProjectWorkspace(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  });

  if (!projectId || !query.data) {
    return {
      project: null,
      cases: [],
      threads: [],
      documentCount: 0,
      insightCount: 0,
      hierarchyStatus: 'none',
      isLoading: !!projectId && query.isLoading,
    };
  }

  return {
    project: query.data.project,
    cases: query.data.cases,
    threads: query.data.threads,
    documentCount: query.data.documentCount,
    insightCount: 0, // Will be enriched by ProjectSidebarContent using useProjectInsights directly
    hierarchyStatus: 'none', // Will be enriched by ProjectSidebarContent using useProjectHierarchy directly
    isLoading: query.isLoading,
  };
}
