/**
 * TypeScript types for rich message cards
 */

export type CardActionVariant = 'primary' | 'secondary' | 'danger';

export interface CardAction {
  id: string;
  label: string;
  action_type: string;
  payload: Record<string, any>;
  variant?: CardActionVariant;
}

export interface BaseCard {
  type: string;
  heading: string;
  description?: string;
  actions: CardAction[];
  metadata: Record<string, any>;
}

export interface SignalExtractionCard extends BaseCard {
  type: 'card_signal_extraction';
  signals: Array<{
    type: 'assumption' | 'question' | 'evidence' | 'claim';
    items: Array<{
      id: string;
      text: string;
      confidence: number;
      status: string;
    }>;
  }>;
}

export interface AssumptionValidatorCard extends BaseCard {
  type: 'card_assumption_validator';
  assumptions: Array<{
    id: string;
    text: string;
    status: 'pending' | 'validated' | 'refuted' | 'uncertain';
    confidence?: number;
    supporting_evidence: any[];
    contradicting_evidence: any[];
  }>;
}

export interface ActionPromptCard extends BaseCard {
  type: 'card_action_prompt';
  prompt_type: string;
  priority: 'high' | 'medium' | 'low';
}

export interface ResearchStatusCard extends BaseCard {
  type: 'card_research_status';
  agent_type: string;
  status: 'running' | 'completed' | 'failed';
  progress_steps: Array<{
    label: string;
    status: 'pending' | 'in_progress' | 'completed' | 'failed';
    details?: string;
    timestamp?: string;
  }>;
  results_preview?: string;
}

export interface CaseSuggestionCard extends BaseCard {
  type: 'card_case_suggestion';
  cases: Array<{
    id: string;
    title: string;
    relevance: number;
    snippet?: string;
  }>;
}

export interface StructurePreviewCard extends BaseCard {
  type: 'card_structure_preview';
  suggested_title: string;
  confidence: number;
  structure_type: string;
  key_elements: Array<{
    type: string;
    content: string;
  }>;
}

export interface EvidenceMapCard extends BaseCard {
  type: 'card_evidence_map';
  nodes: Array<{
    id: string;
    type: 'claim' | 'evidence';
    label: string;
  }>;
  edges: Array<{
    from: string;
    to: string;
    type: 'supports' | 'contradicts';
  }>;
}

export type RichCard = 
  | SignalExtractionCard 
  | AssumptionValidatorCard 
  | ActionPromptCard
  | ResearchStatusCard
  | CaseSuggestionCard
  | StructurePreviewCard
  | EvidenceMapCard;
