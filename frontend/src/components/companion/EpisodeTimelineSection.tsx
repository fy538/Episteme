/**
 * EpisodeTimelineSection — Renders conversation episode history.
 *
 * Shows a vertical timeline of topically coherent conversation segments.
 * The active (unsealed) episode appears at top with a pulsing indicator,
 * followed by sealed episodes in reverse chronological order.
 *
 * Each row shows topic label, message count, and shift type indicator.
 */

'use client';

import { useId, useState } from 'react';
import { cn } from '@/lib/utils';
import { theme, isTerminalTheme } from '@/lib/theme/companionTheme';
import type { ConversationEpisode, CurrentEpisodeInfo, EpisodeShiftType } from '@/lib/types/companion';

interface EpisodeTimelineSectionProps {
  episodes: ConversationEpisode[];
  currentEpisode?: CurrentEpisodeInfo;
  collapsed?: boolean;
}

const SHIFT_COLORS: Record<EpisodeShiftType, string> = {
  initial: 'border-l-zinc-500',
  continuous: 'border-l-emerald-500',
  partial_shift: 'border-l-amber-500',
  discontinuous: 'border-l-red-500',
};

const SHIFT_DOT_COLORS: Record<EpisodeShiftType, string> = {
  initial: 'bg-zinc-400',
  continuous: 'bg-emerald-400',
  partial_shift: 'bg-amber-400',
  discontinuous: 'bg-red-400',
};

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function EpisodeTimelineSection({
  episodes,
  currentEpisode,
  collapsed = false,
}: EpisodeTimelineSectionProps) {
  const [isExpanded, setIsExpanded] = useState(!collapsed);
  const contentId = useId();

  const totalEpisodes = episodes.length + (currentEpisode ? 1 : 0);

  return (
    <section
      className={cn('border-b', theme.thinking.border)}
      role="region"
      aria-label="Episode timeline"
    >
      {/* Header */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'w-full px-3 py-2 flex items-center gap-2 text-left',
          'hover:bg-zinc-800/30 transition-colors',
          isTerminalTheme && 'font-mono'
        )}
        aria-expanded={isExpanded}
        aria-controls={contentId}
      >
        <span className={cn('text-xs', theme.thinking.text)} aria-hidden="true">
          {isExpanded ? '▾' : '▸'}
        </span>
        <span className={cn('text-xs tracking-wider font-medium uppercase', theme.thinking.text)}>
          Topics
        </span>
        {totalEpisodes > 0 && (
          <span className={cn('text-xs ml-auto tabular-nums', theme.thinking.textMuted)}>
            {totalEpisodes}
          </span>
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div id={contentId} className="px-3 pb-3 space-y-0.5">
          {/* Active episode */}
          {currentEpisode && !currentEpisode.sealed && (
            <div className="flex items-center gap-2 py-1.5 pl-2 border-l-2 border-l-cyan-500">
              <span className="relative flex h-2 w-2 shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
              </span>
              <span className={cn('text-xs truncate flex-1', theme.thinking.text)}>
                {currentEpisode.topic_label || 'Current topic'}
              </span>
            </div>
          )}

          {/* Sealed episodes (reverse chronological) */}
          {[...episodes].reverse().map((ep) => (
            <div
              key={ep.id}
              className={cn(
                'flex items-center gap-2 py-1.5 pl-2 border-l-2',
                SHIFT_COLORS[ep.shift_type],
              )}
            >
              <span
                className={cn(
                  'inline-flex rounded-full h-1.5 w-1.5 shrink-0',
                  SHIFT_DOT_COLORS[ep.shift_type],
                )}
              />
              <span className={cn('text-xs truncate flex-1', theme.thinking.textMuted)}>
                {ep.topic_label || `Episode ${ep.episode_index}`}
              </span>
              <span className={cn('text-xs tabular-nums shrink-0', theme.thinking.textSubtle)}>
                {ep.message_count}
              </span>
              {ep.sealed_at && (
                <span className={cn('text-xs shrink-0 hidden sm:inline', theme.thinking.textSubtle)}>
                  {formatRelativeTime(ep.sealed_at)}
                </span>
              )}
            </div>
          ))}

          {/* Empty state */}
          {totalEpisodes === 0 && (
            <div className={cn('text-xs py-2', theme.thinking.textSubtle)}>
              No topic segments yet
            </div>
          )}
        </div>
      )}
    </section>
  );
}
