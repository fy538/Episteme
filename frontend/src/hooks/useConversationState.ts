/**
 * useConversationState Hook
 *
 * State management for the standalone /chat/[threadId] conversation page.
 * Composes existing useChatPanelState and useCompanionState hooks.
 * Adds thread metadata loading and thread-level actions.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { chatAPI } from '@/lib/api/chat';
import { useChatPanelState } from './useChatPanelState';
import { useCompanionState } from './useCompanionState';

interface UseConversationStateOptions {
  threadId: string;
  /** Initial message to send on mount (from hero input handoff) */
  initialMessage?: string | null;
}

export function useConversationState({ threadId, initialMessage }: UseConversationStateOptions) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [initialMessageSent, setInitialMessageSent] = useState(false);

  // Companion state (reflection, action hints, signals, receipts)
  const companion = useCompanionState({
    mode: 'casual',
  });

  // Chat panel state (streaming, messages, signals)
  // Note: onTitleUpdate is wired at the page level (ConversationPage)
  // where it can directly update the ChatPanel's streamCallbacks.
  const chatState = useChatPanelState({
    threadId,
    streamCallbacks: companion.streamCallbacks,
    mode: { mode: 'casual' },
    initialMessage: !initialMessageSent && initialMessage ? initialMessage : undefined,
    onInitialMessageSent: () => {
      setInitialMessageSent(true);
      // Clear sessionStorage after sending
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('episteme_initial_message');
      }
    },
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
    // Chat
    chatState,

    // Companion
    companion,

    // Thread metadata
    thread: thread ?? null,

    // Actions
    handleNewThread,
    handleArchiveThread,
  };
}
