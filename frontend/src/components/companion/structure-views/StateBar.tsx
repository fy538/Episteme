/**
 * StateBar — Quick overview counts for established, open, and eliminated items.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';
import type { ConversationStructure } from '@/lib/types/companion';

export const StateBar = memo(function StateBar({
  structure,
}: {
  structure: ConversationStructure;
}) {
  const { established, open_questions, eliminated } = structure;

  return (
    <div className={cn('flex items-center gap-2 text-xs', theme.thinking.textMuted)}>
      {established.length > 0 && (
        <span className="text-emerald-400">{established.length} established</span>
      )}
      {open_questions.length > 0 && (
        <span className="text-amber-400">{open_questions.length} open</span>
      )}
      {eliminated.length > 0 && (
        <span className="text-zinc-500">{eliminated.length} eliminated</span>
      )}
    </div>
  );
});
