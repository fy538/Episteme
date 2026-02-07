/**
 * Home Component
 *
 * Personalized stacked flow home experience:
 * - Welcome slogan (personalized greeting + stats)
 * - Centered hero input with typewriter placeholder
 * - Action item card (priority next step with context)
 * - 3-column insight grid (articles + prompt placeholders)
 * - Structured timeline (day groups, parent-child nesting)
 * - Sidebar for project/case navigation
 *
 * When user sends a message, home content fades out and full chat takes over.
 *
 * State management extracted to useHomeState hook.
 */

'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DashboardSidebar } from './dashboard/DashboardSidebar';
import { ActionItemCard } from './dashboard/ActionItemCard';
import { ArticleCarousel } from './dashboard/ArticleCarousel';
import { ActivityTimeline } from './dashboard/ActivityTimeline';
import { WelcomeEmpty } from './dashboard/WelcomeEmpty';
import { ChatPanel } from '@/components/workspace/ChatPanel';
import { CompanionPanel } from '@/components/companion';
import { MessageInput } from '@/components/chat/MessageInput';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { NetworkErrorBanner } from '@/components/ui/network-error-banner';
import { Spinner } from '@/components/ui/spinner';
import { Button } from '@/components/ui/button';
import { useHomeState } from '@/hooks/useHomeState';
import { useTodaysBrief } from '@/hooks/useTodaysBrief';
import { eventsAPI } from '@/lib/api/events';
import { buildTimelineTree, generatePlaceholderTree } from '@/lib/utils/timeline-mapper';
import { cn } from '@/lib/utils';
import type { ProjectWithCases, CaseWithInquiries } from '@/hooks/useProjectsQuery';

interface HomeProps {
  projects: ProjectWithCases[];
  isLoading?: boolean;
  onCreateProject?: () => void;
  className?: string;
}

export function Home({
  projects,
  isLoading: propsLoading = false,
  onCreateProject,
  className,
}: HomeProps) {
  const state = useHomeState();
  const brief = useTodaysBrief(projects);

  // Fetch recent events for timeline (only when we have cases)
  const { data: rawEvents = [] } = useQuery({
    queryKey: ['recent-events'],
    queryFn: () => eventsAPI.getRecent(20),
    enabled: !brief.isEmpty,
  });
  const timelineClusters = useMemo(() => {
    const tree = buildTimelineTree(rawEvents);
    // Use placeholder data when no real events exist (for UI development)
    return tree.length > 0 ? tree : generatePlaceholderTree();
  }, [rawEvents]);

  // Handle create project
  const handleCreateProject = () => {
    onCreateProject?.();
  };

  // Loading state
  if (propsLoading || state.isInitializing) {
    return (
      <div className="flex h-screen items-center justify-center bg-neutral-50 dark:bg-neutral-950">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className={cn('flex h-screen bg-white dark:bg-neutral-950', className)}>
        {/* Sidebar — project/case navigation */}
        <DashboardSidebar
          projects={projects}
          isCollapsed={state.sidebarCollapsed}
          onToggleCollapse={() => state.setSidebarCollapsed(!state.sidebarCollapsed)}
          onCreateProject={handleCreateProject}
        />

        {/* Main content */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <NetworkErrorBanner
            isVisible={state.networkError}
            onRetry={() => {
              state.setNetworkError(false);
              window.location.reload();
            }}
          />

          {/* STATE A: Home view — personalized stacked flow */}
          {!state.hasMessages && (
            <div
              className={cn(
                'flex-1 flex flex-col items-center px-6 overflow-y-auto transition-all duration-200 ease-out',
                state.isTransitioning ? 'opacity-0 scale-[0.98] blur-[2px]' : 'opacity-100 scale-100'
              )}
            >
              {/* Top spacer — generous breathing room above greeting */}
              <div className="min-h-[28vh] shrink-0" />

              <div className="w-full max-w-2xl">
                {brief.isEmpty ? (
                  /* New user — generic greeting + WelcomeEmpty */
                  <div className="flex flex-col items-center space-y-6 w-full">
                    <WelcomeEmpty onCreateProject={handleCreateProject} />
                    <div className="w-full rounded-lg border border-neutral-200/60 dark:border-neutral-700/50 overflow-hidden">
                      <MessageInput
                        variant="hero"
                        onSend={state.handleHeroSend}
                        placeholder={state.currentPlaceholder}
                      />
                    </div>
                  </div>
                ) : (
                  /* Returning user — personalized layout */
                  <div className="w-full space-y-5">
                    {/* Welcome slogan */}
                    <div className="text-center animate-fade-in">
                      <h1 className="text-3xl font-display font-semibold text-primary-900 dark:text-primary-50 tracking-tight">
                        {brief.welcomeSlogan}
                      </h1>
                      <p className="text-base text-neutral-500 dark:text-neutral-400 mt-2">
                        {brief.welcomeSubtitle}
                      </p>
                    </div>

                    {/* Hero input — single border, no inner chrome */}
                    <div
                      className="rounded-lg border border-neutral-200/60 dark:border-neutral-700/50 overflow-hidden animate-fade-in"
                      style={{ animationDelay: '60ms' }}
                    >
                      <MessageInput
                        variant="hero"
                        onSend={state.handleHeroSend}
                        placeholder={state.currentPlaceholder}
                      />
                    </div>

                    {/* Action item */}
                    {brief.actionItem && (
                      <div className="animate-fade-in" style={{ animationDelay: '120ms' }}>
                        <ActionItemCard item={brief.actionItem} />
                      </div>
                    )}

                    {/* Insight cards grid (articles + prompt placeholders) */}
                    <div className="animate-fade-in" style={{ animationDelay: '180ms' }}>
                      <ArticleCarousel
                        articles={brief.articles}
                        onPromptClick={state.handleHeroSend}
                      />
                    </div>

                    {/* Activity timeline (event-sourced, connected tree) */}
                    {timelineClusters.length > 0 && (
                      <div className="animate-fade-in" style={{ animationDelay: '240ms' }}>
                        <ActivityTimeline clusters={timelineClusters} />
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Bottom spacer */}
              <div className="min-h-[12vh] shrink-0" />
            </div>
          )}

          {/* STATE B: Chat view — full ChatPanel with companion sidebar */}
          {state.hasMessages && state.threadId && (
            <div className={cn(
              'flex-1 flex min-h-0 animate-fade-in transition-all duration-200 ease-out',
              state.isTransitioning ? 'opacity-0 scale-[0.98] blur-[2px]' : 'opacity-100 scale-100'
            )}>
              {/* Chat: fills remaining width */}
              <div className="flex-1 flex flex-col min-h-0 relative">
                {/* New conversation button */}
                <div className="absolute top-3 right-4 z-10">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={state.handleNewThread}
                    className="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
                  >
                    <PlusIcon className="w-4 h-4 mr-1.5" />
                    New Chat
                  </Button>
                </div>

                <ChatPanel
                  threadId={state.threadId}
                  variant="full"
                  streamCallbacks={state.streamCallbacks}
                  initialMessage={state.pendingMessage || undefined}
                  onInitialMessageSent={() => state.setPendingMessage(null)}
                />
              </div>

              {/* Companion: right sidebar */}
              {state.companionPosition === 'sidebar' && (
                <div className="w-80 border-l border-neutral-200 dark:border-neutral-800 flex flex-col h-full overflow-hidden shrink-0">
                  <CompanionPanel
                    thinking={state.companionThinking}
                    mode="casual"
                    position="sidebar"
                    actionHints={state.actionHints}
                    signals={state.signals}
                    rankedSections={state.rankedSections}
                    pinnedSection={state.pinnedSection}
                    onPinSection={state.setPinnedSection}
                    onTogglePosition={state.toggleCompanion}
                    onClose={() => state.setCompanionPosition('hidden')}
                  />
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </ErrorBoundary>
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

export default Home;
