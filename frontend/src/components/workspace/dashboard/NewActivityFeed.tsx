/**
 * New Activity Feed
 *
 * Shows "while you were away" items - things that happened
 * since the user's last visit.
 */

'use client';

import Link from 'next/link';
import { EmptyState } from '@/components/ui/empty-state';
import { cn } from '@/lib/utils';
import type { ActivityItem } from '@/lib/types/intelligence';

interface NewActivityFeedProps {
  items: ActivityItem[];
  maxItems?: number;
  showSeeAll?: boolean;
  className?: string;
}

export function NewActivityFeed({
  items,
  maxItems = 5,
  showSeeAll = true,
  className,
}: NewActivityFeedProps) {
  const displayItems = items.slice(0, maxItems);
  const hasMore = items.length > maxItems;
  const newCount = items.filter(i => i.isNew).length;

  if (items.length === 0) {
    return (
      <div className={className}>
        <EmptyState
          title="No recent activity"
          description="Activity will appear here as you work on your cases"
          compact
        />
      </div>
    );
  }

  return (
    <div className={cn('space-y-1', className)}>
      {displayItems.map((item) => (
        <ActivityItemRow key={item.id} item={item} />
      ))}

      {hasMore && showSeeAll && (
        <button className="text-sm text-accent-600 dark:text-accent-400 hover:underline pt-2">
          See all activity ({items.length})
        </button>
      )}
    </div>
  );
}

function ActivityItemRow({ item }: { item: ActivityItem }) {
  const styles = getActivityStyles(item.type);
  const Icon = styles.icon;

  // Build link
  const href = item.caseId
    ? `/cases/${item.caseId}`
    : item.projectId
    ? `/projects/${item.projectId}`
    : '/';

  // Format timestamp
  const timeAgo = formatTimeAgo(item.timestamp);

  return (
    <Link
      href={href}
      className={cn(
        'flex items-start gap-3 p-3 rounded-lg transition-colors',
        'hover:bg-neutral-50 dark:hover:bg-neutral-800/50',
        item.isNew && 'bg-accent-50/50 dark:bg-accent-900/10'
      )}
    >
      {/* Icon */}
      <div className={cn('p-1.5 rounded-md shrink-0 mt-0.5', styles.iconBg)}>
        <Icon className={cn('w-3.5 h-3.5', styles.iconColor)} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-medium text-primary-900 dark:text-primary-50">
              {item.title}
            </p>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 truncate">
              {item.description}
            </p>
            {(item.caseTitle || item.projectTitle) && (
              <p className="text-xs text-neutral-500 dark:text-neutral-500 mt-0.5">
                {[item.projectTitle, item.caseTitle].filter(Boolean).join(' · ')}
              </p>
            )}
          </div>

          {/* Time */}
          <span className="text-xs text-neutral-400 dark:text-neutral-500 shrink-0">
            {timeAgo}
          </span>
        </div>
      </div>

      {/* New indicator */}
      {item.isNew && (
        <div className="w-2 h-2 rounded-full bg-accent-500 shrink-0 mt-2" />
      )}
    </Link>
  );
}

function getActivityStyles(type: ActivityItem['type']) {
  switch (type) {
    case 'research_complete':
      return {
        icon: ResearchIcon,
        iconBg: 'bg-success-100 dark:bg-success-900/30',
        iconColor: 'text-success-600 dark:text-success-400',
      };
    case 'blind_spot_surfaced':
      return {
        icon: BlindSpotIcon,
        iconBg: 'bg-accent-100 dark:bg-accent-900/30',
        iconColor: 'text-accent-600 dark:text-accent-400',
      };
    case 'tension_detected':
      return {
        icon: TensionIcon,
        iconBg: 'bg-warning-100 dark:bg-warning-900/30',
        iconColor: 'text-warning-600 dark:text-warning-400',
      };
    case 'inquiry_resolved':
      return {
        icon: CheckIcon,
        iconBg: 'bg-success-100 dark:bg-success-900/30',
        iconColor: 'text-success-600 dark:text-success-400',
      };
    case 'case_ready':
      return {
        icon: ReadyIcon,
        iconBg: 'bg-success-100 dark:bg-success-900/30',
        iconColor: 'text-success-600 dark:text-success-400',
      };
    case 'document_uploaded':
      return {
        icon: DocumentIcon,
        iconBg: 'bg-neutral-100 dark:bg-neutral-800',
        iconColor: 'text-neutral-600 dark:text-neutral-400',
      };
    default:
      return {
        icon: DefaultIcon,
        iconBg: 'bg-neutral-100 dark:bg-neutral-800',
        iconColor: 'text-neutral-600 dark:text-neutral-400',
      };
  }
}

function formatTimeAgo(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;

  return then.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Icons
function ResearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M9 2H5a1.5 1.5 0 00-1.5 1.5v9A1.5 1.5 0 005 14h6a1.5 1.5 0 001.5-1.5V5.5L9 2z" />
      <path d="M9 2v4h4" strokeLinecap="round" />
    </svg>
  );
}

function BlindSpotIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5.5v3M8 10.5v.5" strokeLinecap="round" />
    </svg>
  );
}

function TensionIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M8 6v3M8 11h.01" strokeLinecap="round" />
      <path d="M7 2.5L2 12a1 1 0 00.87 1.5h10.26a1 1 0 00.87-1.5L9 2.5a1 1 0 00-1.74 0z" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M13.5 4.5l-7 7L3 8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ReadyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="6" />
      <path d="M5.5 8l2 2 3.5-3.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DocumentIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M9 2H5a1.5 1.5 0 00-1.5 1.5v9A1.5 1.5 0 005 14h6a1.5 1.5 0 001.5-1.5V5.5L9 2z" />
      <path d="M9 2v4h4" strokeLinecap="round" />
    </svg>
  );
}

function DefaultIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="6" />
    </svg>
  );
}

export default NewActivityFeed;
