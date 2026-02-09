/**
 * SuggestedActions
 *
 * Renders 3 compact action cards in a horizontal row below the
 * recent decision card on the home page. Claude-style prompt chips.
 * Each card navigates to the relevant case or starts a new chat.
 */

'use client';

import { useRouter } from 'next/navigation';
import { useCallback } from 'react';
import { cn } from '@/lib/utils';
import { chatAPI } from '@/lib/api/chat';
import type { HomeActionItem } from '@/hooks/useHomeDashboard';

interface SuggestedActionsProps {
  items: HomeActionItem[];
}

const TYPE_ICONS: Record<HomeActionItem['type'], string> = {
  resolve_inquiry: '\u26a1',
  research_completed: '\ud83d\udcca',
  untested_assumptions: '\u26a0\ufe0f',
  resume_investigating: '\ud83d\udd0d',
  criteria_progress: '\u2705',
  start_investigation: '\ud83d\udca1',
  new_exploration: '\u2728',
};

const VARIANT_STYLES: Record<string, { bg: string; border: string; hover: string }> = {
  default: {
    bg: 'bg-neutral-50 dark:bg-neutral-900/50',
    border: 'border-neutral-200 dark:border-neutral-800',
    hover: 'hover:border-neutral-300 dark:hover:border-neutral-700',
  },
  success: {
    bg: 'bg-success-50/50 dark:bg-success-900/10',
    border: 'border-success-200 dark:border-success-800',
    hover: 'hover:border-success-300 dark:hover:border-success-700',
  },
  warning: {
    bg: 'bg-warning-50/50 dark:bg-warning-900/10',
    border: 'border-warning-200 dark:border-warning-800',
    hover: 'hover:border-warning-300 dark:hover:border-warning-700',
  },
  info: {
    bg: 'bg-info-50/50 dark:bg-info-900/10',
    border: 'border-info-200 dark:border-info-800',
    hover: 'hover:border-info-300 dark:hover:border-info-700',
  },
  error: {
    bg: 'bg-error-50/50 dark:bg-error-900/10',
    border: 'border-error-200 dark:border-error-800',
    hover: 'hover:border-error-300 dark:hover:border-error-700',
  },
  accent: {
    bg: 'bg-accent-50/50 dark:bg-accent-900/10',
    border: 'border-accent-200 dark:border-accent-800',
    hover: 'hover:border-accent-300 dark:hover:border-accent-700',
  },
};

export function SuggestedActions({ items }: SuggestedActionsProps) {
  const router = useRouter();

  const handleClick = useCallback(
    async (item: HomeActionItem) => {
      if (item.type === 'new_exploration') {
        // Start a new chat thread
        try {
          const thread = await chatAPI.createThread();
          router.push(`/chat/${thread.id}`);
        } catch {
          router.push('/chat');
        }
      } else {
        router.push(item.href);
      }
    },
    [router]
  );

  if (items.length === 0) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
      {items.map((item) => {
        const styles = VARIANT_STYLES[item.variant] ?? VARIANT_STYLES.default;

        return (
          <button
            key={item.id}
            onClick={() => handleClick(item)}
            className={cn(
              'flex flex-col items-start text-left rounded-lg border p-3',
              styles.bg,
              styles.border,
              styles.hover,
              'transition-all duration-150 cursor-pointer',
              'min-h-[72px]'
            )}
          >
            <span className="text-sm mb-1">{TYPE_ICONS[item.type]}</span>
            <span className="text-xs font-medium text-neutral-900 dark:text-neutral-100 line-clamp-2 leading-snug">
              {item.title}
            </span>
            {item.description && (
              <span className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-0.5 truncate max-w-full">
                {item.description}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
