/**
 * TrackingLists — Renders established facts, open questions, and eliminated options.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';

interface TrackingListsProps {
  established: string[];
  openQuestions: string[];
  eliminated: string[];
}

export const TrackingLists = memo(function TrackingLists({
  established,
  openQuestions,
  eliminated,
}: TrackingListsProps) {
  if (established.length === 0 && openQuestions.length === 0 && eliminated.length === 0) {
    return null;
  }

  return (
    <div className={cn('pt-2 border-t space-y-2', theme.thinking.border)}>
      {established.length > 0 && (
        <div>
          <p className="text-[10px] text-emerald-400 font-medium mb-0.5">ESTABLISHED</p>
          {established.map((item, i) => (
            <p key={i} className={cn('text-[11px] pl-2', theme.thinking.text)}>{item}</p>
          ))}
        </div>
      )}
      {openQuestions.length > 0 && (
        <div>
          <p className="text-[10px] text-amber-400 font-medium mb-0.5">OPEN QUESTIONS</p>
          {openQuestions.map((item, i) => (
            <p key={i} className={cn('text-[11px] pl-2', theme.thinking.text)}>? {item}</p>
          ))}
        </div>
      )}
      {eliminated.length > 0 && (
        <div>
          <p className="text-[10px] text-zinc-500 font-medium mb-0.5">ELIMINATED</p>
          {eliminated.map((item, i) => (
            <p key={i} className="text-[11px] pl-2 text-zinc-600">{item}</p>
          ))}
        </div>
      )}
    </div>
  );
});
