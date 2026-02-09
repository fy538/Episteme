/**
 * Investigation Plan Types
 *
 * The Plan is a first-class versioned object (1:1 with Case).
 * It holds the investigation phases, assumptions, decision criteria,
 * and stage. Each change creates an immutable PlanVersion snapshot.
 */

// ===== Enums =====

export type CaseStage = 'exploring' | 'investigating' | 'synthesizing' | 'ready';

export type AssumptionStatus = 'untested' | 'confirmed' | 'challenged' | 'refuted';

export type RiskLevel = 'low' | 'medium' | 'high';

// ===== Plan Content (inside PlanVersion.content) =====

export interface PlanPhase {
  id: string;
  title: string;
  description: string;
  order: number;
  inquiry_ids: string[];
}

export interface PlanAssumption {
  id: string;
  assumption_id: string | null;  // Unique identifier for the assumption
  text: string;
  status: AssumptionStatus;
  test_strategy: string;
  evidence_summary: string;
  risk_level: RiskLevel;
}

export interface DecisionCriterion {
  id: string;
  text: string;
  is_met: boolean;
  linked_inquiry_id: string | null;
}

export interface PlanContent {
  phases: PlanPhase[];
  assumptions: PlanAssumption[];
  decision_criteria: DecisionCriterion[];
  stage_rationale: string;
}

// ===== API Response Types =====

export interface InvestigationPlan {
  id: string;
  case: string;
  stage: CaseStage;
  current_version: number;
  position_statement: string;
  current_content: PlanContent | null;
  created_at: string;
  updated_at: string;
}

export interface PlanVersion {
  id: string;
  version_number: number;
  content: PlanContent;
  diff_summary: string;
  diff_data: Record<string, unknown> | null;
  created_by: string;
  created_at: string;
}

// ===== Case Home Aggregated Response =====

export interface CaseHomeInquiry {
  id: string;
  title: string;
  status: string;
  priority: number;
  sequence_index: number;
  evidence_count: number;
  latest_evidence_text: string | null;
  latest_evidence_at: string | null;
  conclusion: string | null;
}

export interface CaseHomeEvent {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  timestamp: string;
  actor_type: string;
}

/** Subset of Case fields returned by the home() endpoint */
export interface CaseHomeCaseSummary {
  id: string;
  title: string;
  status: string;
  position?: string;
  premortem_text?: string;
  premortem_at?: string;
  what_would_change_mind?: string;
  what_changed_mind_response?: string;
  what_changed_mind_response_at?: string;
  user_confidence?: number;
  user_confidence_updated_at?: string;
}

export interface CaseHomeData {
  case: CaseHomeCaseSummary;
  plan: InvestigationPlan | null;
  inquiries: CaseHomeInquiry[];
  activity: {
    recent_events: CaseHomeEvent[];
  };
}
