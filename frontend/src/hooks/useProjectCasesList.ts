/**
 * useProjectCasesList
 *
 * Fetches cases for a project (using the enhanced serializer with decision
 * lifecycle data) and splits them into active vs decided lists.
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { casesAPI } from '@/lib/api/cases';
import type { Case } from '@/lib/types/case';

interface ProjectCasesList {
  activeCases: Case[];
  decidedCases: Case[];
  allCases: Case[];
  isLoading: boolean;
  error: unknown;
}

export function useProjectCasesList(projectId: string | undefined): ProjectCasesList {
  const { data, isLoading, error } = useQuery({
    queryKey: ['project-cases', projectId],
    queryFn: () => casesAPI.listProjectCases(projectId!),
    staleTime: 30_000,
    enabled: !!projectId,
  });

  const { activeCases, decidedCases } = useMemo(() => {
    if (!data) return { activeCases: [], decidedCases: [] };

    const active: Case[] = [];
    const decided: Case[] = [];

    for (const c of data) {
      if (c.status === 'decided' || c.status === 'archived') {
        decided.push(c);
      } else {
        active.push(c);
      }
    }

    // Sort active by updated_at descending
    active.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
    // Sort decided by decision date descending
    decided.sort((a, b) => {
      const aDate = a.decision_summary?.decided_at || a.updated_at;
      const bDate = b.decision_summary?.decided_at || b.updated_at;
      return new Date(bDate).getTime() - new Date(aDate).getTime();
    });

    return { activeCases: active, decidedCases: decided };
  }, [data]);

  return {
    activeCases,
    decidedCases,
    allCases: data || [],
    isLoading,
    error,
  };
}
