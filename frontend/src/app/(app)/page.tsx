/**
 * Home Page
 *
 * Route: /
 * The app entry point. Supports two views, toggleable via [Home | Brief]:
 *
 *   - Home (default): Centered hero input + recent decision + suggested actions.
 *   - Brief: Action-oriented dashboard with active decisions, action queue,
 *            activity timeline, recent threads, and discover feed.
 *
 * View preference is persisted in localStorage.
 * The sidebar shows the Decisions tab for quick navigation.
 */

'use client';

import { useState, useEffect } from 'react';
import { MessageInput } from '@/components/chat/MessageInput';
import { RecentDecisionCard } from '@/components/home/RecentDecisionCard';
import { SuggestedActions } from '@/components/home/SuggestedActions';
import { BriefDashboard } from '@/components/home/BriefDashboard';
import { HomeViewToggle, type HomeViewMode } from '@/components/home/HomeViewToggle';
import { useHomeState } from '@/hooks/useHomeState';
import { useHomeDashboard } from '@/hooks/useHomeDashboard';
import { cn } from '@/lib/utils';

const VIEW_STORAGE_KEY = 'episteme_home_view_mode';

export default function HomePage() {
  const homeState = useHomeState();
  const { recentDecision, actionItems, isLoading } = useHomeDashboard();
  const [userName, setUserName] = useState('');
  const [viewMode, setViewMode] = useState<HomeViewMode>('home');

  useEffect(() => {
    const name = localStorage.getItem('episteme_user_name') || '';
    if (name) {
      setUserName(name.split(/\s+/)[0]); // first name only
    }
    // Restore view mode preference
    const stored = localStorage.getItem(VIEW_STORAGE_KEY) as HomeViewMode | null;
    if (stored === 'home' || stored === 'brief') {
      setViewMode(stored);
    }
  }, []);

  const handleViewModeChange = (mode: HomeViewMode) => {
    setViewMode(mode);
    localStorage.setItem(VIEW_STORAGE_KEY, mode);
  };

  const hasDecisions = recentDecision !== null;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-neutral-950 overflow-y-auto">
      <div
        className={cn(
          'flex-1 flex flex-col items-center px-6 transition-all duration-200 ease-out',
          viewMode === 'home' ? 'pt-[18vh]' : 'pt-8',
          homeState.isTransitioning ? 'opacity-0 scale-[0.98] blur-[2px]' : 'opacity-100 scale-100'
        )}
      >
        {/* ─── Header: Greeting + Toggle ─── */}
        <div className={cn(
          'w-full flex items-start justify-between mb-5',
          viewMode === 'home' ? 'max-w-2xl' : 'max-w-4xl'
        )}>
          <div>
            <h1 className={cn(
              'font-semibold text-neutral-900 dark:text-neutral-100 tracking-tight',
              viewMode === 'home' ? 'text-2xl' : 'text-xl'
            )}>
              {viewMode === 'brief'
                ? (userName ? `Your brief, ${userName}` : 'Your brief')
                : (userName ? `Welcome back, ${userName}` : 'What would you like to explore?')
              }
            </h1>
            {viewMode === 'home' && (
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                {hasDecisions
                  ? 'Continue a decision, or start something new.'
                  : 'Start a conversation to explore a decision.'}
              </p>
            )}
          </div>
          <HomeViewToggle viewMode={viewMode} onViewModeChange={handleViewModeChange} />
        </div>

        {/* ─── Content: Home or Brief ─── */}
        {viewMode === 'home' ? (
          <div className="w-full max-w-2xl space-y-5">
            {/* Hero input */}
            <div className="rounded-lg border border-neutral-200/60 dark:border-neutral-700/50 overflow-hidden">
              <MessageInput
                variant="hero"
                onSend={homeState.handleHeroSend}
                placeholder={homeState.currentPlaceholder}
              />
            </div>

            {/* Row 1: Most recent decision */}
            {!isLoading && recentDecision && (
              <RecentDecisionCard decision={recentDecision} />
            )}

            {/* Row 2: Suggested actions */}
            {!isLoading && actionItems.length > 0 && (
              <SuggestedActions items={actionItems} />
            )}
          </div>
        ) : (
          <BriefDashboard />
        )}
      </div>
    </div>
  );
}
