/**
 * useProjectsQuery Hook
 *
 * React Query wrapper for project + case data loading.
 * Replaces the manual useState + useEffect pattern in app/page.tsx.
 *
 * Benefits:
 * - Automatic caching (60s staleTime from provider config)
 * - Deduplication: multiple components using this won't trigger duplicate requests
 * - Background refetch on stale
 * - Error retry (3 attempts by default)
 */

import { useQuery } from '@tanstack/react-query';
import { projectsAPI } from '@/lib/api/projects';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import type { Project } from '@/lib/types/project';
import type { Case, Inquiry } from '@/lib/types/case';

export interface CaseWithInquiries extends Case {
  inquiries: Inquiry[];
  tensionsCount: number;
  blindSpotsCount: number;
}

export interface ProjectWithCases extends Project {
  cases: CaseWithInquiries[];
}

async function fetchProjectsWithCases(): Promise<ProjectWithCases[]> {
  // Load projects and cases in parallel
  const [projectsResp, casesResp] = await Promise.all([
    projectsAPI.listProjects(),
    casesAPI.listCases(),
  ]);

  // For each case, load inquiries
  // NOTE: Tensions and blind spots are loaded on-demand when viewing case
  // details, since gap analysis triggers expensive LLM calls.
  const casesWithData = await Promise.all(
    casesResp.map(async (caseItem) => {
      const inquiries = await inquiriesAPI.getByCase(caseItem.id).catch(() => []);

      return {
        ...caseItem,
        inquiries,
        tensionsCount: 0,    // Loaded on-demand when viewing case
        blindSpotsCount: 0,  // Loaded on-demand when viewing case
      };
    })
  );

  // Group cases by project
  const projectsWithCases: ProjectWithCases[] = projectsResp.map((project) => ({
    ...project,
    cases: casesWithData.filter((c) => c.project === project.id),
  }));

  // Add cases without projects to "Ungrouped"
  const orphanCases = casesWithData.filter((c) => !c.project);
  if (orphanCases.length > 0) {
    projectsWithCases.push({
      id: 'no-project',
      title: 'Ungrouped Cases',
      description: 'Cases not assigned to a project',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      cases: orphanCases,
    });
  }

  return projectsWithCases;
}

export function useProjectsQuery(enabled = true) {
  return useQuery({
    queryKey: ['projects-with-cases'],
    queryFn: fetchProjectsWithCases,
    enabled,
  });
}
