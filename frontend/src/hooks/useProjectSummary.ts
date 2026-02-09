/**
 * useProjectSummary — React Query hook for project summary.
 *
 * Fetches the current summary, handles regeneration via mutation,
 * and polls during generation.
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { graphAPI } from '@/lib/api/graph';
import type { ProjectSummary } from '@/lib/types/graph';

export function useProjectSummary(projectId: string | undefined) {
  const queryClient = useQueryClient();

  const summaryQuery = useQuery({
    queryKey: ['project-summary', projectId],
    queryFn: () => graphAPI.getSummary(projectId!),
    enabled: !!projectId,
    staleTime: 60_000,
    // Poll every 5s while summary is being generated
    refetchInterval: (query) =>
      query.state.data?.status === 'generating' ? 5_000 : false,
  });

  const regenerateMutation = useMutation({
    mutationFn: () => graphAPI.regenerateSummary(projectId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-summary', projectId] });
    },
  });

  const summary = summaryQuery.data ?? null;

  return {
    summary,
    isLoading: summaryQuery.isLoading,
    isStale: summary?.is_stale ?? false,
    isGenerating: summary?.status === 'generating',
    regenerate: regenerateMutation.mutate,
    isRegenerating: regenerateMutation.isPending,
  };
}
