/**
 * useCaseGraph — React Query hooks for case-scoped graph data and analysis.
 *
 * Mirrors useProjectGraph but fetches case-scoped graph and analysis data.
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { graphAPI } from '@/lib/api/graph';
import { casesAPI } from '@/lib/api/cases';
import type { ProjectGraph } from '@/lib/types/graph';
import type { CaseAnalysis } from '@/lib/types/case-extraction';

/**
 * Fetch graph data scoped to a specific case.
 * Returns case-extracted nodes + referenced project nodes + visible edges.
 */
export function useCaseGraph(projectId: string | undefined, caseId: string | undefined) {
  return useQuery<ProjectGraph>({
    queryKey: ['case-graph', projectId, caseId],
    queryFn: () => graphAPI.getCaseGraph(projectId!, caseId!),
    enabled: !!projectId && !!caseId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

/**
 * Fetch analysis results for a case (readiness, blind spots, assumptions, tensions).
 * Available after the extraction pipeline completes.
 */
export function useCaseAnalysis(caseId: string | undefined) {
  return useQuery<CaseAnalysis>({
    queryKey: ['case-analysis', caseId],
    queryFn: () => casesAPI.getAnalysis(caseId!),
    enabled: !!caseId,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}
