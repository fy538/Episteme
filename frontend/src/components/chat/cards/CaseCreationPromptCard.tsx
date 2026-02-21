/**
 * CaseCreationPromptCard - Subtle inline nudge to structure a case
 *
 * Appears when the LLM's action hints suggest a case would help.
 * Designed to be a gentle suggestion, not an interruption — minimal
 * chrome, conversational reason text, small text buttons.
 */

'use client';

import { Button } from '@/components/ui/button';
import type { InlineActionCard, CaseCreationPromptData } from '@/lib/types/chat';

interface CaseCreationPromptCardProps {
  card: InlineActionCard;
  onCreateCase: (suggestedTitle?: string) => void;
  onDismiss: () => void;
  isCreating?: boolean;
}

export function CaseCreationPromptCard({
  card,
  onCreateCase,
  onDismiss,
  isCreating = false,
}: CaseCreationPromptCardProps) {
  const data = card.data as unknown as CaseCreationPromptData;
  const { suggestedTitle, aiReason } = data;

  return (
    <div className="my-3">
      <div className="border border-neutral-200 dark:border-neutral-800 rounded-lg px-4 py-3 bg-neutral-50/50 dark:bg-neutral-900/30">
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          {aiReason || 'This looks like a decision worth structuring.'}
        </p>
        <div className="flex items-center gap-3 mt-2.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onCreateCase(suggestedTitle)}
            disabled={isCreating}
            isLoading={isCreating}
            className="text-xs font-medium text-accent-600 dark:text-accent-400 hover:text-accent-700 dark:hover:text-accent-300 px-0"
          >
            {isCreating ? 'Analyzing...' : 'Structure as a case'}
          </Button>
          <span className="text-neutral-300 dark:text-neutral-700">&middot;</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDismiss}
            disabled={isCreating}
            className="text-xs text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 px-0"
          >
            Dismiss
          </Button>
        </div>
      </div>
    </div>
  );
}
