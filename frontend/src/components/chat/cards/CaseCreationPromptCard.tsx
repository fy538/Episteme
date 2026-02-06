/**
 * CaseCreationPromptCard - Prompts user to create a case when signals accumulate
 *
 * Appears when there are enough signals to warrant structured tracking.
 */

'use client';

import { Button } from '@/components/ui/button';
import {
  ActionCard,
  ActionCardHeader,
  ActionCardTitle,
  ActionCardDescription,
  ActionCardFooter,
} from '@/components/ui/action-card';
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
  const { signalCount, suggestedTitle, keyQuestions, aiReason } = data;

  return (
    <div className="my-3 mx-4">
      <ActionCard variant="warning">
        <ActionCardHeader icon="+">
          <ActionCardTitle>Track this as a case?</ActionCardTitle>
          <ActionCardDescription>
            {aiReason || (
              <>
                I see a decision forming with {signalCount} signals
                {keyQuestions && keyQuestions.length > 0 && (
                  <> and {keyQuestions.length} key question{keyQuestions.length !== 1 ? 's' : ''}</>
                )}.
              </>
            )}
          </ActionCardDescription>

          {/* Key questions preview */}
          {keyQuestions && keyQuestions.length > 0 && (
            <div className="mt-2 space-y-1">
              {keyQuestions.slice(0, 2).map((q, i) => (
                <div
                  key={i}
                  className="text-xs text-warning-700 dark:text-warning-300 flex items-start gap-1"
                >
                  <span>?</span>
                  <span className="truncate">{q}</span>
                </div>
              ))}
              {keyQuestions.length > 2 && (
                <div className="text-xs text-warning-600 dark:text-warning-400">
                  +{keyQuestions.length - 2} more questions
                </div>
              )}
            </div>
          )}

          {/* Suggested title */}
          {suggestedTitle && (
            <div className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
              Suggested: &quot;{suggestedTitle}&quot;
            </div>
          )}
        </ActionCardHeader>

        <ActionCardFooter className="ml-7">
          <Button size="sm" onClick={() => onCreateCase(suggestedTitle)} disabled={isCreating}>
            {isCreating ? (
              <span className="inline-flex items-center gap-2">
                <span className="w-3 h-3 border-2 border-white/60 border-t-white rounded-full animate-spin" />
                Creating...
              </span>
            ) : (
              'Create Case'
            )}
          </Button>
          <Button variant="ghost" size="sm" onClick={onDismiss} disabled={isCreating}>
            Keep Chatting
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}
