/**
 * Inquiries API functions
 */

import { apiClient } from './client';
import type { Inquiry } from '../types/case';

export const inquiriesAPI = {
  async promoteSignal(signalId: string, title?: string): Promise<{ signal: any; inquiry_id: string }> {
    return apiClient.post(`/signals/${signalId}/promote_to_inquiry/`, {
      title,
      elevation_reason: 'user_created'
    });
  },

  async getByCase(caseId: string): Promise<Inquiry[]> {
    const response = await apiClient.get<{ results: Inquiry[] }>(
      `/inquiries/?case=${caseId}`
    );
    return response.results || [];
  },

  async getInquiry(inquiryId: string): Promise<Inquiry> {
    return apiClient.get<Inquiry>(`/inquiries/${inquiryId}/`);
  },

  async create(data: {
    case: string;
    title: string;
    description?: string;
    origin_text?: string;
    origin_document?: string;
    status: string;
  }): Promise<Inquiry> {
    return apiClient.post('/inquiries/', data);
  },

  async resolve(inquiryId: string, conclusion: string): Promise<Inquiry> {
    return apiClient.post(`/inquiries/${inquiryId}/resolve/`, { conclusion });
  },

  async update(inquiryId: string, data: Partial<Inquiry>): Promise<Inquiry> {
    return apiClient.patch<Inquiry>(`/inquiries/${inquiryId}/`, data);
  },

  async delete(inquiryId: string): Promise<void> {
    return apiClient.delete(`/inquiries/${inquiryId}/`);
  },

  async generateTitle(text: string): Promise<{ title: string }> {
    return apiClient.post('/inquiries/generate_title/', { text });
  },

  async generateBriefUpdate(
    inquiryId: string,
    briefId: string
  ): Promise<{
    updated_content: string;
    changes: Array<any>;
    summary: string;
  }> {
    return apiClient.post(`/inquiries/${inquiryId}/generate_brief_update/`, {
      brief_id: briefId,
    });
  },

  async getDashboard(caseId: string): Promise<any> {
    return apiClient.get(`/inquiries/dashboard/?case_id=${caseId}`);
  },

  async getEvidenceSummary(inquiryId: string): Promise<any> {
    return apiClient.get(`/inquiries/${inquiryId}/evidence_summary/`);
  },

  async startInvestigation(inquiryId: string): Promise<any> {
    return apiClient.post(`/inquiries/${inquiryId}/start_investigation/`, {});
  },

  async createFromAssumption(params: {
    caseId: string;
    assumptionText: string;
    autoGenerateTitle?: boolean;
  }): Promise<Inquiry> {
    return apiClient.post('/inquiries/create_from_assumption/', {
      case_id: params.caseId,
      assumption_text: params.assumptionText,
      auto_generate_title: params.autoGenerateTitle ?? true,
    });
  },
};
