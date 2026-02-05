/**
 * EvidenceSuggestionCard - Suggests adding mentioned evidence to an inquiry
 *
 * Appears when evidence is mentioned in chat that could support/contradict an inquiry.
 */

'use client';

import { Button } from '@/components/ui/button';
import {
  ActionCard,
  ActionCardHeader,
  ActionCardTitle,
  ActionCardDescription,
  ActionCardFooter,
  type ActionCardVariant,
} from '@/components/ui/action-card';
import type { InlineActionCard, EvidenceSuggestionData } from '@/lib/types/chat';

interface EvidenceSuggestionCardProps {
  card: InlineActionCard;
  onAddEvidence: (inquiryId?: string, direction?: string) => void;
  onDismiss: () => void;
}

type EvidenceDirection = 'supporting' | 'contradicting' | 'neutral';

const DIRECTION_CONFIG: Record<EvidenceDirection, {
  icon: string;
  label: string;
  variant: ActionCardVariant;
}> = {
  supporting: {
    icon: '+',
    label: 'Supporting',
    variant: 'success',
  },
  contradicting: {
    icon: '-',
    label: 'Contradicting',
    variant: 'error',
  },
  neutral: {
    icon: '~',
    label: 'Relevant',
    variant: 'info',
  },
};

export function EvidenceSuggestionCard({
  card,
  onAddEvidence,
  onDismiss,
}: EvidenceSuggestionCardProps) {
  const data = card.data as unknown as EvidenceSuggestionData;
  const { evidenceText, suggestedInquiryId, suggestedInquiryTitle, direction } = data;
  const config = DIRECTION_CONFIG[direction];

  return (
    <div className="my-3 mx-4">
      <ActionCard variant={config.variant}>
        <ActionCardHeader icon={<span className="font-mono">{config.icon}</span>}>
          <ActionCardTitle>{config.label} evidence detected</ActionCardTitle>

          {/* Evidence preview */}
          <ActionCardDescription className="line-clamp-2">
            &quot;{evidenceText}&quot;
          </ActionCardDescription>

          {/* Target inquiry */}
          {suggestedInquiryTitle && (
            <div className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
              For inquiry: {suggestedInquiryTitle}
            </div>
          )}
        </ActionCardHeader>

        <ActionCardFooter className="ml-7">
          <Button
            size="sm"
            onClick={() => onAddEvidence(suggestedInquiryId, direction)}
          >
            Add to Inquiry
          </Button>
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            Dismiss
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}
