/**
 * Home Context Zone
 *
 * Displays 1-3 contextual elements above the chat input:
 * - Continue card (if there's recent work to resume)
 * - Top action card (tensions, blind spots)
 * - Activity summary (what happened while you were away)
 *
 * This zone disappears once the user starts a conversation.
 */

'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import { EmptyContextZone } from './EmptyContextZone';
import type { ContinueState, IntelligenceItem, ActivityItem } from '@/lib/types/intelligence';

interface HomeContextZoneProps {
  continueState: ContinueState | null;
  topAction: IntelligenceItem | null;
  activity: ActivityItem[];
  className?: string;
}

export function HomeContextZone({
  continueState,
  topAction,
  activity,
  className,
}: HomeContextZoneProps) {
  const newActivityCount = activity.filter(a => a.isNew).length;
  const hasContent = continueState || (topAction && topAction.type !== 'continue') || newActivityCount > 0;

  if (!hasContent) {
    return <EmptyContextZone className={className} />;
  }

  // Calculate animation delays based on which cards are visible
  let animationIndex = 0;

  return (
    <div className={cn('max-w-2xl mx-auto px-6 py-4 space-y-3', className)}>
      {/* Continue card - first to animate */}
      {continueState && (
        <div
          className="animate-slide-up"
          style={{ animationDelay: `${animationIndex++ * 75}ms` }}
        >
          <ContinueCard state={continueState} />
        </div>
      )}

      {/* Top action (if different from continue) - second to animate */}
      {topAction && topAction.type !== 'continue' && (
        <div
          className="animate-slide-up"
          style={{ animationDelay: `${animationIndex++ * 75}ms` }}
        >
          <CompactActionCard action={topAction} />
        </div>
      )}

      {/* Activity summary - third to animate */}
      {newActivityCount > 0 && (
        <div
          className="animate-slide-up"
          style={{ animationDelay: `${animationIndex++ * 75}ms` }}
        >
          <ActivitySummary items={activity} />
        </div>
      )}
    </div>
  );
}

// Continue Card - shows where user left off
function ContinueCard({ state }: { state: ContinueState }) {
  const href = state.caseId
    ? `/workspace/cases/${state.caseId}`
    : state.projectId
      ? `/workspace/projects/${state.projectId}`
      : '/workspace';

  return (
    <Link
      href={href}
      className="block p-4 rounded-xl border border-accent-200 dark:border-accent-800 bg-accent-50/50 dark:bg-accent-900/20 hover:border-accent-300 dark:hover:border-accent-700 hover:bg-accent-50 dark:hover:bg-accent-900/30 transition-colors group"
    >
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-accent-100 dark:bg-accent-800 flex items-center justify-center text-accent-600 dark:text-accent-400 flex-shrink-0">
          <ArrowRightIcon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-accent-600 dark:text-accent-400 uppercase tracking-wide">
              Continue
            </span>
          </div>
          <h3 className="font-medium text-primary-900 dark:text-primary-50 truncate group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors">
            {state.title}
          </h3>
          {state.subtitle && (
            <p className="text-sm text-neutral-500 dark:text-neutral-400 truncate">
              {state.subtitle}
            </p>
          )}
        </div>
        <ChevronRightIcon className="w-5 h-5 text-neutral-400 dark:text-neutral-500 group-hover:text-accent-500 transition-colors" />
      </div>
    </Link>
  );
}

// Compact Action Card - for tensions, blind spots, etc.
function CompactActionCard({ action }: { action: IntelligenceItem }) {
  const href = action.caseId
    ? `/workspace/cases/${action.caseId}`
    : action.projectId
      ? `/workspace/projects/${action.projectId}`
      : '/workspace';

  const typeConfig = {
    tension: {
      icon: <AlertTriangleIcon className="w-4 h-4" />,
      label: 'Tension',
      colors: 'bg-warning-100 dark:bg-warning-900/30 text-warning-600 dark:text-warning-400',
      border: 'border-warning-200 dark:border-warning-800',
    },
    blind_spot: {
      icon: <EyeOffIcon className="w-4 h-4" />,
      label: 'Blind Spot',
      colors: 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400',
      border: 'border-accent-200 dark:border-accent-800',
    },
    explore: {
      icon: <CompassIcon className="w-4 h-4" />,
      label: 'Explore',
      colors: 'bg-info-100 dark:bg-info-900/30 text-info-600 dark:text-info-400',
      border: 'border-info-200 dark:border-info-800',
    },
    research_ready: {
      icon: <CheckCircleIcon className="w-4 h-4" />,
      label: 'Research Ready',
      colors: 'bg-success-100 dark:bg-success-900/30 text-success-600 dark:text-success-400',
      border: 'border-success-200 dark:border-success-800',
    },
    ready: {
      icon: <CheckCircleIcon className="w-4 h-4" />,
      label: 'Ready',
      colors: 'bg-success-100 dark:bg-success-900/30 text-success-600 dark:text-success-400',
      border: 'border-success-200 dark:border-success-800',
    },
    stale: {
      icon: <ClockIcon className="w-4 h-4" />,
      label: 'Needs Attention',
      colors: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400',
      border: 'border-neutral-200 dark:border-neutral-700',
    },
    continue: {
      icon: <ArrowRightIcon className="w-4 h-4" />,
      label: 'Continue',
      colors: 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400',
      border: 'border-accent-200 dark:border-accent-800',
    },
  };

  const config = typeConfig[action.type] || typeConfig.stale;

  return (
    <Link
      href={href}
      className={cn(
        'block p-4 rounded-xl border hover:shadow-sm transition-all group',
        config.border,
        'bg-white dark:bg-neutral-900 hover:bg-neutral-50 dark:hover:bg-neutral-800'
      )}
    >
      <div className="flex items-center gap-3">
        <div className={cn('w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0', config.colors)}>
          {config.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={cn('text-xs font-medium uppercase tracking-wide', config.colors.replace('bg-', 'text-').split(' ')[0])}>
              {config.label}
            </span>
            {action.caseTitle && (
              <span className="text-xs text-neutral-400 dark:text-neutral-500">
                {action.caseTitle}
              </span>
            )}
          </div>
          <h3 className="font-medium text-primary-900 dark:text-primary-50 truncate group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors">
            {action.title}
          </h3>
        </div>
        <ChevronRightIcon className="w-5 h-5 text-neutral-400 dark:text-neutral-500 group-hover:text-accent-500 transition-colors" />
      </div>
    </Link>
  );
}

// Activity Summary - compact "while you were away"
function ActivitySummary({ items }: { items: ActivityItem[] }) {
  const newItems = items.filter(a => a.isNew);
  if (newItems.length === 0) return null;

  const firstItem = newItems[0];

  return (
    <div className="p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900/50">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
          While You Were Away
        </span>
        <span className="text-xs font-medium text-accent-600 dark:text-accent-400">
          {newItems.length} new
        </span>
      </div>
      <p className="text-sm text-primary-900 dark:text-primary-100 truncate">
        {firstItem.title}: {firstItem.description}
      </p>
      {newItems.length > 1 && (
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
          +{newItems.length - 1} more update{newItems.length > 2 ? 's' : ''}
        </p>
      )}
    </div>
  );
}

// Icons
function ArrowRightIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}

function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

function AlertTriangleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01" />
    </svg>
  );
}

function EyeOffIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24M1 1l22 22" />
    </svg>
  );
}

function CompassIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  );
}

export default HomeContextZone;
