/**
 * Skeleton loading components
 * Provides visual feedback during async operations
 */

import { cn } from '@/lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-md bg-neutral-200 dark:bg-neutral-800',
        className
      )}
      {...props}
    >
      <div className="shimmer absolute inset-0" />
    </div>
  );
}

export function ConversationsSkeleton() {
  return (
    <div className="w-72 border-r border-neutral-200 p-4 bg-neutral-50 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="h-7 w-32" />
        <Skeleton className="h-8 w-16 rounded-md" />
      </div>

      {/* Search */}
      <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-4 w-24" />
      </div>

      {/* Conversation groups */}
      {[1, 2].map((group) => (
        <div key={group} className="space-y-2">
          <Skeleton className="h-4 w-20" />
          <div className="space-y-2">
            {[1, 2, 3].map((item) => (
              <div
                key={item}
                className="rounded border border-transparent bg-white/60 px-3 py-2 space-y-2"
              >
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function MessageListSkeleton() {
  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className={`flex ${i % 2 === 0 ? 'justify-end' : 'justify-start'}`}
        >
          <div className="max-w-2xl space-y-2">
            <Skeleton
              className={cn(
                'rounded-lg',
                i % 2 === 0 ? 'h-16 w-64' : 'h-24 w-96'
              )}
            />
            {i % 2 === 1 && <Skeleton className="h-4 w-48" />}
          </div>
        </div>
      ))}
    </div>
  );
}

export function ProjectSidebarSkeleton() {
  return (
    <div className="w-64 border-r border-neutral-200 bg-white p-4 space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-8 w-8 rounded" />
      </div>
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-10 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}

export function CaseCardSkeleton() {
  return (
    <div className="border border-neutral-200 rounded-lg p-4 space-y-3">
      <div className="flex items-start justify-between">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-6 w-16 rounded-full" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
    </div>
  );
}

/** Workspace main content skeleton — mimics CaseHome layout */
export function WorkspaceContentSkeleton({ variant = 'default' }: { variant?: 'default' | 'brief' | 'dashboard' }) {
  if (variant === 'brief') {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
        <div className="space-y-3 mt-6">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
        <div className="space-y-3 mt-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </div>
    );
  }

  if (variant === 'dashboard') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-56" />
          <Skeleton className="h-9 w-28 rounded-md" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-4 space-y-3">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
              <div className="flex gap-2 pt-1">
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // default: CaseHome-like layout
  return (
    <div className="space-y-6">
      {/* Stage badge + title */}
      <div>
        <Skeleton className="h-5 w-24 rounded-full mb-3" />
        <Skeleton className="h-7 w-72" />
        <Skeleton className="h-4 w-48 mt-2" />
      </div>

      {/* Metric cards row */}
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-4 space-y-2">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-8 w-12" />
          </div>
        ))}
      </div>

      {/* Assumptions list */}
      <div className="space-y-3">
        <Skeleton className="h-5 w-32" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="h-4 w-4 rounded-full shrink-0" />
            <Skeleton className="h-4 flex-1" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        ))}
      </div>

      {/* Criteria list */}
      <div className="space-y-3">
        <Skeleton className="h-5 w-36" />
        {[1, 2].map((i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="h-4 w-4 rounded-full shrink-0" />
            <Skeleton className="h-4 flex-1" />
          </div>
        ))}
      </div>
    </div>
  );
}
