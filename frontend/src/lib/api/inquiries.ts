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
};
