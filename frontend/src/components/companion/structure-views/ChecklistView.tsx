/**
 * ChecklistView — Renders a checklist with status indicators.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';
import type { CheckItemStatus, ChecklistContent, StructureViewProps } from './types';

const CHECK_STATUS_ICONS: Record<CheckItemStatus, string> = {
  done: '\u2713',
  pending: '\u25cb',
  blocked: '\u2717',
  not_applicable: '\u2014',
};

export const ChecklistView = memo(function ChecklistView({
  content,
}: StructureViewProps<ChecklistContent>) {
  const items = content.items ?? [];

  return (
    <div className="space-y-1">
      {content.title && (
        <p className={cn('text-xs font-medium', theme.thinking.text)}>{content.title}</p>
      )}
      {items.map((item, i) => (
        <div key={i} className="flex items-start gap-1.5">
          <span className={cn(
            'text-xs mt-0.5',
            item.status === 'done' ? 'text-emerald-400' :
            item.status === 'blocked' ? 'text-red-400' : 'text-zinc-500',
          )}>
            {CHECK_STATUS_ICONS[item.status ?? 'pending']}
          </span>
          <div className="flex-1">
            <span className={cn(
              'text-xs',
              item.status === 'done' ? 'text-emerald-400/80' : theme.thinking.text,
            )}>
              {item.text}
            </span>
            {item.detail && (
              <p className={cn('text-[10px]', theme.thinking.textMuted)}>{item.detail}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
});
