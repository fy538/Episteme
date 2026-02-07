/**
 * useCaseQuery Hook
 *
 * React Query wrapper for case detail data.
 * Replaces manual fetching in case overview and case workspace pages.
 *
 * Benefits:
 * - Shared cache between overview and workspace views
 * - Background refetch when stale
 * - Automatic retry on failure
 */

import { useQuery } from '@tanstack/react-query';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { projectsAPI } from '@/lib/api/projects';
import type { Case, Inquiry } from '@/lib/types/case';
import type { Project } from '@/lib/types/project';

interface CaseQueryData {
  caseData: Case;
  inquiries: Inquiry[];
  project: Project | null;
}

async function fetchCaseData(caseId: string): Promise<CaseQueryData> {
  const [caseResp, inquiriesResp] = await Promise.all([
    casesAPI.getCase(caseId),
    inquiriesAPI.getByCase(caseId),
  ]);

  let project: Project | null = null;
  if (caseResp.project) {
    try {
      project = await projectsAPI.getProject(caseResp.project);
    } catch {
      // Project may not exist or user may not have access
    }
  }

  return {
    caseData: caseResp,
    inquiries: inquiriesResp,
    project,
  };
}

export function useCaseQuery(caseId: string, enabled = true) {
  return useQuery({
    queryKey: ['case', caseId],
    queryFn: () => fetchCaseData(caseId),
    enabled: enabled && !!caseId,
  });
}

/**
 * Pre-fetching helper for case list items
 * (can be called from list components to warm cache on hover)
 */
export function useCaseQueryKey(caseId: string) {
  return ['case', caseId];
}
