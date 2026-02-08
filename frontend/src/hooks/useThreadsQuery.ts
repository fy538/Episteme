/**
 * useThreadsQuery Hook
 *
 * React Query wrapper for chat thread listing.
 * Groups threads by date (Today / This Week / Older) for the conversations panel.
 */

import { useQuery } from '@tanstack/react-query';
import { chatAPI } from '@/lib/api/chat';
import type { ChatThread } from '@/lib/types/chat';

interface UseThreadsQueryOptions {
  /** Filter threads by search text */
  search?: string;
  /** Include archived threads */
  archived?: boolean;
  /** Enable/disable the query */
  enabled?: boolean;
}

export interface GroupedThreads {
  today: ChatThread[];
  thisWeek: ChatThread[];
  older: ChatThread[];
}

/** Group threads by date for display in the conversations panel */
function groupThreadsByDate(threads: ChatThread[]): GroupedThreads {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const weekStart = new Date(todayStart);
  weekStart.setDate(weekStart.getDate() - 6);

  const groups: GroupedThreads = { today: [], thisWeek: [], older: [] };

  for (const thread of threads) {
    const updated = new Date(thread.updated_at);
    if (updated >= todayStart) {
      groups.today.push(thread);
    } else if (updated >= weekStart) {
      groups.thisWeek.push(thread);
    } else {
      groups.older.push(thread);
    }
  }

  return groups;
}

/** Format a thread timestamp for compact display */
export function formatThreadTime(dateStr: string): string {
  const now = new Date();
  const then = new Date(dateStr);

  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterdayStart = new Date(todayStart);
  yesterdayStart.setDate(yesterdayStart.getDate() - 1);
  const weekStart = new Date(todayStart);
  weekStart.setDate(weekStart.getDate() - 6);

  if (then >= todayStart) {
    return then.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: false,
    });
  }
  if (then >= yesterdayStart) {
    return 'Yesterday';
  }
  if (then >= weekStart) {
    return then.toLocaleDateString('en-US', { weekday: 'short' });
  }
  return then.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });
}

export function useThreadsQuery(options?: UseThreadsQueryOptions) {
  return useQuery({
    queryKey: ['threads', options?.search ?? '', options?.archived ?? false],
    queryFn: () =>
      chatAPI.listThreads({
        q: options?.search || undefined,
        archived: options?.archived ? 'true' : 'false',
      }),
    enabled: options?.enabled !== false,
    staleTime: 30_000, // 30 seconds
    select: groupThreadsByDate,
  });
}

/** Flat thread list query (no grouping) — useful for search results */
export function useThreadsListQuery(options?: UseThreadsQueryOptions) {
  return useQuery({
    queryKey: ['threads-flat', options?.search ?? '', options?.archived ?? false],
    queryFn: () =>
      chatAPI.listThreads({
        q: options?.search || undefined,
        archived: options?.archived ? 'true' : 'false',
      }),
    enabled: options?.enabled !== false,
    staleTime: 30_000,
  });
}
