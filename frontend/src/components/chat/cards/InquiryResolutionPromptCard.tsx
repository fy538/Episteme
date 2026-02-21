/**
 * InquiryResolutionPromptCard - Prompts user to resolve an inquiry
 *
 * Appears when the AI suggests an inquiry can be resolved.
 * Includes confirmation step before resolving.
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
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
  onAddMore?: (inquiryId: string) => void;
  onDismiss: () => void;
  isResolving?: boolean;
}

export function InquiryResolutionPromptCard({
  card,
  onResolve,
  onDismiss,
  isResolving = false,
}: InquiryResolutionPromptCardProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const data = card.data as unknown as InquiryResolutionPromptData;
  const { inquiryId, inquiryTitle, suggestedConclusion } = data;

  // Confirmation view
  if (showConfirm) {
    return (
      <div className="my-3 mx-4">
        <ActionCard variant="info">
          <ActionCardHeader icon="?">
            <ActionCardTitle>Confirm Resolution</ActionCardTitle>
            <ActionCardDescription>
              Resolving &quot;{inquiryTitle}&quot; will mark it as complete with this conclusion.
              This action helps finalize your analysis.
            </ActionCardDescription>

            {suggestedConclusion && (
              <div className="mt-2 p-2 bg-info-100 dark:bg-info-800/30 rounded text-sm">
                <span className="text-xs text-info-700 dark:text-info-300 font-medium block mb-1">
                  Conclusion:
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
              disabled={isResolving}
            >
              {isResolving ? (
                <span className="inline-flex items-center gap-2">
                  <Spinner size="xs" />
                  Resolving...
                </span>
              ) : (
                'Yes, Resolve'
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowConfirm(false)}
              disabled={isResolving}
            >
              Cancel
            </Button>
          </ActionCardFooter>
        </ActionCard>
      </div>
    );
  }

  // Default view
  return (
    <div className="my-3 mx-4">
      <ActionCard variant="success">
        <ActionCardHeader icon="!">
          <ActionCardTitle>Ready to resolve?</ActionCardTitle>
          <ActionCardDescription>
            &quot;{inquiryTitle}&quot; may be ready for resolution.
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
            onClick={() => setShowConfirm(true)}
          >
            Resolve
          </Button>
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            Not Yet
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}
