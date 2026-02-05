import { RichCard, CardAction } from '@/lib/types/cards';
import { SignalExtractionCard } from './SignalExtractionCard';
import { AssumptionValidatorCard } from './AssumptionValidatorCard';
import { ActionPromptCard } from './ActionPromptCard';
import { ResearchStatusCard } from './ResearchStatusCard';

interface Props {
  card: RichCard;
  onAction: (action: CardAction) => void;
}

export function CardRenderer({ card, onAction }: Props) {
  // Extract type for use in default case (TypeScript loses track after exhaustive switch)
  const cardType = card.type;

  switch (cardType) {
    case 'card_signal_extraction':
      return <SignalExtractionCard card={card} onAction={onAction} />;
    
    case 'card_assumption_validator':
      return <AssumptionValidatorCard card={card} onAction={onAction} />;
    
    case 'card_action_prompt':
      return <ActionPromptCard card={card} onAction={onAction} />;
    
    case 'card_research_status':
      return <ResearchStatusCard card={card} onAction={onAction} />;
    
    // Add other card types here as they're implemented
    case 'card_case_suggestion':
    case 'card_structure_preview':
    case 'card_evidence_map':
      return (
        <div className="p-4 border rounded bg-neutral-50 dark:bg-neutral-800">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Card type "{card.type}" is not yet implemented.
          </p>
        </div>
      );
    
    default:
      // Fallback for unknown card types
      return (
        <div className="p-4 border rounded bg-neutral-50 dark:bg-neutral-800">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Unknown card type: {cardType}
          </p>
        </div>
      );
  }
}
