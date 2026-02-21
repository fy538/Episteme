/**
 * ComparisonView — Renders a comparison table of options against criteria.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';
import type { ComparisonContent, StructureViewProps } from './types';

export const ComparisonView = memo(function ComparisonView({
  content,
}: StructureViewProps<ComparisonContent>) {
  const options = content.options ?? [];
  const criteria = content.criteria ?? [];

  if (options.length === 0) {
    return (
      <p className={cn('text-[11px] italic', theme.thinking.textMuted)}>
        No options to compare yet.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      {content.comparing && (
        <p className={cn('text-xs font-medium mb-1', theme.thinking.text)}>{content.comparing}</p>
      )}
      <table className="w-full text-[11px]">
        <thead>
          <tr>
            <th className={cn('text-left py-1 pr-2', theme.thinking.textMuted)}>Criterion</th>
            {options.map((opt) => (
              <th key={opt} className={cn('text-left py-1 px-1', theme.thinking.text)}>{opt}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {criteria.map((row, i) => (
            <tr key={i} className="border-t border-zinc-800/50">
              <td className={cn('py-1 pr-2', theme.thinking.textMuted)}>{row.criterion}</td>
              {options.map((opt) => (
                <td key={opt} className={cn(
                  'py-1 px-1',
                  row.winner === opt ? 'text-emerald-400' : theme.thinking.text,
                )}>
                  {row.values?.[opt] ?? '-'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
});
