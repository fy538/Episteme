/**
 * InquiryResolutionPromptCard - Prompts user to resolve an inquiry
 *
 * Appears when there's strong evidence suggesting an inquiry can be resolved.
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
import type { InlineActionCard, InquiryResolutionPromptData } from '@/lib/types/chat';

interface InquiryResolutionPromptCardProps {
  card: InlineActionCard;
  onResolve: (inquiryId: string, conclusion?: string) => void;
  onAddMore: (inquiryId: string) => void;
  onDismiss: () => void;
}

export function InquiryResolutionPromptCard({
  card,
  onResolve,
  onAddMore,
  onDismiss,
}: InquiryResolutionPromptCardProps) {
  const data = card.data as unknown as InquiryResolutionPromptData;
  const { inquiryId, inquiryTitle, evidenceCount, suggestedConclusion } = data;

  return (
    <div className="my-3 mx-4">
      <ActionCard variant="success">
        <ActionCardHeader icon="!">
          <ActionCardTitle>Ready to resolve?</ActionCardTitle>
          <ActionCardDescription>
            &quot;{inquiryTitle}&quot; has {evidenceCount} pieces of evidence.
          </ActionCardDescription>

          {/* Suggested conclusion */}
          {suggestedConclusion && (
            <div className="mt-2 p-2 bg-success-100 dark:bg-success-800/30 rounded text-sm">
              <span className="text-xs text-success-700 dark:text-success-300 font-medium block mb-1">
                Suggested conclusion:
              </span>
              <span className="text-neutral-700 dark:text-neutral-300">
                {suggestedConclusion}
              </span>
            </div>
          )}
        </ActionCardHeader>

        <ActionCardFooter className="ml-7">
          <Button
            size="sm"
            onClick={() => onResolve(inquiryId, suggestedConclusion)}
          >
            Resolve
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onAddMore(inquiryId)}
          >
            Add More Evidence
          </Button>
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            Not Yet
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}
