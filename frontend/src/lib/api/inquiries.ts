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
};
