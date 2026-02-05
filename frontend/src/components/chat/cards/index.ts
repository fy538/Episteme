/**
 * Chat Card Components
 *
 * Rich cards displayed in chat messages and inline action cards.
 */

// Message cards (displayed within assistant messages)
export { CardRenderer } from './CardRenderer';
export { ActionPromptCard } from './ActionPromptCard';
export { AssumptionValidatorCard } from './AssumptionValidatorCard';
export { ResearchStatusCard } from './ResearchStatusCard';
export { SignalExtractionCard } from './SignalExtractionCard';

// Inline action cards (displayed after messages)
export { InlineActionCardRenderer } from './InlineActionCardRenderer';
export type { InlineCardActions } from './InlineActionCardRenderer';
export { SignalsCollapsedCard } from './SignalsCollapsedCard';
export { CaseCreationPromptCard } from './CaseCreationPromptCard';
export { EvidenceSuggestionCard } from './EvidenceSuggestionCard';
export { InquiryResolutionPromptCard } from './InquiryResolutionPromptCard';
export { ResearchResultsCard } from './ResearchResultsCard';
export { InquiryFocusPromptCard } from './InquiryFocusPromptCard';
