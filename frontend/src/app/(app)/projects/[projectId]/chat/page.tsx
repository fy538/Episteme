/**
 * Project Chat Page
 *
 * Route: /projects/[projectId]/chat
 *
 * Two states:
 *   A) No active thread → Chat landing with hero input + recent threads
 *   B) Active thread (from ?thread= param) → Full ChatPanel + CompanionPanel
 *
 * Supports initial message handoff from the project home hero input
 * via sessionStorage (same pattern as /chat/[threadId]/page.tsx).
 */

'use client';

import { useState, useCallback, useMemo } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { ChatPanel } from '@/components/workspace/ChatPanel';
import { CompanionPanel } from '@/components/companion';
import { MessageInput } from '@/components/chat/MessageInput';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { useConversationState } from '@/hooks/useConversationState';
import { useProjectThreads } from '@/hooks/useProjectThreads';
import { chatAPI } from '@/lib/api/chat';
import type { ChatThread } from '@/lib/types/chat';

export default function ProjectChatPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const projectId = params.projectId as string;
  const threadId = searchParams.get('thread');
  const queryClient = useQueryClient();

  if (threadId) {
    return (
      <ActiveThreadView
        projectId={projectId}
        threadId={threadId}
        router={router}
        queryClient={queryClient}
      />
    );
  }

  return (
    <ChatLanding
      projectId={projectId}
      router={router}
    />
  );
}

// ─── Chat Landing (no active thread) ───────────────────────────

function ChatLanding({
  projectId,
  router,
}: {
  projectId: string;
  router: ReturnType<typeof useRouter>;
}) {
  const [isSending, setIsSending] = useState(false);
  const { data: threads, isLoading: isThreadsLoading } = useProjectThreads(projectId);

  const handleSend = useCallback(
    async (content: string) => {
      if (!content.trim() || isSending) return;
      try {
        setIsSending(true);
        const thread = await chatAPI.createThread(projectId);
        if (typeof window !== 'undefined') {
          sessionStorage.setItem(
            'episteme_initial_message',
            JSON.stringify({ threadId: thread.id, content })
          );
        }
        router.push(`/projects/${projectId}/chat?thread=${thread.id}`);
      } catch (err) {
        console.error('Failed to create thread:', err);
        setIsSending(false);
      }
    },
    [projectId, router, isSending]
  );

  const handleThreadClick = useCallback(
    (thread: ChatThread) => {
      router.push(`/projects/${projectId}/chat?thread=${thread.id}`);
    },
    [projectId, router]
  );

  return (
    <div className="h-full flex flex-col items-center justify-center px-6 py-12">
      {/* Hero input */}
      <h2 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-4">
        What would you like to explore?
      </h2>
      <div className="w-full max-w-lg mb-10">
        <MessageInput
          variant="hero"
          placeholder="Ask a question about this project..."
          onSend={handleSend}
          disabled={isSending}
        />
      </div>

      {/* Recent threads */}
      {isThreadsLoading ? (
        <Spinner size="sm" className="text-neutral-400" />
      ) : threads && threads.length > 0 ? (
        <div className="w-full max-w-lg">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-2">
            Recent conversations
          </h3>
          <div className="space-y-1">
            {threads.slice(0, 8).map((thread: ChatThread) => (
              <button
                key={thread.id}
                onClick={() => handleThreadClick(thread)}
                className="w-full text-left px-3 py-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800/50 transition-colors group"
              >
                <p className="text-sm text-neutral-700 dark:text-neutral-300 truncate group-hover:text-neutral-900 dark:group-hover:text-neutral-100">
                  {thread.title || 'Untitled conversation'}
                </p>
                <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">
                  {formatRelativeTime(thread.updated_at)}
                </p>
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

// ─── Active Thread View ─────────────────────────────────────────

function ActiveThreadView({
  projectId,
  threadId,
  router,
  queryClient,
}: {
  projectId: string;
  threadId: string;
  router: ReturnType<typeof useRouter>;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  // Read initial message from sessionStorage (set by home hero input)
  const [initialMessage, setInitialMessage] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    const raw = sessionStorage.getItem('episteme_initial_message');
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      if (parsed.threadId === threadId) {
        sessionStorage.removeItem('episteme_initial_message');
        return parsed.content;
      }
      return null;
    } catch {
      sessionStorage.removeItem('episteme_initial_message');
      return raw;
    }
  });

  const { companion, thread } = useConversationState({ threadId });

  // Merge title update handler into companion stream callbacks
  const streamCallbacksWithTitle = useMemo(
    () => ({
      ...companion.streamCallbacks,
      onTitleUpdate: (title: string) => {
        queryClient.setQueryData(
          ['thread', threadId],
          (old: ChatThread | undefined) => (old ? { ...old, title } : old)
        );
        queryClient.invalidateQueries({ queryKey: ['project-threads', projectId] });
        queryClient.invalidateQueries({ queryKey: ['threads'] });
      },
    }),
    [companion.streamCallbacks, threadId, projectId, queryClient]
  );

  return (
    <div className="absolute inset-0 flex">
      {/* Main chat area */}
      <div className="flex-1 min-w-0 flex flex-col">
        <ChatPanel
          threadId={threadId}
          variant="full"
          streamCallbacks={streamCallbacksWithTitle}
          initialMessage={initialMessage || undefined}
          onInitialMessageSent={() => setInitialMessage(null)}
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
            status={companion.status}
            conversationStructure={companion.conversationStructure}
            episodeHistory={companion.episodeHistory}
            currentEpisode={companion.currentEpisode}
            rankedSections={companion.rankedSections}
            pinnedSection={companion.pinnedSection}
            onPinSection={companion.setPinnedSection}
            onDismissCompleted={companion.dismissCompleted}
            onTogglePosition={companion.toggleCompanion}
            onClose={() => companion.setCompanionPosition('hidden')}
          />
        </div>
      ) : (
        <Button
          variant="ghost"
          size="icon"
          onClick={companion.toggleCompanion}
          className="absolute top-3 right-3 z-30 w-8 h-8 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 shadow-sm hover:shadow-md text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 transition-all duration-200"
          aria-label="Open companion panel"
          title="Open companion panel"
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </Button>
      )}
    </div>
  );
}

// ─── Helpers ────────────────────────────────────────────────────

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMs / 3_600_000);
  const diffDays = Math.floor(diffMs / 86_400_000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
