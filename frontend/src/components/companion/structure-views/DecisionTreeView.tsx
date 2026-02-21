/**
 * DecisionTreeView — Renders a decision tree with branching options.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';
import type { BranchStatus, DecisionTreeContent, StructureViewProps } from './types';

const BRANCH_STATUS_COLORS: Record<BranchStatus, string> = {
  viable: 'text-emerald-400',
  preferred: 'text-blue-400',
  exploring: 'text-amber-400',
  eliminated: 'text-zinc-500 line-through',
};

export const DecisionTreeView = memo(function DecisionTreeView({
  content,
}: StructureViewProps<DecisionTreeContent>) {
  const question = content.question ?? '';
  const branches = content.branches ?? [];

  return (
    <div className="space-y-1.5">
      {question && (
        <p className={cn('text-xs font-medium', theme.thinking.text)}>{question}</p>
      )}
      {branches.map((branch, i) => (
        <div key={i} className="pl-3 border-l border-zinc-700/50">
          <div className="flex items-center gap-1.5">
            <span className={cn(
              'text-xs font-medium',
              branch.status ? (BRANCH_STATUS_COLORS[branch.status] ?? 'text-zinc-400') : 'text-zinc-400',
            )}>
              {branch.label}
            </span>
            {branch.status && (
              <span className={cn('text-[10px] px-1 rounded', theme.thinking.textMuted)}>
                {branch.status}
              </span>
            )}
          </div>
          {branch.detail && (
            <p className={cn('text-[11px] mt-0.5', theme.thinking.textMuted)}>{branch.detail}</p>
          )}
          {branch.reason && branch.status === 'eliminated' && (
            <p className="text-[10px] text-zinc-600 mt-0.5">{branch.reason}</p>
          )}
        </div>
      ))}
    </div>
  );
});
