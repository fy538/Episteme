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

import { useCallback } from 'react';
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
