/**
 * useProjectOrientation — React Query hook for lens-based project orientation.
 *
 * Fetches the current orientation, handles regeneration via mutation,
 * and streams generation progress via SSE for progressive finding rendering.
 *
 * Flow:
 * 1. GET /orientation/ — returns current orientation (or 'generating'/'none')
 * 2. If generating, auto-starts SSE stream
 * 3. SSE delivers: status → lead → findings (one by one) → angles → completed
 * 4. Each SSE event updates React Query cache for immediate UI rendering
 * 5. On completed, invalidates to fetch the full serialized response
 */

'use client';

import { useRef, useEffect, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { graphAPI } from '@/lib/api/graph';
import type { ProjectOrientation } from '@/lib/types/orientation';
import type { ProjectInsight } from '@/lib/types/hierarchy';

export function useProjectOrientation(projectId: string | undefined) {
  const queryClient = useQueryClient();
  const abortControllerRef = useRef<AbortController | null>(null);
  const isStreamingRef = useRef(false);
  const researchPollRef = useRef<{ interval: ReturnType<typeof setInterval>; timeout: ReturnType<typeof setTimeout> } | null>(null);

  // Memoize queryKey so downstream useCallback/useMutation references
  // stay stable across renders (prevents SSE stream restarts).
  const queryKey = useMemo(() => ['project-orientation', projectId], [projectId]);

  const orientationQuery = useQuery({
    queryKey,
    queryFn: () => graphAPI.getOrientation(projectId!),
    enabled: !!projectId,
    staleTime: 60_000,
    // Poll as fallback when SSE isn't active during generation
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status !== 'generating') return false;
      if (isStreamingRef.current) return false;
      return 3_000;
    },
  });

  // Start SSE stream for progressive finding rendering
  const startStream = useCallback((pid: string) => {
    if (isStreamingRef.current) return;

    const controller = new AbortController();
    abortControllerRef.current = controller;
    isStreamingRef.current = true;

    graphAPI
      .streamOrientation(
        pid,
        (event: { event: string; data: unknown }) => {
          if (event.event === 'status') {
            const data = event.data as { status: string; lens_type: string };
            queryClient.setQueryData(queryKey, (prev: ProjectOrientation | undefined) => {
              if (!prev) return prev;
              return { ...prev, status: data.status, lens_type: data.lens_type || prev.lens_type };
            });
          } else if (event.event === 'lead') {
            const data = event.data as { lead_text: string };
            queryClient.setQueryData(queryKey, (prev: ProjectOrientation | undefined) => {
              if (!prev) return prev;
              return { ...prev, lead_text: data.lead_text };
            });
          } else if (event.event === 'finding' || event.event === 'angle') {
            const finding = event.data as ProjectInsight;
            queryClient.setQueryData(queryKey, (prev: ProjectOrientation | undefined) => {
              if (!prev) return prev;
              // Append finding if not already present
              const existingIds = new Set(prev.findings.map((f) => f.id));
              if (existingIds.has(finding.id)) return prev;
              return { ...prev, findings: [...prev.findings, finding] };
            });
          } else if (event.event === 'completed') {
            isStreamingRef.current = false;
            queryClient.invalidateQueries({ queryKey });
          } else if (event.event === 'failed' || event.event === 'timeout') {
            isStreamingRef.current = false;
            queryClient.invalidateQueries({ queryKey });
          }
        },
        controller.signal,
      )
      .catch((err) => {
        if (err.name !== 'AbortError') {
          console.warn('Orientation SSE stream failed, falling back to polling:', err.message);
        }
      })
      .finally(() => {
        isStreamingRef.current = false;
        abortControllerRef.current = null;
      });
  }, [queryClient, queryKey]);

  // Abort SSE stream + research polling on unmount or projectId change
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      isStreamingRef.current = false;
      if (researchPollRef.current) {
        clearInterval(researchPollRef.current.interval);
        clearTimeout(researchPollRef.current.timeout);
        researchPollRef.current = null;
      }
    };
  }, [projectId]);

  // Auto-start SSE when we detect generating status
  useEffect(() => {
    const status = orientationQuery.data?.status;
    if (status === 'generating' && projectId && !isStreamingRef.current) {
      startStream(projectId);
    }
  }, [orientationQuery.data?.status, projectId, startStream]);

  // ── Mutations ──────────────────────────────────────────────

  const regenerateMutation = useMutation({
    mutationFn: () => graphAPI.regenerateOrientation(projectId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      if (projectId) {
        setTimeout(() => startStream(projectId), 500);
      }
    },
  });

  const generateAngleMutation = useMutation({
    mutationFn: (insightId: string) => graphAPI.generateAngle(projectId!, insightId),
    onSuccess: (data) => {
      // Update the finding's content in the cache
      queryClient.setQueryData(queryKey, (prev: ProjectOrientation | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          findings: prev.findings.map((f) =>
            f.id === data.insight_id ? { ...f, content: data.content } : f
          ),
        };
      });
    },
  });

  const researchMutation = useMutation({
    mutationFn: (insightId: string) => graphAPI.researchInsight(projectId!, insightId),
    onSuccess: (_data, insightId) => {
      // Optimistically set status to 'researching'
      queryClient.setQueryData(queryKey, (prev: ProjectOrientation | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          findings: prev.findings.map((f) =>
            f.id === insightId ? { ...f, status: 'researching' as const } : f
          ),
        };
      });
      // Clear any previous research poll
      if (researchPollRef.current) {
        clearInterval(researchPollRef.current.interval);
        clearTimeout(researchPollRef.current.timeout);
      }
      // Poll for result
      const interval = setInterval(async () => {
        if (!projectId) return;
        const orientation = await graphAPI.getOrientation(projectId);
        const finding = orientation.findings.find((f) => f.id === insightId);
        if (finding && finding.status !== 'researching') {
          clearInterval(interval);
          researchPollRef.current = null;
          queryClient.setQueryData(queryKey, orientation);
        }
      }, 3_000);
      // Stop polling after 60s
      const timeout = setTimeout(() => {
        clearInterval(interval);
        researchPollRef.current = null;
      }, 60_000);
      researchPollRef.current = { interval, timeout };
    },
  });

  const orientation = orientationQuery.data ?? null;

  return {
    orientation,
    isLoading: orientationQuery.isLoading,
    isGenerating: orientation?.status === 'generating',
    isStreaming: isStreamingRef.current,
    regenerate: regenerateMutation.mutate,
    isRegenerating: regenerateMutation.isPending,
    generateAngle: generateAngleMutation.mutate,
    isGeneratingAngle: generateAngleMutation.isPending,
    generatingAngleId: generateAngleMutation.isPending
      ? (generateAngleMutation.variables ?? null)
      : null,
    researchGap: researchMutation.mutate,
    isResearching: researchMutation.isPending,
  };
}
