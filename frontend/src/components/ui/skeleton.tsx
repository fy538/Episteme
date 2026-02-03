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
