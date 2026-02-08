/**
 * ConversationsPanelContent
 *
 * Sidebar panel content when Conversations is the active rail section.
 * Shows thread history grouped by date, with search and "New Chat" button.
 */

'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useThreadsQuery, formatThreadTime } from '@/hooks/useThreadsQuery';
import { chatAPI } from '@/lib/api/chat';
import { cn } from '@/lib/utils';
import type { ChatThread } from '@/lib/types/chat';

interface ConversationsPanelContentProps {
  activeThreadId?: string;
}

export function ConversationsPanelContent({ activeThreadId }: ConversationsPanelContentProps) {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const { data: grouped, isLoading } = useThreadsQuery({
    search: search || undefined,
  });

  const handleNewChat = useCallback(async () => {
    try {
      setIsCreating(true);
      const thread = await chatAPI.createThread();
      router.push(`/chat/${thread.id}`);
    } catch (err) {
      console.error('Failed to create thread:', err);
    } finally {
      setIsCreating(false);
    }
  }, [router]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-neutral-200 dark:border-neutral-800 space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            Conversations
          </h2>
          <button
            onClick={handleNewChat}
            disabled={isCreating}
            className={cn(
              'flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium',
              'bg-accent-50 text-accent-700 dark:bg-accent-900/30 dark:text-accent-300',
              'hover:bg-accent-100 dark:hover:bg-accent-900/50',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-colors duration-150'
            )}
          >
            <PlusIcon className="w-3.5 h-3.5" />
            New
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <SearchSmallIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search conversations..."
            className={cn(
              'w-full pl-8 pr-3 py-1.5 text-xs rounded-md',
              'bg-neutral-100 dark:bg-neutral-800',
              'text-neutral-900 dark:text-neutral-100',
              'placeholder:text-neutral-400 dark:placeholder:text-neutral-500',
              'border border-transparent',
              'focus:border-accent-300 dark:focus:border-accent-700 focus:outline-none',
              'transition-colors duration-150'
            )}
          />
        </div>
      </div>

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-4 h-4 border-2 border-accent-300 border-t-accent-600 rounded-full animate-spin" />
          </div>
        ) : !grouped || (grouped.today.length === 0 && grouped.thisWeek.length === 0 && grouped.older.length === 0) ? (
          <div className="text-center py-8 px-4">
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              {search ? 'No conversations found' : 'No conversations yet'}
            </p>
            {!search && (
              <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
                Start one from the Home page
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {grouped.today.length > 0 && (
              <ThreadGroup label="Today" threads={grouped.today} activeThreadId={activeThreadId} />
            )}
            {grouped.thisWeek.length > 0 && (
              <ThreadGroup label="This Week" threads={grouped.thisWeek} activeThreadId={activeThreadId} />
            )}
            {grouped.older.length > 0 && (
              <ThreadGroup label="Older" threads={grouped.older} activeThreadId={activeThreadId} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ThreadGroup({
  label,
  threads,
  activeThreadId,
}: {
  label: string;
  threads: ChatThread[];
  activeThreadId?: string;
}) {
  return (
    <div>
      <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1 px-2">
        {label}
      </h3>
      <div className="space-y-0.5">
        {threads.map((thread) => (
          <ThreadItem
            key={thread.id}
            thread={thread}
            isActive={thread.id === activeThreadId}
          />
        ))}
      </div>
    </div>
  );
}

function ThreadItem({ thread, isActive }: { thread: ChatThread; isActive: boolean }) {
  const title = thread.title || thread.latest_message?.content?.slice(0, 50) || 'New conversation';
  const hasCase = !!thread.primary_case;

  return (
    <Link
      href={`/chat/${thread.id}`}
      className={cn(
        'flex flex-col gap-0.5 px-2 py-1.5 rounded-md',
        'transition-colors duration-150',
        isActive
          ? 'bg-accent-50 dark:bg-accent-900/30 text-accent-700 dark:text-accent-300'
          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800'
      )}
    >
      <div className="flex items-center gap-1.5">
        {hasCase && (
          <span className="w-1.5 h-1.5 rounded-full bg-accent-400 shrink-0" />
        )}
        <span className="text-sm truncate flex-1">{title}</span>
      </div>
      <div className="flex items-center gap-2 text-xs text-neutral-400 dark:text-neutral-500">
        <span>{formatThreadTime(thread.updated_at)}</span>
        {thread.message_count != null && thread.message_count > 0 && (
          <span>{thread.message_count} msgs</span>
        )}
      </div>
    </Link>
  );
}

// --- Icons ---

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SearchSmallIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" strokeLinecap="round" />
    </svg>
  );
}
