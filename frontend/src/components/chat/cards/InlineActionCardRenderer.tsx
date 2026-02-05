/**
 * InlineActionCardRenderer - Renders the appropriate inline action card based on type
 */

'use client';

import type { InlineActionCard } from '@/lib/types/chat';
import { SignalsCollapsedCard } from './SignalsCollapsedCard';
import { CaseCreationPromptCard } from './CaseCreationPromptCard';
import { EvidenceSuggestionCard } from './EvidenceSuggestionCard';
import { InquiryResolutionPromptCard } from './InquiryResolutionPromptCard';
import { ResearchResultsCard } from './ResearchResultsCard';
import { InquiryFocusPromptCard } from './InquiryFocusPromptCard';

export interface InlineCardActions {
  // Signals
  onExpandSignals?: () => void;
  onSignalClick?: (signalText: string) => void;

  // Case creation
  onCreateCase?: (suggestedTitle?: string) => void;

  // Evidence
  onAddEvidence?: (inquiryId?: string, direction?: string) => void;

  // Inquiry resolution
  onResolveInquiry?: (inquiryId: string, conclusion?: string) => void;
  onAddMoreEvidence?: (inquiryId: string) => void;

  // Research
  onViewResearchResults?: (researchId: string) => void;
  onAddResearchToCase?: (researchId: string) => void;

  // Focus
  onFocusInquiry?: (inquiryId: string) => void;

  // Common
  onDismissCard?: (cardId: string) => void;
}

interface InlineActionCardRendererProps {
  card: InlineActionCard;
  actions: InlineCardActions;
}

export function InlineActionCardRenderer({
  card,
  actions,
}: InlineActionCardRendererProps) {
  const handleDismiss = () => {
    actions.onDismissCard?.(card.id);
  };

  switch (card.type) {
    case 'signals_collapsed':
      return (
        <SignalsCollapsedCard
          card={card}
          onExpand={actions.onExpandSignals}
          onSignalClick={actions.onSignalClick}
        />
      );

    case 'case_creation_prompt':
      return (
        <CaseCreationPromptCard
          card={card}
          onCreateCase={actions.onCreateCase || (() => {})}
          onDismiss={handleDismiss}
        />
      );

    case 'evidence_suggestion':
      return (
        <EvidenceSuggestionCard
          card={card}
          onAddEvidence={actions.onAddEvidence || (() => {})}
          onDismiss={handleDismiss}
        />
      );

    case 'inquiry_resolution':
      return (
        <InquiryResolutionPromptCard
          card={card}
          onResolve={actions.onResolveInquiry || (() => {})}
          onAddMore={actions.onAddMoreEvidence || (() => {})}
          onDismiss={handleDismiss}
        />
      );

    case 'research_results':
      return (
        <ResearchResultsCard
          card={card}
          onViewResults={actions.onViewResearchResults || (() => {})}
          onAddToCase={actions.onAddResearchToCase || (() => {})}
          onDismiss={handleDismiss}
        />
      );

    case 'inquiry_focus_prompt':
      return (
        <InquiryFocusPromptCard
          card={card}
          onFocus={actions.onFocusInquiry || (() => {})}
          onDismiss={handleDismiss}
        />
      );

    default:
      return null;
  }
}
