/**
 * StatusSection - Displays background work progress and recently completed items
 *
 * Shows:
 * - Running tasks with progress bars
 * - Just-completed items (last ~30 seconds)
 */

'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { theme, isTerminalTheme } from '@/lib/theme/companionTheme';
import type { BackgroundWorkItem } from '@/lib/types/companion';

interface StatusSectionProps {
  inProgress: BackgroundWorkItem[];
  justCompleted: BackgroundWorkItem[];
  onDismissCompleted?: (id: string) => void;
}

const TYPE_ICONS: Record<string, string> = {
  research: '?',
  analysis: '*',
  extraction: '#',
};

const TYPE_LABELS: Record<string, string> = {
  research: 'Research',
  analysis: 'Analysis',
  extraction: 'Extract',
};

export function StatusSection({
  inProgress,
  justCompleted,
  onDismissCompleted,
}: StatusSectionProps) {
  const [collapsed, setCollapsed] = useState(false);

  const hasItems = inProgress.length > 0 || justCompleted.length > 0;

  if (!hasItems) {
    return null;
  }

  const totalInProgress = inProgress.length;
  const totalCompleted = justCompleted.length;

  return (
    <section className={cn('border-b', theme.thinking.border)}>
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className={cn(
          'w-full px-3 py-2 flex items-center justify-between transition-colors',
          theme.thinking.bgHover,
          isTerminalTheme && 'font-mono'
        )}
      >
        <div className="flex items-center gap-2">
          <span className={cn('text-xs', theme.thinking.text)}>{'>'}</span>
          <span className={cn('text-xs tracking-wider font-medium uppercase', theme.thinking.text)}>
            STATUS
          </span>
          {totalInProgress > 0 && (
            <span className={cn('animate-pulse text-xs', theme.status.running.text)}>
              ({totalInProgress} active)
            </span>
          )}
          {totalCompleted > 0 && totalInProgress === 0 && (
            <span className={cn('text-xs', theme.status.completed.text)}>
              ({totalCompleted} done)
            </span>
          )}
        </div>
        <span className={cn('text-xs', theme.thinking.textMuted)}>
          {collapsed ? '[+]' : '[-]'}
        </span>
      </button>

      {/* Content */}
      {!collapsed && (
        <div className={cn('px-3 pb-3 space-y-2', isTerminalTheme && 'font-mono')}>
          {/* In Progress Items */}
          {inProgress.map((item) => (
            <div
              key={item.id}
              className={cn(
                'border p-2 text-xs',
                theme.thinking.border,
                theme.thinking.bg
              )}
            >
              <div className={cn('flex items-center gap-2 mb-1', theme.status.running.text)}>
                <span className="animate-spin">@</span>
                <span className={theme.thinking.text}>
                  {TYPE_LABELS[item.type] || item.type}:
                </span>
                <span className={cn('truncate flex-1', theme.thinking.text)}>
                  {item.title}
                </span>
              </div>

              {/* Progress bar */}
              {item.progress !== undefined && (
                <div className="mt-1">
                  <div className={cn('mb-0.5', theme.thinking.textMuted)}>
                    {item.progress}%
                  </div>
                  <div className={theme.thinking.text}>
                    {Array.from({ length: 20 }).map((_, i) => (
                      <span key={i}>
                        {i < Math.floor(item.progress! / 5) ? '=' : '-'}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Just Completed Items */}
          {justCompleted.map((item) => (
            <div
              key={item.id}
              className={cn(
                'border p-2 text-xs',
                theme.status.completed.bg
              )}
              style={{ borderColor: 'rgba(34, 197, 94, 0.3)' }} // green-900/30 equivalent
            >
              <div className="flex items-center justify-between">
                <div className={cn('flex items-center gap-2', theme.status.completed.text)}>
                  <span>+</span>
                  <span>
                    {TYPE_LABELS[item.type] || item.type}:
                  </span>
                  <span className="truncate">
                    {item.title}
                  </span>
                </div>
                {onDismissCompleted && (
                  <button
                    onClick={() => onDismissCompleted(item.id)}
                    className={cn(
                      'opacity-60 hover:opacity-100 transition-opacity',
                      theme.status.completed.text
                    )}
                  >
                    [x]
                  </button>
                )}
              </div>
              <div className={cn('mt-1 opacity-60', theme.status.completed.text)}>
                (just now)
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
