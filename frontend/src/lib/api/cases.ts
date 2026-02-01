/**
 * Cases API functions
 */

import { apiClient } from './client';
import type { Case, CaseDocument } from '../types/case';

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
};
