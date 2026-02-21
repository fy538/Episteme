/**
 * React Query hook for project insights (agent-discovered observations).
 *
 * Exposes error and mutation loading states.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { graphAPI } from '@/lib/api/graph';
import type { InsightStatus } from '@/lib/types/hierarchy';

export function useProjectInsights(projectId: string | undefined) {
  const queryClient = useQueryClient();

  const insightsQuery = useQuery({
    queryKey: ['project-insights', projectId],
    queryFn: () => graphAPI.getInsights(projectId!, { status: 'active' }),
    enabled: !!projectId,
    staleTime: 60_000,
  });

  const updateMutation = useMutation({
    mutationFn: ({ insightId, status }: { insightId: string; status: InsightStatus }) => {
      if (!projectId) return Promise.reject(new Error('No project ID'));
      return graphAPI.updateInsight(projectId, insightId, { status });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-insights', projectId] });
    },
  });

  return {
    insights: insightsQuery.data ?? [],
    isLoading: insightsQuery.isLoading,
    error: insightsQuery.error,
    isError: insightsQuery.isError,
    acknowledge: (id: string) => updateMutation.mutate({ insightId: id, status: 'acknowledged' }),
    dismiss: (id: string) => updateMutation.mutate({ insightId: id, status: 'dismissed' }),
    updatingInsightId: updateMutation.isPending
      ? (updateMutation.variables?.insightId ?? null)
      : null,
  };
}
