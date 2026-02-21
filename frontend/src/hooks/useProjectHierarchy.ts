/**
 * React Query hook for the project's hierarchical cluster tree.
 *
 * Polls every 5s while the hierarchy is building (max 5min), then stops.
 * Exposes error, failed, and mutation loading states.
 */

import { useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { graphAPI } from '@/lib/api/graph';
import type { ClusterHierarchy } from '@/lib/types/hierarchy';

const MAX_POLL_DURATION_MS = 5 * 60 * 1000; // 5 minutes

export function useProjectHierarchy(projectId: string | undefined) {
  const queryClient = useQueryClient();
  const buildStartRef = useRef<number | null>(null);

  const hierarchyQuery = useQuery({
    queryKey: ['project-hierarchy', projectId],
    queryFn: () => graphAPI.getHierarchy(projectId!),
    enabled: !!projectId,
    staleTime: 60_000,
    refetchInterval: (query) => {
      const data = query.state.data as ClusterHierarchy | undefined;
      if (data?.status === 'building') {
        // Track when building started for timeout
        if (!buildStartRef.current) {
          buildStartRef.current = Date.now();
        }
        // Stop polling after MAX_POLL_DURATION_MS
        if (Date.now() - buildStartRef.current > MAX_POLL_DURATION_MS) {
          return false;
        }
        return 5_000;
      }
      // Reset start time when not building
      buildStartRef.current = null;
      return false;
    },
  });

  const rebuildMutation = useMutation({
    mutationFn: () => {
      if (!projectId) return Promise.reject(new Error('No project ID'));
      return graphAPI.rebuildHierarchy(projectId);
    },
    onSuccess: () => {
      buildStartRef.current = null; // Reset poll timer
      queryClient.invalidateQueries({ queryKey: ['project-hierarchy', projectId] });
    },
  });

  const status = hierarchyQuery.data?.status;

  return {
    hierarchy: hierarchyQuery.data ?? null,
    isLoading: hierarchyQuery.isLoading,
    isBuilding: status === 'building',
    isReady: status === 'ready',
    isFailed: status === 'failed',
    error: hierarchyQuery.error,
    isError: hierarchyQuery.isError,
    rebuild: rebuildMutation.mutate,
    isRebuilding: rebuildMutation.isPending,
  };
}
