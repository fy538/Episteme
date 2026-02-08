/**
 * Standalone Conversation Page
 *
 * Route: /chat/[threadId]
 * Renders a full-screen chat experience with companion panel on the right.
 *
 * Supports initial message handoff from the home hero input via sessionStorage.
 */

'use client';

import { useState, useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ChatPanel } from '@/components/workspace/ChatPanel';
import { CompanionPanel } from '@/components/companion';
import { useConversationState } from '@/hooks/useConversationState';
import type { ChatThread } from '@/lib/types/chat';

export default function ConversationPage({
  params,
}: {
  params: { threadId: string };
}) {
  // Read initial message from sessionStorage (set by home hero input)
  const [initialMessage, setInitialMessage] = useState<string | null>(null);
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const msg = sessionStorage.getItem('episteme_initial_message');
      if (msg) {
        setInitialMessage(msg);
      }
    }
  }, []);

  const queryClient = useQueryClient();
  const { chatState, companion, thread } = useConversationState({
    threadId: params.threadId,
    initialMessage,
  });

  // Merge title update handler into companion stream callbacks
  const streamCallbacksWithTitle = useMemo(() => ({
    ...companion.streamCallbacks,
    onTitleUpdate: (title: string) => {
      queryClient.setQueryData(['thread', params.threadId], (old: ChatThread | undefined) =>
        old ? { ...old, title } : old
      );
      queryClient.invalidateQueries({ queryKey: ['threads'] });
    },
  }), [companion.streamCallbacks, params.threadId, queryClient]);

  return (
    <div className="absolute inset-0 flex">
      {/* Main chat area */}
      <div className="flex-1 min-w-0 flex flex-col">
        <ChatPanel
            threadId={params.threadId}
            variant="full"
            streamCallbacks={streamCallbacksWithTitle}
            initialMessage={initialMessage || undefined}
            onInitialMessageSent={() => {
              setInitialMessage(null);
              if (typeof window !== 'undefined') {
                sessionStorage.removeItem('episteme_initial_message');
              }
            }}
          />
      </div>

      {/* Companion panel (right sidebar) */}
      {companion.companionPosition === 'sidebar' ? (
        <div className="w-80 border-l border-neutral-200 dark:border-neutral-800 flex flex-col h-full overflow-hidden shrink-0">
          <CompanionPanel
            thinking={companion.companionThinking}
            mode="casual"
            position="sidebar"
            actionHints={companion.actionHints}
            signals={companion.signals}
            rankedSections={companion.rankedSections}
            pinnedSection={companion.pinnedSection}
            onPinSection={companion.setPinnedSection}
            onTogglePosition={companion.toggleCompanion}
            onClose={() => companion.setCompanionPosition('hidden')}
          />
        </div>
      ) : (
        /* Floating button to re-open the companion panel */
        <button
          onClick={companion.toggleCompanion}
          className="absolute top-3 right-3 z-30 w-8 h-8 rounded-lg bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 shadow-sm hover:shadow-md flex items-center justify-center text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 transition-all duration-200"
          aria-label="Open companion panel"
          title="Open companion panel"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      )}
    </div>
  );
}
