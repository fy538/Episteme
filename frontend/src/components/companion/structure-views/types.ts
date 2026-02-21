/**
 * Shared types for structure view components.
 *
 * These interfaces replace the pervasive `Record<string, any>` with
 * concrete shapes matching the LLM-generated structure content.
 */

// ===== Assumption Surface =====

export type AssumptionSource = 'stated' | 'inferred' | 'implicit';
export type AssumptionRisk = 'high' | 'medium' | 'low';

export interface SurfacedAssumption {
  text: string;
  source?: AssumptionSource;
  risk?: AssumptionRisk;
}

export interface AssumptionSurfaceContent {
  context?: string;
  assumptions?: SurfacedAssumption[];
}

// ===== Angle Map =====

export type AngleStatus = 'opened' | 'touched' | 'not_yet_discussed';

export interface Angle {
  label: string;
  status?: AngleStatus;
  source?: string;
}

export interface AngleMapContent {
  topic?: string;
  angles?: Angle[];
}

// ===== Decision Tree =====

export type BranchStatus = 'viable' | 'preferred' | 'exploring' | 'eliminated';

export interface DecisionBranch {
  label: string;
  status?: BranchStatus;
  detail?: string;
  reason?: string;
}

export interface DecisionTreeContent {
  question?: string;
  branches?: DecisionBranch[];
}

// ===== Checklist =====

export type CheckItemStatus = 'done' | 'pending' | 'blocked' | 'not_applicable';

export interface ChecklistItem {
  text: string;
  status?: CheckItemStatus;
  detail?: string;
}

export interface ChecklistContent {
  title?: string;
  items?: ChecklistItem[];
}

// ===== Comparison =====

export interface ComparisonCriterion {
  criterion: string;
  values?: Record<string, string>;
  winner?: string;
}

export interface ComparisonContent {
  comparing?: string;
  options?: string[];
  criteria?: ComparisonCriterion[];
}

// ===== Exploration Map =====

export type ExplorationStatus = 'explored' | 'partially_explored' | 'unexplored';

export interface ExplorationArea {
  label: string;
  status?: ExplorationStatus;
  summary?: string;
}

export interface ExplorationMapContent {
  center?: string;
  areas?: ExplorationArea[];
}

// ===== Pros & Cons =====

export interface ProsConsItem {
  point: string;
}

export interface ProsConsContent {
  subject?: string;
  pros?: Array<string | ProsConsItem>;
  cons?: Array<string | ProsConsItem>;
}

// ===== Constraint List =====

export interface Constraint {
  text: string;
  impact?: string;
}

export interface ConstraintListContent {
  topic?: string;
  constraints?: Constraint[];
}

// ===== Flow =====

export type FlowStepStatus = 'understood' | 'blocked' | 'pending';

export interface FlowStep {
  label: string;
  status?: FlowStepStatus;
  detail?: string;
}

export interface FlowContent {
  title?: string;
  steps?: FlowStep[];
}

// ===== Concept Map =====

export interface ConceptNode {
  label: string;
  description?: string;
}

export interface ConceptConnection {
  from: string;
  to: string;
  relation: string;
}

export interface ConceptMapContent {
  title?: string;
  nodes?: ConceptNode[];
  connections?: ConceptConnection[];
}

// ===== Common =====

/** Props shared by all structure view components */
export interface StructureViewProps<T = Record<string, unknown>> {
  content: T;
}
