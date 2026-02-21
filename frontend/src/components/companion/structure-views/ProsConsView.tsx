/**
 * ProsConsView — Renders a two-column pros and cons layout.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';
import type { ProsConsContent, StructureViewProps } from './types';

export const ProsConsView = memo(function ProsConsView({
  content,
}: StructureViewProps<ProsConsContent>) {
  const pros = content.pros ?? [];
  const cons = content.cons ?? [];

  return (
    <div className="space-y-2">
      {content.subject && (
        <p className={cn('text-xs font-medium', theme.thinking.text)}>{content.subject}</p>
      )}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-[10px] text-emerald-400 font-medium mb-1">PROS</p>
          {pros.map((p, i) => (
            <p key={i} className={cn('text-[11px]', theme.thinking.text)}>
              + {typeof p === 'string' ? p : p.point}
            </p>
          ))}
        </div>
        <div>
          <p className="text-[10px] text-red-400 font-medium mb-1">CONS</p>
          {cons.map((c, i) => (
            <p key={i} className={cn('text-[11px]', theme.thinking.text)}>
              - {typeof c === 'string' ? c : c.point}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
});
