/**
 * Plan API client — Investigation plan operations
 *
 * All plan endpoints are nested under /cases/{caseId}/plan/
 */

import { apiClient } from './client';
import type {
  InvestigationPlan,
  PlanVersion,
  CaseHomeData,
  CaseStage,
} from '@/lib/types/plan';

export const plansAPI = {
  // ===== Plan =====

  /** Get current investigation plan with latest version content */
  getPlan(caseId: string): Promise<InvestigationPlan> {
    return apiClient.get(`/cases/${caseId}/plan/`);
  },

  // ===== Stage =====

  /** Update the investigation stage */
  updateStage(
    caseId: string,
    stage: CaseStage,
    rationale?: string
  ): Promise<InvestigationPlan> {
    return apiClient.post(`/cases/${caseId}/plan/stage/`, {
      stage,
      rationale: rationale || '',
    });
  },

  /** Accept a proposed plan diff (creates new version) */
  acceptDiff(
    caseId: string,
    content: Record<string, unknown>,
    diffSummary: string,
    diffData?: Record<string, unknown>
  ): Promise<PlanVersion> {
    return apiClient.post(`/cases/${caseId}/plan/accept-diff/`, {
      content,
      diff_summary: diffSummary,
      diff_data: diffData || null,
    });
  },

  // ===== Granular Updates =====

  /** Update an assumption's status */
  updateAssumption(
    caseId: string,
    assumptionId: string,
    newStatus: string,
    evidenceSummary?: string
  ): Promise<PlanVersion> {
    return apiClient.patch(
      `/cases/${caseId}/plan/assumptions/${assumptionId}/`,
      {
        status: newStatus,
        evidence_summary: evidenceSummary || '',
      }
    );
  },

  /** Update a decision criterion's met status */
  updateCriterion(
    caseId: string,
    criterionId: string,
    isMet: boolean
  ): Promise<PlanVersion> {
    return apiClient.patch(
      `/cases/${caseId}/plan/criteria/${criterionId}/`,
      {
        is_met: isMet,
      }
    );
  },

  // ===== Plan Generation =====

  /** Generate a plan for a case that doesn't have one */
  generatePlan(caseId: string): Promise<InvestigationPlan> {
    return apiClient.post(`/cases/${caseId}/generate-plan/`, {});
  },

  // ===== Case Home (Aggregated) =====

  /** Get everything needed to render the case home in one call */
  getCaseHome(caseId: string): Promise<CaseHomeData> {
    return apiClient.get(`/cases/${caseId}/home/`);
  },
};
