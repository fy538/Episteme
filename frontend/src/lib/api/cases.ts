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
  BriefSection,
  BriefSectionsResponse,
  BriefOverview,
  EvolveBriefResponse,
  CreateBriefSectionData,
  UpdateBriefSectionData,
  ScaffoldResult,
  SectionJudgmentSummary,
} from '../types/case';

// Re-export types that were previously defined in this file
export type { CaseHealthMetrics, SectionJudgmentSummary } from '../types/case';
export type { SectionJudgmentSection, SectionJudgmentMismatch } from '../types/case';

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
   * Get evidence landscape (counts, not scores)
   */
  async getEvidenceLandscape(caseId: string): Promise<EvidenceLandscape> {
    return apiClient.get(`/cases/${caseId}/evidence-landscape/`);
  },

  /**
   * Save user's premortem text
   */
  async savePremortem(caseId: string, text: string): Promise<{ premortem_text: string; premortem_at: string }> {
    return apiClient.patch(`/cases/${caseId}/premortem/`, { premortem_text: text });
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

  // ── Intelligent Brief ─────────────────────────────────────────

  /**
   * Get all brief sections with annotations
   */
  async getBriefSections(caseId: string): Promise<BriefSectionsResponse> {
    return apiClient.get(`/cases/${caseId}/brief-sections/`);
  },

  /**
   * Create a new brief section
   */
  async createBriefSection(caseId: string, data: CreateBriefSectionData): Promise<BriefSection> {
    return apiClient.post(`/cases/${caseId}/brief-sections/`, data);
  },

  /**
   * Update a brief section
   */
  async updateBriefSection(
    caseId: string,
    sectionId: string,
    data: UpdateBriefSectionData
  ): Promise<BriefSection> {
    return apiClient.patch(`/cases/${caseId}/brief-sections/${sectionId}/`, data);
  },

  /**
   * Delete a brief section
   */
  async deleteBriefSection(caseId: string, sectionId: string): Promise<void> {
    return apiClient.delete(`/cases/${caseId}/brief-sections/${sectionId}/`);
  },

  /**
   * Bulk reorder brief sections
   */
  async reorderBriefSections(
    caseId: string,
    sections: Array<{ id: string; order: number }>
  ): Promise<void> {
    return apiClient.post(`/cases/${caseId}/brief-sections/reorder/`, { sections });
  },

  /**
   * Link a brief section to an inquiry
   */
  async linkSectionToInquiry(
    caseId: string,
    sectionId: string,
    inquiryId: string
  ): Promise<BriefSection> {
    return apiClient.post(
      `/cases/${caseId}/brief-sections/${sectionId}/link-inquiry/`,
      { inquiry_id: inquiryId }
    );
  },

  /**
   * Unlink a brief section from its inquiry
   */
  async unlinkSectionFromInquiry(caseId: string, sectionId: string): Promise<BriefSection> {
    return apiClient.post(`/cases/${caseId}/brief-sections/${sectionId}/unlink-inquiry/`, {});
  },

  /**
   * Dismiss an annotation on a brief section
   */
  async dismissAnnotation(
    caseId: string,
    sectionId: string,
    annotationId: string
  ): Promise<void> {
    return apiClient.post(
      `/cases/${caseId}/brief-sections/${sectionId}/dismiss-annotation/${annotationId}/`,
      {}
    );
  },

  /**
   * Trigger brief grounding recomputation
   */
  async evolveBrief(caseId: string): Promise<EvolveBriefResponse> {
    return apiClient.post(`/cases/${caseId}/evolve-brief/`, {});
  },

  /**
   * Get lightweight brief overview
   */
  async getBriefOverview(caseId: string): Promise<BriefOverview> {
    return apiClient.get(`/cases/${caseId}/brief-overview/`);
  },

  /**
   * Scaffold a case from a chat thread
   */
  async scaffoldFromChat(projectId: string, threadId: string): Promise<ScaffoldResult> {
    return apiClient.post('/cases/scaffold/', {
      project_id: projectId,
      thread_id: threadId,
      mode: 'chat',
    });
  },

  /**
   * Scaffold a minimal case.
   *
   * Optionally pass a skill pack slug or individual skill ID to scaffold
   * with domain-specific brief sections and auto-activate skills.
   */
  async scaffoldMinimal(
    projectId: string,
    title: string,
    decisionQuestion?: string,
    options?: { packSlug?: string; skillId?: string }
  ): Promise<ScaffoldResult> {
    return apiClient.post('/cases/scaffold/', {
      project_id: projectId,
      title,
      decision_question: decisionQuestion,
      mode: 'minimal',
      ...(options?.packSlug ? { pack_slug: options.packSlug } : {}),
      ...(options?.skillId ? { skill_id: options.skillId } : {}),
    });
  },

  /**
   * Save user's response to the "what would change your mind" resurface prompt.
   */
  async saveWhatChangedMindResponse(
    caseId: string,
    response: 'updated_view' | 'proceeding_anyway' | 'not_materialized'
  ): Promise<{ what_changed_mind_response: string; what_changed_mind_response_at: string }> {
    return apiClient.patch(`/cases/${caseId}/what-changed-mind-response/`, { response });
  },

  /**
   * Get synthesis summary comparing user judgment vs structural grounding
   */
  async getSectionJudgmentSummary(caseId: string): Promise<SectionJudgmentSummary> {
    return apiClient.get(`/cases/${caseId}/section-judgment-summary/`);
  },

  /**
   * Export case brief as markdown (client-side assembly)
   *
   * Downloads the brief and plan data and assembles a
   * shareable markdown document locally.
   */
  async exportBriefMarkdown(caseId: string): Promise<string> {
    const [caseData, sections, home] = await Promise.all([
      this.getCase(caseId),
      this.getBriefSections(caseId).catch(() => ({ sections: [] })),
      apiClient.get(`/cases/${caseId}/home/`).catch(() => null) as Promise<any>,
    ]);

    const lines: string[] = [];
    lines.push(`# ${caseData.title}`);
    lines.push('');
    if (caseData.decision_question) {
      lines.push(`**Decision:** ${caseData.decision_question}`);
      lines.push('');
    }

    // Plan stage
    if (home?.plan?.stage) {
      lines.push(`**Stage:** ${home.plan.stage}`);
      lines.push('');
    }

    // Position statement
    if (home?.plan?.position_statement) {
      lines.push(`> ${home.plan.position_statement}`);
      lines.push('');
    }

    // Brief sections
    const sectionList = (sections as any)?.sections ?? [];
    if (sectionList.length > 0) {
      lines.push('## Brief');
      lines.push('');
      for (const section of sectionList) {
        lines.push(`### ${section.heading}`);
        lines.push('');
        lines.push(section.content || '');
        lines.push('');
      }
    }

    // Assumptions
    const assumptions = home?.plan?.current_content?.assumptions ?? [];
    if (assumptions.length > 0) {
      lines.push('## Assumptions');
      lines.push('');
      for (const a of assumptions) {
        lines.push(`- **[${a.status.toUpperCase()}]** ${a.text}`);
        if (a.evidence_summary) {
          lines.push(`  - Evidence: ${a.evidence_summary}`);
        }
      }
      lines.push('');
    }

    // Decision criteria
    const criteria = home?.plan?.current_content?.decision_criteria ?? [];
    if (criteria.length > 0) {
      lines.push('## Decision Criteria');
      lines.push('');
      for (const c of criteria) {
        lines.push(`- [${c.is_met ? 'x' : ' '}] ${c.text}`);
      }
      lines.push('');
    }

    lines.push('---');
    lines.push(`*Exported from Episteme on ${new Date().toLocaleDateString()}*`);

    return lines.join('\n');
  },

  /**
   * Export case as structured JSON (full reasoning graph IR)
   */
  async exportJSON(caseId: string): Promise<Record<string, unknown>> {
    return apiClient.get(`/cases/${caseId}/export/?type=full`);
  },
};

