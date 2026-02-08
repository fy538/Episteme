/**
 * useCaseHome Hook
 *
 * Fetches aggregated case home data via the getCaseHome() endpoint.
 * Provides loading state, derived computations for stage/assumption/criteria
 * summaries, and a refresh function.
 *
 * Used by the CaseHome component (the default main content view).
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { plansAPI } from '@/lib/api/plans';
import type { CaseStage, CaseHomeData } from '@/lib/types/plan';

interface AssumptionSummary {
  untested: number;
  confirmed: number;
  challenged: number;
  refuted: number;
  total: number;
}

interface CriteriaProgress {
  met: number;
  total: number;
}

interface UseCaseHomeReturn {
  data: CaseHomeData | null;
  isLoading: boolean;
  error: Error | null;
  stage: CaseStage;
  assumptionSummary: AssumptionSummary;
  criteriaProgress: CriteriaProgress;
  refresh: () => void;
}

export function useCaseHome(caseId: string): UseCaseHomeReturn {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['case-home', caseId],
    queryFn: () => plansAPI.getCaseHome(caseId),
    staleTime: 30_000, // 30 seconds
  });

  const stage: CaseStage = data?.plan?.stage ?? 'exploring';

  const assumptionSummary = useMemo<AssumptionSummary>(() => {
    const assumptions = data?.plan?.current_content?.assumptions ?? [];
    return {
      untested: assumptions.filter(a => a.status === 'untested').length,
      confirmed: assumptions.filter(a => a.status === 'confirmed').length,
      challenged: assumptions.filter(a => a.status === 'challenged').length,
      refuted: assumptions.filter(a => a.status === 'refuted').length,
      total: assumptions.length,
    };
  }, [data?.plan?.current_content?.assumptions]);

  const criteriaProgress = useMemo<CriteriaProgress>(() => {
    const criteria = data?.plan?.current_content?.decision_criteria ?? [];
    return {
      met: criteria.filter(c => c.is_met).length,
      total: criteria.length,
    };
  }, [data?.plan?.current_content?.decision_criteria]);

  return {
    data: data ?? null,
    isLoading,
    error: error as Error | null,
    stage,
    assumptionSummary,
    criteriaProgress,
    refresh: refetch,
  };
}
