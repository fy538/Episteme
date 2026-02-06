/**
 * Home Component
 *
 * Chat-first home experience that combines:
 * - Collapsible sidebar for project/case navigation
 * - Context zone with actionable suggestions (disappears once conversation starts)
 * - Full chat interface
 *
 * This merges the previous dashboard and chat pages into one cohesive experience.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardSidebar } from './dashboard/DashboardSidebar';
import { HomeContextZone } from './dashboard/HomeContextZone';
import { ActionChips } from './dashboard/ActionChips';
import { WelcomeEmpty } from './dashboard/WelcomeEmpty';
import { ChatInterface, UnifiedStreamCallbacks } from '@/components/chat/ChatInterface';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { NetworkErrorBanner } from '@/components/ui/network-error-banner';
import { Spinner } from '@/components/ui/spinner';
import { chatAPI } from '@/lib/api/chat';
import { cn } from '@/lib/utils';
import type { Project } from '@/lib/types/project';
import type { Case, Inquiry } from '@/lib/types/case';
import type { ContinueState, IntelligenceItem, ActivityItem } from '@/lib/types/intelligence';
import type { ChatThread, InlineActionCard } from '@/lib/types/chat';
import type { Signal } from '@/lib/types/signal';

// Extended types for the project list
interface ProjectWithCases extends Project {
  cases: CaseWithInquiries[];
}

interface CaseWithInquiries extends Case {
  inquiries: Inquiry[];
  readinessScore: number;
  tensionsCount: number;
  blindSpotsCount: number;
}

interface HomeProps {
  projects: ProjectWithCases[];
  continueState: ContinueState | null;
  topAction: IntelligenceItem | null;
  activity: ActivityItem[];
  isLoading?: boolean;
  onCreateProject?: () => void;
  className?: string;
}

export function Home({
  projects,
  continueState,
  topAction,
  activity,
  isLoading: propsLoading = false,
  onCreateProject,
  className,
}: HomeProps) {
  const router = useRouter();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Thread and message state
  const [threadId, setThreadId] = useState<string | null>(null);
  const [hasMessages, setHasMessages] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [networkError, setNetworkError] = useState(false);

  // Companion state (for unified streaming)
  const [reflection, setReflection] = useState('');
  const [isReflectionStreaming, setIsReflectionStreaming] = useState(false);
  const [signals, setSignals] = useState<Signal[]>([]);

  // Initialize or load thread
  useEffect(() => {
    async function initThread() {
      try {
        setIsInitializing(true);

        // Try to get existing threads
        const threads = await chatAPI.listThreads({ archived: 'false' });

        if (threads.length > 0) {
          // Use the most recent thread
          const recentThread = threads[0];
          setThreadId(recentThread.id);

          // Check if it has messages
          const messages = await chatAPI.getMessages(recentThread.id);
          setHasMessages(messages.length > 0);
        } else {
          // Create a new thread
          const newThread = await chatAPI.createThread();
          setThreadId(newThread.id);
          setHasMessages(false);
        }
      } catch (err) {
        console.error('Failed to initialize thread:', err);
        setNetworkError(true);
      } finally {
        setIsInitializing(false);
      }
    }

    initThread();
  }, []);

  // Reset context visibility when thread changes
  useEffect(() => {
    async function checkMessages() {
      if (!threadId) return;

      try {
        const messages = await chatAPI.getMessages(threadId);
        setHasMessages(messages.length > 0);
      } catch (err) {
        console.error('Failed to check messages:', err);
      }
    }

    checkMessages();
  }, [threadId]);

  // Handle creating a new thread (new conversation)
  const handleNewThread = useCallback(async () => {
    try {
      const newThread = await chatAPI.createThread();
      setThreadId(newThread.id);
      setHasMessages(false);
      setReflection('');
      setSignals([]);
    } catch (err) {
      console.error('Failed to create thread:', err);
    }
  }, []);

  // Handle action chip clicks
  const handleChipClick = useCallback((action: string, data?: Record<string, unknown>) => {
    switch (action) {
      case 'continue':
        if (data?.caseId) {
          router.push(`/workspace/cases/${data.caseId}`);
        } else if (data?.projectId) {
          router.push(`/workspace/projects/${data.projectId}`);
        }
        break;
      case 'explore':
        // Pre-fill chat with exploration prompt
        // For now, just focus the input
        break;
      case 'new_case':
        if (projects.length > 0) {
          router.push(`/workspace/projects/${projects[0].id}?action=new-case`);
        } else if (onCreateProject) {
          onCreateProject();
        }
        break;
      case 'research':
        router.push('/chat?mode=research');
        break;
    }
  }, [router, projects, onCreateProject]);

  // Handle create project
  const handleCreateProject = useCallback(() => {
    if (onCreateProject) {
      onCreateProject();
    } else {
      router.push('/workspace/projects/new');
    }
  }, [onCreateProject, router]);

  // Unified stream callbacks
  const unifiedStreamCallbacks: UnifiedStreamCallbacks = {
    onReflectionChunk: useCallback((delta: string) => {
      setIsReflectionStreaming(true);
      setReflection(prev => prev + delta);
    }, []),
    onReflectionComplete: useCallback((content: string) => {
      setReflection(content);
      setIsReflectionStreaming(false);
    }, []),
    onSignals: useCallback((newSignals: Signal[]) => {
      setSignals(prev => {
        const existingIds = new Set(prev.map(s => s.id));
        const unique = newSignals.filter(s => !existingIds.has(s.id));
        return [...prev, ...unique];
      });
    }, []),
    onMessageComplete: useCallback(() => {
      // Mark that we now have messages (hide context zone)
      setHasMessages(true);
    }, []),
  };

  // Loading state
  if (propsLoading || isInitializing) {
    return (
      <div className="flex h-screen items-center justify-center bg-neutral-50 dark:bg-neutral-950">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  // Show context zone when there are no messages
  const showContextZone = !hasMessages;
  const hasNoProjects = projects.length === 0;

  return (
    <ErrorBoundary>
      <div className={cn('flex h-screen bg-neutral-50 dark:bg-neutral-950', className)}>
        {/* Sidebar - project/case navigation */}
        <DashboardSidebar
          projects={projects}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          onCreateProject={handleCreateProject}
        />

        {/* Main content - chat-first experience */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <NetworkErrorBanner
            isVisible={networkError}
            onRetry={() => {
              setNetworkError(false);
              window.location.reload();
            }}
          />

          {/* Content wrapper */}
          <div className="flex-1 flex flex-col min-h-0">
            {/* Context zone - animates out when conversation starts */}
            <div className={cn(
              'flex-shrink-0 transition-all duration-300 ease-out',
              showContextZone
                ? 'opacity-100 translate-y-0 pt-12'
                : 'opacity-0 -translate-y-4 h-0 overflow-hidden pointer-events-none'
            )}>
              {hasNoProjects ? (
                /* Welcome state for new users */
                <WelcomeEmpty onCreateProject={handleCreateProject} />
              ) : (
                <>
                  {/* Greeting */}
                  <div className="text-center mb-6">
                    <h1 className="text-2xl font-bold text-primary-900 dark:text-primary-50 mb-2 animate-fade-in">
                      What would you like to work on?
                    </h1>
                    <p className="text-neutral-500 dark:text-neutral-400 animate-fade-in" style={{ animationDelay: '100ms' }}>
                      Start a conversation or pick up where you left off
                    </p>
                  </div>

                  {/* Context cards */}
                  <HomeContextZone
                    continueState={continueState}
                    topAction={topAction}
                    activity={activity}
                  />
                </>
              )}
            </div>

            {/* Chat interface */}
            <div className={cn(
              'flex-1 flex flex-col min-h-0',
              showContextZone ? 'max-w-2xl mx-auto w-full' : ''
            )}>
              {threadId && (
                <ChatInterface
                  threadId={threadId}
                  onToggleLeft={() => setSidebarCollapsed(!sidebarCollapsed)}
                  leftCollapsed={sidebarCollapsed}
                  rightCollapsed={true}
                  unifiedStreamCallbacks={unifiedStreamCallbacks}
                />
              )}
            </div>

            {/* Action chips - animates out with context zone */}
            <div className={cn(
              'flex-shrink-0 transition-all duration-300 ease-out',
              showContextZone
                ? 'opacity-100 translate-y-0 pb-4'
                : 'opacity-0 translate-y-4 h-0 overflow-hidden pointer-events-none'
            )}>
              <ActionChips
                continueState={continueState}
                hasProjects={!hasNoProjects}
                onChipClick={handleChipClick}
              />
            </div>
          </div>
        </main>
      </div>
    </ErrorBoundary>
  );
}

export default Home;
