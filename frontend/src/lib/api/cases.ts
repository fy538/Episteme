/**
 * Cases API functions
 */

import { apiClient } from './client';
import type {
  Case,
  CaseDocument,
  CaseAnalysisResponse,
  Constraint,
  SuccessCriterion,
  Stakeholder,
  EvidenceLandscape,
  ReadinessChecklistItem,
  ReadinessChecklistResponse,
  BlindSpotPrompt,
} from '../types/case';

interface CreateCaseResponse {
  case: Case;
  main_brief: CaseDocument;
}

export const casesAPI = {
  async createCase(title: string, projectId?: string): Promise<CreateCaseResponse> {
    return apiClient.post<CreateCaseResponse>('/cases/', {
      title,
      project_id: projectId,
      position: '',
    });
  },

  async getCase(caseId: string): Promise<Case> {
    return apiClient.get<Case>(`/cases/${caseId}/`);
  },

  async listCases(): Promise<Case[]> {
    const response = await apiClient.get<{ results: Case[] }>('/cases/');
    return response.results || [];
  },

  async updateCase(caseId: string, data: Partial<Case>): Promise<Case> {
    return apiClient.patch<Case>(`/cases/${caseId}/`, data);
  },

  async deleteCase(caseId: string): Promise<void> {
    return apiClient.delete(`/cases/${caseId}/`);
  },

  async getCaseDocuments(caseId: string): Promise<CaseDocument[]> {
    const response = await apiClient.get<{ results: CaseDocument[] }>(
      `/cases/documents/?case=${caseId}`
    );
    return response.results || [];
  },

  async getOnboarding(caseId: string): Promise<any> {
    return apiClient.get(`/cases/${caseId}/onboarding/`);
  },

  /**
   * Generate a brief outline for a case
   */
  async generateBriefOutline(caseId: string): Promise<{ outline: string; case_id: string }> {
    return apiClient.post<{ outline: string; case_id: string }>(
      `/cases/${caseId}/generate-brief-outline/`,
      {}
    );
  },

  /**
   * Update decision frame fields
   */
  async updateDecisionFrame(
    caseId: string,
    data: {
      decision_question?: string;
      constraints?: Constraint[];
      success_criteria?: SuccessCriterion[];
      stakeholders?: Stakeholder[];
    }
  ): Promise<Case> {
    return apiClient.patch<Case>(`/cases/${caseId}/`, data);
  },

  /**
   * Get AI suggestions for inquiries
   */
  async suggestInquiries(caseId: string): Promise<Array<{
    title: string;
    description: string;
    reason: string;
    priority: number;
  }>> {
    return apiClient.post(`/cases/${caseId}/suggest-inquiries/`, {});
  },

  /**
   * Suggest evidence sources for an inquiry
   */
  async suggestEvidenceSources(caseId: string, inquiryId: string): Promise<Array<{
    inquiry_id: string;
    suggestion: string;
    source_type: string;
    why_helpful: string;
    how_to_find: string;
  }>> {
    return apiClient.post(`/cases/${caseId}/suggest-evidence-sources/`, {
      inquiry_id: inquiryId,
    });
  },

  /**
   * Get evidence landscape (counts, not scores)
   */
  async getEvidenceLandscape(caseId: string): Promise<EvidenceLandscape> {
    return apiClient.get(`/cases/${caseId}/evidence-landscape/`);
  },

  /**
   * Set user's self-assessed confidence
   */
  async setUserConfidence(
    caseId: string,
    confidence: number,
    whatWouldChangeMind?: string
  ): Promise<{
    user_confidence: number;
    user_confidence_updated_at: string;
    what_would_change_mind: string;
  }> {
    return apiClient.patch(`/cases/${caseId}/user-confidence/`, {
      user_confidence: confidence,
      what_would_change_mind: whatWouldChangeMind,
    });
  },

  /**
   * Get readiness checklist items
   */
  async getReadinessChecklist(caseId: string): Promise<ReadinessChecklistResponse> {
    return apiClient.get(`/cases/${caseId}/readiness-checklist/`);
  },

  /**
   * Add a checklist item
   */
  async addChecklistItem(
    caseId: string,
    description: string,
    isRequired = true
  ): Promise<ReadinessChecklistItem> {
    return apiClient.post(`/cases/${caseId}/readiness-checklist/`, {
      description,
      is_required: isRequired,
    });
  },

  /**
   * Update a checklist item
   */
  async updateChecklistItem(
    caseId: string,
    itemId: string,
    updates: Partial<{
      description: string;
      is_required: boolean;
      is_complete: boolean;
      order: number;
    }>
  ): Promise<ReadinessChecklistItem> {
    return apiClient.patch(`/cases/${caseId}/readiness-checklist/${itemId}/`, updates);
  },

  /**
   * Delete a checklist item
   */
  async deleteChecklistItem(caseId: string, itemId: string): Promise<void> {
    return apiClient.delete(`/cases/${caseId}/readiness-checklist/${itemId}/`);
  },

  /**
   * Initialize default checklist items
   */
  async initDefaultChecklist(caseId: string): Promise<{
    message: string;
    items: ReadinessChecklistItem[];
  }> {
    return apiClient.post(`/cases/${caseId}/readiness-checklist/init-defaults/`, {});
  },

  /**
   * Get blind spot prompts (from gap analysis)
   */
  async getBlindSpotPrompts(caseId: string): Promise<{
    prompts: BlindSpotPrompt[];
    missing_perspectives: string[];
    unvalidated_assumptions: string[];
    contradictions: string[];
    evidence_gaps: string[];
    recommendations: string[];
  }> {
    return apiClient.post(`/cases/${caseId}/analyze-gaps/`, {});
  },
};
