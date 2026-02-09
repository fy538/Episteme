/**
 * useProjectGraph — React Query hook for fetching project graph data.
 *
 * Uses the clustered endpoint to get backend-computed clusters and
 * quality metrics alongside nodes and edges.
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { graphAPI } from '@/lib/api/graph';
import type { ClusteredProjectGraph, ProjectGraph } from '@/lib/types/graph';

export function useProjectGraph(projectId: string | undefined) {
  return useQuery<ClusteredProjectGraph>({
    queryKey: ['project-graph', projectId],
    queryFn: async () => {
      try {
        return await graphAPI.getClusteredGraph(projectId!);
      } catch {
        // Fallback to basic graph endpoint if clustered fails
        const graph = await graphAPI.getGraph(projectId!);
        return {
          ...graph,
          clusters: [],
          cluster_quality: { modularity: 0, mean_conductance: 0, per_cluster: [] },
        };
      }
    },
    enabled: !!projectId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}
