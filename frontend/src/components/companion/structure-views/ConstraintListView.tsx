/**
 * ConstraintListView — Renders a list of constraints with impact notes.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';
import type { ConstraintListContent, StructureViewProps } from './types';

export const ConstraintListView = memo(function ConstraintListView({
  content,
}: StructureViewProps<ConstraintListContent>) {
  const constraints = content.constraints ?? [];

  return (
    <div className="space-y-1">
      {content.topic && (
        <p className={cn('text-xs font-medium', theme.thinking.text)}>{content.topic}</p>
      )}
      {constraints.map((c, i) => (
        <div key={i} className="flex items-start gap-1.5">
          <span className="text-amber-400 text-xs mt-0.5">{'\u2022'}</span>
          <div>
            <span className={cn('text-xs', theme.thinking.text)}>{c.text}</span>
            {c.impact && (
              <p className={cn('text-[10px]', theme.thinking.textMuted)}>{c.impact}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
});
