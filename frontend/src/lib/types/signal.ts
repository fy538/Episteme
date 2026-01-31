/**
 * TypeScript types for signals and inquiries
 */

export type SignalType = 
  | 'DecisionIntent'
  | 'Claim'
  | 'Goal'
  | 'Constraint'
  | 'Assumption'
  | 'Question'
  | 'EvidenceMention';

export interface Signal {
  id: string;
  type: SignalType;
  status: 'suggested' | 'confirmed' | 'rejected';
  text: string;
  normalized_text: string;
  confidence: number;
  case?: string;
  thread: string;
  inquiry?: string;
  dismissed_at?: string;
  created_at: string;
}

export interface InquirySuggestion {
  signal: Signal;
  reason: string;
  suggested_title: string;
  similar_count: number;
}
