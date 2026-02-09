/**
 * useProjectChat — manages chat panel state for the project page.
 *
 * Lazy thread creation: thread is only created when the first message is sent.
 * Persists threadId for the session so re-opening the panel reuses the same thread.
 */

import { useState, useCallback } from 'react';
import { chatAPI } from '@/lib/api/chat';

export function useProjectChat(projectId: string) {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isChatCollapsed, setIsChatCollapsed] = useState(false);
  const [isCreatingThread, setIsCreatingThread] = useState(false);

  const openChat = useCallback(
    async (initialMessage?: string) => {
      let tid = threadId;

      if (!tid) {
        setIsCreatingThread(true);
        try {
          const thread = await chatAPI.createThread(projectId);
          tid = thread.id;
          setThreadId(tid);
        } finally {
          setIsCreatingThread(false);
        }
      }

      setIsChatOpen(true);
      setIsChatCollapsed(false);
    },
    [projectId, threadId]
  );

  const toggleChat = useCallback(() => {
    if (!isChatOpen) return;
    setIsChatCollapsed((prev) => !prev);
  }, [isChatOpen]);

  const closeChat = useCallback(() => {
    setIsChatOpen(false);
    setIsChatCollapsed(false);
  }, []);

  return {
    threadId,
    isChatOpen,
    isChatCollapsed,
    isCreatingThread,
    openChat,
    toggleChat,
    closeChat,
  };
}
