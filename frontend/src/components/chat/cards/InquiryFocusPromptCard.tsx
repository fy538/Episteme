/**
 * InquiryFocusPromptCard - Prompts user to focus on a specific inquiry
 *
 * Appears when the user asks about a topic that matches an existing inquiry.
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
import type { InlineActionCard, InquiryFocusPromptData } from '@/lib/types/chat';

interface InquiryFocusPromptCardProps {
  card: InlineActionCard;
  onFocus: (inquiryId: string) => void;
  onDismiss: () => void;
}

export function InquiryFocusPromptCard({
  card,
  onFocus,
  onDismiss,
}: InquiryFocusPromptCardProps) {
  const data = card.data as unknown as InquiryFocusPromptData;
  const { inquiryId, inquiryTitle, matchedTopic } = data;

  return (
    <div className="my-3 mx-4">
      <ActionCard variant="accent">
        <ActionCardHeader icon="@">
          <ActionCardTitle>Related inquiry found</ActionCardTitle>
          <ActionCardDescription>
            Your question about &quot;{matchedTopic}&quot; relates to an open inquiry.
          </ActionCardDescription>

          {/* Inquiry title */}
          <div className="mt-2 p-2 bg-accent-100 dark:bg-accent-800/30 rounded">
            <span className="text-sm font-medium text-accent-700 dark:text-accent-300">
              {inquiryTitle}
            </span>
          </div>

          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-2">
            Focus mode will help you gather evidence specifically for this inquiry.
          </p>
        </ActionCardHeader>

        <ActionCardFooter className="ml-7">
          <Button size="sm" onClick={() => onFocus(inquiryId)}>
            Focus on Inquiry
          </Button>
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            Keep Chatting
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}
