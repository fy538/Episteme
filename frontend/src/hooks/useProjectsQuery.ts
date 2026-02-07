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
import { calculateReadinessScore } from '@/lib/utils/intelligence-transforms';
import type { Project } from '@/lib/types/project';
import type { Case, Inquiry } from '@/lib/types/case';

export interface CaseWithInquiries extends Case {
  inquiries: Inquiry[];
  readinessScore: number;
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

  // For each case, load inquiries and basic readiness data
  // NOTE: We intentionally skip getBlindSpotPrompts here because it triggers
  // an expensive OpenAI API call per case. Gap analysis should only run
  // when explicitly requested (e.g., viewing case details).
  const casesWithData = await Promise.all(
    casesResp.map(async (caseItem) => {
      const [inquiries, landscape] = await Promise.all([
        inquiriesAPI.getByCase(caseItem.id).catch(() => []),
        casesAPI.getEvidenceLandscape(caseItem.id).catch(() => null),
      ]);

      const inquiryStats = landscape?.inquiries || { total: 0, resolved: 0 };
      // Calculate readiness without tensions/blindspots (they require LLM call)
      const readinessScore = calculateReadinessScore(
        inquiryStats,
        undefined,
        0, // tensionsCount - will be loaded on-demand
        0  // blindSpotsCount - will be loaded on-demand
      );

      return {
        ...caseItem,
        inquiries,
        readinessScore,
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
