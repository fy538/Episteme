/**
 * TypeScript types for case extraction pipeline and analysis results.
 */

export type ExtractionPhase =
  | 'none'
  | 'pending'
  | 'retrieving'
  | 'extracting'
  | 'integrating'
  | 'analyzing'
  | 'complete'
  | 'failed';

export interface ExtractionStatus {
  extraction_status: ExtractionPhase;
  extraction_started_at?: string;
  extraction_completed_at?: string;
  extraction_error?: string;
  extraction_result?: ExtractionResult;
  chunks_retrieved?: number;
}

export interface ExtractionResult {
  node_count: number;
  edge_count: number;
  chunk_count: number;
}

export interface BlindSpot {
  description: string;
  severity: 'high' | 'medium' | 'low';
  suggested_action: string;
  relevant_theme_ids?: string[];
}

export interface AssumptionAssessment {
  node_id: string;
  content: string;
  load_bearing: boolean;
  supporting_evidence: number;
  contradicting_evidence: number;
  testable: boolean;
  implicit: boolean;
}

export interface TensionSummary {
  node_id: string;
  content: string;
  status: string;
  involved_nodes: string[];
}

export interface EvidenceCoverage {
  total_claims: number;
  supported_claims: number;
  unsupported_claims: Array<{ node_id: string; content: string }>;
  total_evidence: number;
  evidence_per_claim: number;
}

export interface DecisionReadiness {
  ready: boolean;
  confidence: number;
  issues: string[];
}

export interface CaseAnalysis {
  blind_spots: BlindSpot[];
  assumption_assessment: AssumptionAssessment[];
  key_tensions: TensionSummary[];
  evidence_coverage: EvidenceCoverage;
  readiness: DecisionReadiness;
  assumption_count: number;
  tension_count: number;
}
