/**
 * Dashboard Overview - Main view when no project is selected
 * Shows cross-project intelligence and quick access
 */

'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Case, Inquiry } from '@/lib/types/case';
import type { ChatThread } from '@/lib/types/chat';
import { ResearchCompleteCard } from './intelligence/ResearchCompleteCard';
import { ConversationPromptCard } from './intelligence/ConversationPromptCard';
import { AttentionNeededCard } from './intelligence/AttentionNeededCard';
import { ConnectionCard } from './intelligence/ConnectionCard';

interface DashboardOverviewProps {
  recentCases: Case[];
  pendingInquiries: Inquiry[];
  recentThreads: ChatThread[];
}

export function DashboardOverview({
  recentCases,
  pendingInquiries,
  recentThreads,
}: DashboardOverviewProps) {
  const router = useRouter();

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Simple Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl tracking-tight font-bold text-primary-900 dark:text-primary-50">
          Workspace
        </h1>
        <Button onClick={() => router.push('/chat')}>
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          Start Chat
        </Button>
      </div>

      {/* Intelligence Feed */}
      <div>
        <h2 className="text-lg font-semibold text-primary-900 dark:text-primary-50 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Intelligence Feed
        </h2>
        <div className="space-y-3">
          <ResearchCompleteCard />
          <ConversationPromptCard />
          <AttentionNeededCard />
          <ConnectionCard />
        </div>
      </div>

      {/* Recent Activity (Single Column, Mixed) */}
      <div>
        <h2 className="text-lg font-semibold text-primary-900 dark:text-primary-50 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Recent Activity
        </h2>
        
        {recentCases.length === 0 && recentThreads.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12 text-neutral-500 dark:text-neutral-400">
              <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p className="mb-4">No activity yet. Start a conversation to get going.</p>
              <Button onClick={() => router.push('/chat')}>
                Start Your First Chat
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {[...recentCases, ...recentThreads]
              .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
              .slice(0, 8)
              .map((item) => {
                if ('status' in item) {
                  // Case
                  return (
                    <Link
                      key={item.id}
                      href={`/workspace/cases/${item.id}`}
                      className="block p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 hover:border-accent-500 dark:hover:border-accent-600 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <svg className="w-5 h-5 text-accent-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-sm text-primary-900 dark:text-primary-50 truncate">
                            {item.title}
                          </h4>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="success" className="text-xs">Case</Badge>
                            {item.confidence != null && (
                              <span className="text-xs text-neutral-600 dark:text-neutral-400">
                                {Math.round(item.confidence * 100)}% confidence
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </Link>
                  );
                } else {
                  // Thread
                  return (
                    <Link
                      key={item.id}
                      href={`/chat?thread=${item.id}`}
                      className="block p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 hover:border-accent-500 dark:hover:border-accent-600 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <svg className="w-5 h-5 text-accent-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-sm text-primary-900 dark:text-primary-50 truncate">
                            {item.title}
                          </h4>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="default" className="text-xs">Chat</Badge>
                            <span className="text-xs text-neutral-600 dark:text-neutral-400">
                              {item.message_count || 0} messages
                            </span>
                          </div>
                        </div>
                      </div>
                    </Link>
                  );
                }
              })}
          </div>
        )}
      </div>
    </div>
  );
}
