/**
 * CompanionSkeleton — Themed loading skeleton for the companion panel.
 *
 * Mimics the layout of ThinkingSection + ConversationStructure
 * so the panel feels alive while the companion LLM processes the
 * first response. Uses the existing Skeleton primitive with
 * companion theme colors.
 */

'use client';

import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import { theme, isTerminalTheme } from '@/lib/theme/companionTheme';

export function CompanionSkeleton() {
  // Computed inside the component body so it re-evaluates if theme
  // ever becomes dynamic (e.g. user theme switcher).
  const skeletonBg = isTerminalTheme
    ? '!bg-cyan-950/30'
    : '!bg-accent-100 dark:!bg-accent-900/20';

  return (
    <div className={cn('px-3 py-3 space-y-4 animate-in fade-in duration-300', isTerminalTheme && 'font-mono')}>
      {/* Section 1: Mimics ThinkingSection — header + content lines */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Skeleton className={cn('h-3 w-3', skeletonBg)} />
          <Skeleton className={cn('h-3 w-16', skeletonBg)} />
        </div>
        <div className={cn('border-l-2 pl-2 space-y-1.5', theme.thinking.border)}>
          <Skeleton className={cn('h-2.5 w-full', skeletonBg)} />
          <Skeleton className={cn('h-2.5 w-4/5', skeletonBg)} />
          <Skeleton className={cn('h-2.5 w-3/5', skeletonBg)} />
        </div>
      </div>

      {/* Section 2: Mimics ConversationStructure — header + tracking items */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Skeleton className={cn('h-3 w-3', skeletonBg)} />
          <Skeleton className={cn('h-3 w-20', skeletonBg)} />
        </div>
        <div className="space-y-1.5 pl-2">
          <div className="flex items-center gap-1.5">
            <Skeleton className={cn('h-2 w-2 rounded-full', skeletonBg)} />
            <Skeleton className={cn('h-2.5 w-3/4', skeletonBg)} />
          </div>
          <div className="flex items-center gap-1.5">
            <Skeleton className={cn('h-2 w-2 rounded-full', skeletonBg)} />
            <Skeleton className={cn('h-2.5 w-2/3', skeletonBg)} />
          </div>
        </div>
      </div>
    </div>
  );
}
