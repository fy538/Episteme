/**
 * useConversationState Hook
 *
 * State management for the standalone /chat/[threadId] conversation page.
 * Composes useCompanionState for the companion panel and thread metadata.
 *
 * Chat panel state (messages, streaming) is managed entirely by ChatPanel's
 * internal useChatPanelState — NOT duplicated here. The companion's
 * streamCallbacks are passed to ChatPanel via the page-level wiring.
 */

'use client';

import { useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { chatAPI } from '@/lib/api/chat';
import { useCompanionState } from './useCompanionState';

interface UseConversationStateOptions {
  threadId: string;
}

export function useConversationState({ threadId }: UseConversationStateOptions) {
  const router = useRouter();
  const queryClient = useQueryClient();

  // Companion state (reflection, action hints, receipts)
  const companion = useCompanionState({
    mode: 'casual',
  });

  // Thread metadata
  const { data: thread } = useQuery({
    queryKey: ['thread', threadId],
    queryFn: () => chatAPI.getThread(threadId),
    enabled: !!threadId,
    staleTime: 60_000,
  });

  // Load existing conversation structure on mount
  const { data: existingStructure } = useQuery({
    queryKey: ['thread-structure', threadId],
    queryFn: () => chatAPI.getConversationStructure(threadId),
    enabled: !!threadId,
    staleTime: 30_000,
  });

  // Load episode history on mount
  const { data: episodesData } = useQuery({
    queryKey: ['thread-episodes', threadId],
    queryFn: () => chatAPI.getEpisodes(threadId),
    enabled: !!threadId,
    staleTime: 30_000,
  });

  // Hydrate companion with existing structure.
  // Including threadId ensures that if the component is reused across navigations,
  // the effect re-runs with the correct thread's data (React Query scopes by key,
  // but the effect must re-fire when the key changes).
  useEffect(() => {
    if (existingStructure) {
      companion.streamCallbacks.onCompanionStructure?.(existingStructure);
    }
    // Only run when existingStructure or threadId changes, not on every companion change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [existingStructure, threadId]);

  // Hydrate companion with episode history (same threadId guard as above)
  useEffect(() => {
    if (episodesData) {
      // Only load sealed episodes into history (active one tracked via currentEpisode)
      const sealedEpisodes = episodesData.episodes.filter(ep => ep.sealed);
      companion.setEpisodeHistory(sealedEpisodes);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodesData, threadId]);

  // Create new thread and navigate to it
  const handleNewThread = useCallback(async () => {
    try {
      const newThread = await chatAPI.createThread();
      // Invalidate the threads list query so the sidebar updates
      queryClient.invalidateQueries({ queryKey: ['threads'] });
      router.push(`/chat/${newThread.id}`);
    } catch (err) {
      console.error('Failed to create thread:', err);
    }
  }, [router, queryClient]);

  // Archive the current thread
  const handleArchiveThread = useCallback(async () => {
    try {
      await chatAPI.updateThread(threadId, { archived: true });
      queryClient.invalidateQueries({ queryKey: ['threads'] });
      // Navigate to thread list
      router.push('/chat');
    } catch (err) {
      console.error('Failed to archive thread:', err);
    }
  }, [threadId, router, queryClient]);

  return {
    // Companion
    companion,

    // Thread metadata
    thread: thread ?? null,

    // Actions
    handleNewThread,
    handleArchiveThread,
  };
}
