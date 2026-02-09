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
  // User-stated epistemic confidence
  user_confidence?: number; // 0-100
  user_confidence_updated_at?: string;
  what_would_change_mind?: string;
  what_changed_mind_response?: 'updated_view' | 'proceeding_anyway' | 'not_materialized' | '';
  what_changed_mind_response_at?: string;
  // Premortem
  premortem_text?: string;
  premortem_at?: string;
  // Decision Frame fields
  decision_question?: string;
  constraints?: Constraint[];
  success_criteria?: SuccessCriterion[];
  stakeholders?: Stakeholder[];
  // Per-case configuration
  intelligence_config?: {
    auto_validate?: boolean;
    background_research?: boolean;
    gap_detection?: boolean;
  };
  investigation_preferences?: {
    rigor?: 'light' | 'standard' | 'thorough';
    evidence_threshold?: 'low' | 'medium' | 'high';
    disable_locks?: boolean;
  };
  // Relationships
  main_brief?: string;
  linked_thread?: string;
  user: string;
  project?: string;
  created_at: string;
  updated_at: string;
  // Active skills (from CaseSerializer.active_skills_summary)
  active_skills_summary?: Array<{ id: string; name: string; domain: string }>;
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
  created_at: string;
  updated_at: string;
}

export interface WorkingDocument {
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

// Readiness Checklist types
export interface ReadinessChecklistItem {
  id: string;
  description: string;
  is_required: boolean;
  is_complete: boolean;
  completed_at?: string;
  linked_inquiry?: string;
  linked_assumption?: string;
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
}

// ── Intelligent Brief Types ─────────────────────────────────────

export type SectionType = 'decision_frame' | 'inquiry_brief' | 'synthesis' | 'trade_offs' | 'recommendation' | 'custom';
export type GroundingStatus = 'empty' | 'weak' | 'moderate' | 'strong' | 'conflicted';
export type AnnotationType = 'tension' | 'blind_spot' | 'ungrounded' | 'evidence_desert' | 'well_grounded' | 'stale' | 'circular' | 'low_credibility';
export type AnnotationPriority = 'blocking' | 'important' | 'info';

export interface BriefAnnotation {
  id: string;
  annotation_type: AnnotationType;
  description: string;
  priority: AnnotationPriority;
  source_ids: string[];
  source_inquiry?: string;
  created_at: string;
  dismissed_at?: string;
  resolved_at?: string;
  resolved_by?: string;
}

export interface BriefSection {
  id: string;
  section_id: string;
  heading: string;
  order: number;
  section_type: SectionType;
  inquiry?: string;
  inquiry_title?: string;
  parent_section?: string;
  depth: number;
  created_by: 'system' | 'user' | 'agent';
  is_linked: boolean;
  grounding_status: GroundingStatus;
  grounding_data: {
    evidence_count?: number;
    supporting?: number;
    contradicting?: number;
    neutral?: number;
    unvalidated_assumptions?: number;
    tensions_count?: number;
    confidence_avg?: number | null;
  };
  user_confidence?: number;
  user_confidence_at?: string;
  annotations: BriefAnnotation[];
  is_locked: boolean;
  lock_reason: string;
  is_collapsed: boolean;
  subsections: BriefSection[];
  content_preview?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BriefSectionsResponse {
  sections: BriefSection[];
  brief_id: string;
}

export interface BriefOverview {
  sections: Array<{
    id: string;
    section_id: string;
    heading: string;
    section_type: SectionType;
    grounding_status: GroundingStatus;
    is_locked: boolean;
    is_linked: boolean;
    annotation_counts: {
      blocking: number;
      important: number;
      info: number;
    };
    subsection_count: number;
  }>;
  overall_grounding: {
    score: number;
    total_sections: number;
    status_counts?: Record<string, number>;
  };
}

export interface EvolveSectionChange {
  id: string;
  heading: string;
  old_status: string;
  new_status: string;
}

export interface EvolveAnnotationChange {
  id: string;
  type: AnnotationType;
  section_heading: string;
}

export interface EvolveDiff {
  section_changes: EvolveSectionChange[];
  new_annotations: EvolveAnnotationChange[];
  resolved_annotations: EvolveAnnotationChange[];
  readiness_created?: number;
  readiness_auto_completed?: number;
}

export interface EvolveBriefResponse {
  status: string;
  updated_sections: number;
  new_annotations: number;
  resolved_annotations: number;
  readiness_created?: number;
  readiness_auto_completed?: number;
  diff?: EvolveDiff;
}

export interface CreateBriefSectionData {
  heading: string;
  section_type?: SectionType;
  order?: number;
  parent_section?: string;
  inquiry?: string;
  after_section_id?: string;
}

export interface UpdateBriefSectionData {
  heading?: string;
  order?: number;
  section_type?: SectionType;
  inquiry?: string | null;
  parent_section?: string | null;
  is_collapsed?: boolean;
}

export interface ScaffoldResult {
  case: Case;
  brief: WorkingDocument;
  inquiries: Inquiry[];
  sections: BriefSection[];
}

// ── Health & Judgment types ─────────────────────────────────────

export interface CaseHealthMetrics {
  staleness: { stale: boolean; days_since_activity: number | null };
  imbalance: { imbalanced: boolean; inquiry_events: number; synthesis_events: number };
  confidence_plateau: { plateau: boolean; evidence_events: number; confidence_events: number };
  momentum: { trend: 'accelerating' | 'steady' | 'decelerating' | 'stalled'; this_week: number; last_week: number };
}

export interface SectionJudgmentSection {
  section_id: string;
  heading: string;
  section_type: string;
  grounding_status: string;
  grounding_strength: number;
  user_confidence: number | null;
  evidence_count: number;
  tensions_count: number;
}

export interface SectionJudgmentMismatch {
  section_id: string;
  heading: string;
  type: 'overconfident' | 'underconfident';
  description: string;
  user_confidence: number;
  grounding_status: string;
}

export interface SectionJudgmentSummary {
  sections: SectionJudgmentSection[];
  mismatches: SectionJudgmentMismatch[];
  rated_count: number;
  total_count: number;
}

