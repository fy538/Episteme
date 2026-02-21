/**
 * Types for the project home concierge page.
 *
 * The concierge endpoint returns card signals; the frontend
 * card selection algorithm picks the best 1-3 cards to display.
 */

// ─── API Response ──────────────────────────────────

export interface DecisionAtRisk {
  case_id: string;
  case_title: string;
  decision_text: string;
  risk_type: 'overdue_outcome' | 'contradicted_assumption';
  days_overdue: number;
  outcome_check_date: string;
}

export interface CaseAttention {
  case_id: string;
  case_title: string;
  attention_type: 'untested_load_bearing' | 'blocking_tension';
  detail: string;
  stage: string;
}

export interface RecentActiveCase {
  case_id: string;
  case_title: string;
  last_activity: string;
  stage: string;
  progress_summary: string;
}

export interface OrientationShift {
  has_shift: boolean;
  hierarchy_status: 'none' | 'building' | 'ready' | 'failed';
}

export interface WorthExploringPrompt {
  insight_id: string;
  title: string;
  insight_type: string;
  confidence: number;
}

export interface ConciergeData {
  project_id: string;
  has_documents: boolean;
  has_cases: boolean;
  document_count: number;
  decisions_at_risk: DecisionAtRisk[];
  cases_needing_attention: CaseAttention[];
  recent_active_cases: RecentActiveCase[];
  orientation_shift: OrientationShift | null;
  worth_exploring: WorthExploringPrompt[];
}

// ─── Card Types ────────────────────────────────────

export type ConciergeCardType =
  | 'decision_at_risk'
  | 'worth_exploring'
  | 'case_needs_attention'
  | 'resume_work'
  | 'orientation_shift'
  | 'get_started';

export type ConciergeCardVariant = 'warning' | 'accent' | 'info' | 'neutral' | 'action';

export interface ConciergeCardAction {
  label: string;
  href?: string;
  onClick?: () => void;
}

export interface ConciergeCard {
  type: ConciergeCardType;
  priority: number;
  title: string;
  subtitle: string;
  href: string;
  caseId?: string;
  variant: ConciergeCardVariant;
  actions?: ConciergeCardAction[];
}
