/**
 * Activity Timeline — Connected Tree
 *
 * Structured chronological event tree with:
 * - Day group headers (Today, Yesterday, This week, Earlier)
 * - Vertical rail with colored parent dots
 * - Branch connectors (├─ / └─) for child events
 * - Case title context on parent rows
 * - Bottom fade mask for graceful truncation
 *
 * Accepts TimelineCluster[] from buildTimelineTree() or
 * generatePlaceholderTree().
 */

'use client';

import Link from 'next/link';
import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import type { TimelineCluster, TimelineEntry, TimelineIcon, TimelineAccent } from '@/lib/utils/timeline-mapper';

interface ActivityTimelineProps {
  clusters: TimelineCluster[];
  className?: string;
}

// --- Day grouping ---

type DayBucket = 'Today' | 'Yesterday' | 'This week' | 'Earlier';

function getDayBucket(timestamp: string): DayBucket {
  const now = new Date();
  const then = new Date(timestamp);

  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterdayStart = new Date(todayStart);
  yesterdayStart.setDate(yesterdayStart.getDate() - 1);
  const weekStart = new Date(todayStart);
  weekStart.setDate(weekStart.getDate() - 6);

  if (then >= todayStart) return 'Today';
  if (then >= yesterdayStart) return 'Yesterday';
  if (then >= weekStart) return 'This week';
  return 'Earlier';
}

interface DayGroup {
  label: DayBucket;
  clusters: TimelineCluster[];
}

function groupByDay(clusters: TimelineCluster[]): DayGroup[] {
  const bucketOrder: DayBucket[] = ['Today', 'Yesterday', 'This week', 'Earlier'];
  const map = new Map<DayBucket, TimelineCluster[]>();

  for (const cluster of clusters) {
    const bucket = getDayBucket(cluster.timestamp);
    if (!map.has(bucket)) map.set(bucket, []);
    map.get(bucket)!.push(cluster);
  }

  return bucketOrder
    .filter(b => map.has(b))
    .map(b => ({ label: b, clusters: map.get(b)! }));
}

// --- Component ---

export function ActivityTimeline({ clusters, className }: ActivityTimelineProps) {
  const dayGroups = useMemo(() => groupByDay(clusters), [clusters]);

  if (clusters.length === 0) return null;

  return (
    <div className={cn('relative', className)}>
      <div className="space-y-4">
        {dayGroups.map((group) => (
          <DayGroupSection key={group.label} group={group} />
        ))}
      </div>
    </div>
  );
}

function DayGroupSection({ group }: { group: DayGroup }) {
  return (
    <div>
      {/* Day label */}
      <p className="text-[11px] font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-2">
        {group.label}
      </p>

      {/* Clusters within this day */}
      <div className="space-y-1">
        {group.clusters.map((cluster, clusterIdx) => (
          <ClusterNode
            key={cluster.id}
            cluster={cluster}
            isLast={clusterIdx === group.clusters.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

function ClusterNode({ cluster, isLast }: { cluster: TimelineCluster; isLast: boolean }) {
  const hasChildren = cluster.children.length > 0;

  return (
    <div className="relative">
      {/* Vertical rail — runs full height of cluster, stops if last in group */}
      {!isLast && (
        <div
          className="absolute left-[7px] top-[18px] bottom-0 w-px bg-neutral-200 dark:bg-neutral-700/60"
        />
      )}
      {/* Rail segment through children */}
      {hasChildren && (
        <div
          className="absolute left-[7px] top-[18px] w-px bg-neutral-200 dark:bg-neutral-700/60"
          style={{ height: `calc(100% - 18px)` }}
        />
      )}

      {/* Parent row */}
      <ParentRow
        entry={cluster.parentEntry}
        caseTitle={cluster.caseTitle}
        caseId={cluster.caseId}
      />

      {/* Children */}
      {hasChildren && (
        <div className="mt-px">
          {cluster.children.map((child, childIdx) => (
            <ChildRow
              key={child.id}
              entry={child}
              isLast={childIdx === cluster.children.length - 1}
              caseId={cluster.caseId}
            />
          ))}
        </div>
      )}

      {/* Spacing between clusters */}
      {!isLast && <div className="h-1" />}
    </div>
  );
}

function ParentRow({
  entry,
  caseTitle,
  caseId,
}: {
  entry: TimelineEntry;
  caseTitle: string | null;
  caseId: string | null;
}) {
  const content = (
    <div className="flex items-center gap-2 py-1 group/row hover:bg-neutral-50 dark:hover:bg-neutral-800/30 rounded transition-colors -mx-1 px-1">
      {/* Colored dot on rail */}
      <div className="relative shrink-0 w-[14px] h-[14px] flex items-center justify-center">
        <EntryDot accent={entry.accent} size="parent" />
      </div>

      {/* Icon */}
      <EntryIcon icon={entry.icon} accent={entry.accent} />

      {/* Heading + case context */}
      <p className="flex-1 min-w-0 text-[13px] truncate">
        <span className="font-medium text-primary-900 dark:text-primary-50">
          {entry.heading}
        </span>
        {caseTitle && (
          <span className="text-neutral-400 dark:text-neutral-500">
            {' \u00B7 '}{caseTitle}
          </span>
        )}
      </p>

      {/* Timestamp */}
      <span className="text-[11px] text-neutral-400 dark:text-neutral-500 shrink-0 tabular-nums">
        {formatTimeAgo(entry.timestamp)}
      </span>
    </div>
  );

  if (caseId) {
    return <Link href={`/cases/${caseId}`}>{content}</Link>;
  }
  return content;
}

function ChildRow({
  entry,
  isLast,
  caseId,
}: {
  entry: TimelineEntry;
  isLast: boolean;
  caseId: string | null;
}) {
  const content = (
    <div className="flex items-center gap-2 py-0.5 group/row hover:bg-neutral-50 dark:hover:bg-neutral-800/30 rounded transition-colors -mx-1 px-1">
      {/* Branch connector: vertical rail + horizontal branch */}
      <div className="relative shrink-0 w-[14px] h-full flex items-center justify-center">
        {/* Horizontal branch line */}
        <div
          className={cn(
            'absolute left-[7px] top-1/2 h-px bg-neutral-200 dark:bg-neutral-700/60',
            'w-[7px]'
          )}
        />
        {/* Vertical rail segment — continues for non-last, stops at midpoint for last */}
        {!isLast && (
          <div className="absolute left-[7px] top-0 bottom-0 w-px bg-neutral-200 dark:bg-neutral-700/60" />
        )}
        {isLast && (
          <div className="absolute left-[7px] top-0 h-1/2 w-px bg-neutral-200 dark:bg-neutral-700/60" />
        )}
      </div>

      {/* Indent spacer for branch */}
      <div className="w-1.5 shrink-0" />

      {/* Small child dot */}
      <EntryDot accent={entry.accent} size="child" />

      {/* Heading */}
      <p className="flex-1 min-w-0 text-[13px] truncate text-primary-800 dark:text-primary-200">
        {entry.heading}
      </p>

      {/* Timestamp */}
      <span className="text-[11px] text-neutral-400 dark:text-neutral-500 shrink-0 tabular-nums">
        {formatTimeAgo(entry.timestamp)}
      </span>
    </div>
  );

  if (caseId) {
    return <Link href={`/cases/${caseId}`}>{content}</Link>;
  }
  return content;
}

// --- Visual Primitives ---

const accentDotColor: Record<TimelineAccent, string> = {
  accent: 'bg-accent-500',
  success: 'bg-success-500',
  neutral: 'bg-neutral-300 dark:bg-neutral-600',
};

function EntryDot({ accent, size }: { accent: TimelineAccent; size: 'parent' | 'child' }) {
  return (
    <div
      className={cn(
        'rounded-full shrink-0',
        accentDotColor[accent],
        size === 'parent' ? 'w-[7px] h-[7px]' : 'w-[5px] h-[5px]'
      )}
    />
  );
}

function EntryIcon({ icon, accent }: { icon: TimelineIcon; accent: TimelineAccent }) {
  const colorClass = accent === 'success'
    ? 'text-success-500'
    : accent === 'accent'
    ? 'text-accent-500'
    : 'text-neutral-400 dark:text-neutral-500';

  const iconClass = cn('w-3.5 h-3.5 shrink-0', colorClass);

  switch (icon) {
    case 'check':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case 'plus':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 5v14M5 12h14" strokeLinecap="round" />
        </svg>
      );
    case 'zap':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
      );
    case 'refresh':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="23 4 23 10 17 10" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case 'layers':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polygon points="12 2 2 7 12 12 22 7 12 2" />
          <polyline points="2 17 12 22 22 17" strokeLinecap="round" strokeLinejoin="round" />
          <polyline points="2 12 12 17 22 12" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case 'file':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <path d="M14 2v6h6" strokeLinecap="round" />
        </svg>
      );
    default:
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
        </svg>
      );
  }
}

function formatTimeAgo(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'now';
  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays === 1) return '1d';
  if (diffDays < 7) return `${diffDays}d`;

  return then.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
