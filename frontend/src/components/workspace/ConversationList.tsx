/**
 * Conversation List Component
 * Shows all chat threads grouped by linked/standalone
 */

'use client';

import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { ChatThread } from '@/lib/types/chat';
import type { Case } from '@/lib/types/case';

interface ConversationListProps {
  threads: ChatThread[];
  cases: Case[];
  onStartChat?: () => void;
}

export function ConversationList({
  threads,
  cases,
  onStartChat,
}: ConversationListProps) {
  const linkedThreads = threads.filter(t => t.primary_case);
  const standaloneThreads = threads.filter(t => !t.primary_case);

  const getCaseName = (caseId: string) => {
    const foundCase = cases.find(c => c.id === caseId);
    return foundCase?.title || 'Unknown Case';
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const renderThreadCard = (thread: ChatThread) => (
    <Card key={thread.id} className="hover:border-accent-500 dark:hover:border-accent-600 transition-colors">
      <CardContent className="pt-4">
        <div className="space-y-2">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <Link href={`/chat?thread=${thread.id}`}>
                <h4 className="font-medium text-sm text-primary-900 dark:text-primary-50 hover:text-accent-600 transition-colors">
                  {thread.title}
                </h4>
              </Link>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-neutral-600 dark:text-neutral-400">
                  {thread.message_count || 0} messages
                </span>
                <span className="text-xs text-neutral-500 dark:text-neutral-500">•</span>
                <span className="text-xs text-neutral-600 dark:text-neutral-400">
                  {formatDate(thread.updated_at)}
                </span>
              </div>
            </div>
          </div>

          {thread.primary_case && (
            <div className="text-xs">
              <Link 
                href={`/workspace/cases/${thread.primary_case}`}
                className="text-accent-600 hover:text-accent-700 hover:underline"
              >
                {getCaseName(thread.primary_case)}
              </Link>
            </div>
          )}

          {thread.latest_message && (
            <p className="text-xs text-neutral-600 dark:text-neutral-400 line-clamp-2 mt-2">
              {thread.latest_message.content}
            </p>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-2 border-t border-neutral-200 dark:border-neutral-700">
            <Link href={`/chat?thread=${thread.id}`}>
              <Button size="sm" variant="default">
                Continue
              </Button>
            </Link>
            {!thread.primary_case && (
              <Button size="sm" variant="outline">
                Link to Case
              </Button>
            )}
            <Button size="sm" variant="outline">
              Convert to Case
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-primary-900 dark:text-primary-50">
            Project Chats ({threads.length})
          </h3>
          {onStartChat && (
            <Button onClick={onStartChat}>
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Start Chat
            </Button>
          )}
        </div>
        <p className="text-xs text-neutral-600 dark:text-neutral-400">
          Conversations linked to this project. For quick exploration,{' '}
          <Link href="/chat" className="text-accent-600 hover:text-accent-700 hover:underline">
            use Chat →
          </Link>
        </p>
      </div>

      {threads.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12 text-neutral-500 dark:text-neutral-400">
            <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="mb-2">No project conversations yet.</p>
            <p className="text-xs text-neutral-400 mb-4">
              Want to explore freely?{' '}
              <Link href="/chat" className="text-accent-600 hover:text-accent-700 hover:underline">
                Try Chat →
              </Link>
            </p>
            {onStartChat && (
              <Button onClick={onStartChat}>
                Start First Conversation
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Linked to Cases */}
          {linkedThreads.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-primary-700 dark:text-primary-400 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
                Linked to Cases ({linkedThreads.length})
              </h4>
              <div className="space-y-2">
                {linkedThreads.map(renderThreadCard)}
              </div>
            </div>
          )}

          {/* Standalone */}
          {standaloneThreads.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-neutral-700 dark:text-neutral-400 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                Standalone ({standaloneThreads.length})
              </h4>
              <div className="space-y-2">
                {standaloneThreads.map(renderThreadCard)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
