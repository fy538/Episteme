/**
 * TypeScript types for cases and inquiries
 */

export interface Constraint {
  type: string;
  description: string;
}

export interface SuccessCriterion {
  criterion: string;
  measurable?: string;
  target?: string;
}

export interface Stakeholder {
  name: string;
  interest: string;
  influence: 'low' | 'medium' | 'high';
}

export interface Case {
  id: string;
  title: string;
  status: 'draft' | 'active' | 'archived';
  stakes: 'low' | 'medium' | 'high';
  position: string;
  confidence?: number; // DEPRECATED - use user_confidence
  // User-stated epistemic confidence
  user_confidence?: number; // 0-100
  user_confidence_updated_at?: string;
  what_would_change_mind?: string;
  // Decision Frame fields
  decision_question?: string;
  constraints?: Constraint[];
  success_criteria?: SuccessCriterion[];
  stakeholders?: Stakeholder[];
  // Relationships
  main_brief?: string;
  linked_thread?: string;
  user: string;
  project?: string;
  created_at: string;
  updated_at: string;
}

export interface CaseAnalysisResponse {
  should_suggest: boolean;
  suggested_title: string;
  suggested_question: string;
  position_draft: string;
  key_questions: string[];
  assumptions: string[];
  constraints: Constraint[];
  success_criteria: SuccessCriterion[];
  signals_summary: {
    assumptions: number;
    questions: number;
    claims: number;
    constraints: number;
    goals: number;
  };
  confidence: number;
  correlation_id: string;
  message_count: number;
}

export interface Inquiry {
  id: string;
  case: string;
  title: string;
  description: string;
  elevation_reason: string;
  status: 'open' | 'investigating' | 'resolved' | 'archived';
  conclusion: string;
  conclusion_confidence?: number;
  resolved_at?: string;
  priority: number;
  sequence_index: number;
  brief?: string;
  // Dependency fields
  blocked_by?: string[];
  blocks?: string[];
  // Optional computed fields
  related_signals_count?: number;
  created_at: string;
  updated_at: string;
}

export interface CaseDocument {
  id: string;
  case: string;
  inquiry?: string;
  document_type: 'case_brief' | 'inquiry_brief' | 'research' | 'debate' | 'critique' | 'source' | 'notes';
  title: string;
  content_markdown: string;
  edit_friction: 'low' | 'high' | 'readonly';
  ai_structure: Record<string, any>;
  highlighted_assumptions?: any[];
  generated_by_ai: boolean;
  agent_type: string;
  times_cited: number;
  can_edit: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

// Evidence Landscape types (replaces computed confidence)
export interface EvidenceLandscape {
  evidence: {
    supporting: number;
    contradicting: number;
    neutral: number;
  };
  assumptions: {
    total: number;
    validated: number;
    untested: number;
    untested_list: Array<{
      id: string;
      text: string;
      inquiry_id?: string;
    }>;
  };
  inquiries: {
    total: number;
    open: number;
    investigating: number;
    resolved: number;
  };
  unlinked_claims: Array<{
    text: string;
    location: string;
  }>;
}

// Readiness Checklist types
export interface ReadinessChecklistItem {
  id: string;
  description: string;
  is_required: boolean;
  is_complete: boolean;
  completed_at?: string;
  linked_inquiry?: string;
  linked_assumption_signal?: string;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface ReadinessChecklistResponse {
  items: ReadinessChecklistItem[];
  progress: {
    completed: number;
    required: number;
    required_completed: number;
    total: number;
  };
}

// Blind spot prompts (from gap analysis)
export interface BlindSpotPrompt {
  type: 'alternative' | 'assumption' | 'evidence_gap';
  text: string;
  action: 'create_inquiry' | 'investigate' | 'add_evidence';
  signal_id?: string;
}
