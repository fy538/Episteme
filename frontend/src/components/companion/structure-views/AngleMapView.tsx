/**
 * AngleMapView — Renders the angles/dimensions being explored in a conversation.
 *
 * Lightweight structure for early conversations: shows which angles have been
 * opened, touched, or not yet discussed. The 'not_yet_discussed' items are
 * the only generative element — everything else traces to the conversation.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';
import type { AngleStatus, AngleMapContent, StructureViewProps } from './types';

const STATUS_DOT: Record<AngleStatus, string> = {
  opened: 'bg-emerald-400',
  touched: 'bg-amber-400',
  not_yet_discussed: 'bg-zinc-600 ring-1 ring-zinc-500',
};

const STATUS_TEXT: Record<AngleStatus, string> = {
  opened: 'text-emerald-400',
  touched: 'text-amber-400',
  not_yet_discussed: 'text-zinc-500 italic',
};

export const AngleMapView = memo(function AngleMapView({
  content,
}: StructureViewProps<AngleMapContent>) {
  const angles = content.angles ?? [];

  return (
    <div className="space-y-1.5">
      {content.topic && (
        <p className={cn('text-xs font-medium', theme.thinking.text)}>{content.topic}</p>
      )}
      {angles.map((angle, i) => {
        const status = angle.status ?? 'touched';
        return (
          <div key={i} className="flex items-start gap-2 py-0.5">
            <span
              className={cn(
                'w-1.5 h-1.5 rounded-full mt-1.5 shrink-0',
                STATUS_DOT[status],
              )}
              aria-hidden="true"
            />
            <div className="min-w-0">
              <span className={cn('text-xs', STATUS_TEXT[status])}>
                {angle.label}
              </span>
              {angle.source && (
                <p className={cn('text-[10px]', theme.thinking.textMuted)}>
                  {angle.source}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
});
