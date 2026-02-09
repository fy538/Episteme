/**
 * InlineActionCardRenderer - Renders the appropriate inline action card based on type
 *
 * Wraps all card types in a slide-up entrance animation for polish.
 */

'use client';

import { motion } from 'framer-motion';
import type { InlineActionCard } from '@/lib/types/chat';
import { CaseCreationPromptCard } from './CaseCreationPromptCard';
import { CasePreviewCard } from './CasePreviewCard';
import { InquiryResolutionPromptCard } from './InquiryResolutionPromptCard';
import { ResearchResultsCard } from './ResearchResultsCard';
import { InquiryFocusPromptCard } from './InquiryFocusPromptCard';
import { PlanDiffProposalCard } from './PlanDiffProposalCard';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { easingCurves, transitionDurations } from '@/lib/motion-config';

export interface InlineCardActions {
  // Case creation
  onCreateCase?: (suggestedTitle?: string) => void;

  // Case preview (after analysis)
  onCreateCaseFromPreview?: (analysis: Record<string, unknown>, title: string) => void;
  onAdjustCasePreview?: () => void;

  // Inquiry resolution
  onResolveInquiry?: (inquiryId: string, conclusion?: string) => void;

  // Research
  onViewResearchResults?: (researchId: string) => void;
  onAddResearchToCase?: (researchId: string) => void;

  // Focus
  onFocusInquiry?: (inquiryId: string) => void;

  // Plan diff
  onAcceptPlanDiff?: (proposedContent: Record<string, unknown>, diffSummary: string, diffData: Record<string, unknown>) => Promise<void> | void;

  // Loading states
  isCreatingCase?: boolean;

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
  const prefersReducedMotion = useReducedMotion();

  const handleDismiss = () => {
    actions.onDismissCard?.(card.id);
  };

  let cardContent: React.ReactNode;

  switch (card.type) {
    case 'case_creation_prompt':
      cardContent = (
        <CaseCreationPromptCard
          card={card}
          onCreateCase={actions.onCreateCase || (() => {})}
          onDismiss={handleDismiss}
          isCreating={actions.isCreatingCase}
        />
      );
      break;

    case 'case_preview':
      cardContent = (
        <CasePreviewCard
          card={card}
          onCreateCase={actions.onCreateCaseFromPreview || (() => {})}
          onAdjust={actions.onAdjustCasePreview || (() => {})}
          onDismiss={handleDismiss}
          isCreating={actions.isCreatingCase}
        />
      );
      break;

    case 'inquiry_resolution':
      cardContent = (
        <InquiryResolutionPromptCard
          card={card}
          onResolve={actions.onResolveInquiry || (() => {})}
          onAddMore={() => {}}
          onDismiss={handleDismiss}
        />
      );
      break;

    case 'research_results':
      cardContent = (
        <ResearchResultsCard
          card={card}
          onViewResults={actions.onViewResearchResults || (() => {})}
          onAddToCase={actions.onAddResearchToCase || (() => {})}
          onDismiss={handleDismiss}
        />
      );
      break;

    case 'inquiry_focus_prompt':
      cardContent = (
        <InquiryFocusPromptCard
          card={card}
          onFocus={actions.onFocusInquiry || (() => {})}
          onDismiss={handleDismiss}
        />
      );
      break;

    case 'plan_diff_proposal':
      cardContent = (
        <PlanDiffProposalCard
          card={card}
          onAccept={actions.onAcceptPlanDiff || (() => {})}
          onDismiss={handleDismiss}
        />
      );
      break;

    default:
      return null;
  }

  if (prefersReducedMotion) {
    return <>{cardContent}</>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: transitionDurations.normal,
        ease: easingCurves.easeOutExpo,
      }}
    >
      {cardContent}
    </motion.div>
  );
}
