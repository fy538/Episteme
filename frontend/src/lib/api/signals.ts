/**
 * Signals API functions
 */

import { apiClient } from './client';
import type { Signal, InquirySuggestion } from '../types/signal';

export const signalsAPI = {
  async getByThread(threadId: string): Promise<Signal[]> {
    const response = await apiClient.get<{ results: Signal[] }>(
      `/signals/?thread_id=${threadId}`
    );
    return response.results || [];
  },

  async getByCase(caseId: string): Promise<Signal[]> {
    const response = await apiClient.get<{ results: Signal[] }>(
      `/signals/?case_id=${caseId}`
    );
    return response.results || [];
  },

  async getPromotionSuggestions(caseId: string): Promise<InquirySuggestion[]> {
    return apiClient.get<InquirySuggestion[]>(
      `/signals/promotion_suggestions/?case_id=${caseId}`
    );
  },

  async dismissSignal(signalId: string): Promise<Signal> {
    return apiClient.post<Signal>(`/signals/${signalId}/dismiss/`, {});
  },

  // Phase 1: Signal actions
  async confirm(signalId: string): Promise<Signal> {
    return apiClient.post<Signal>(`/signals/${signalId}/confirm/`, {});
  },

  async reject(signalId: string): Promise<Signal> {
    return apiClient.post<Signal>(`/signals/${signalId}/reject/`, {});
  },

  async edit(signalId: string, text: string): Promise<Signal> {
    return apiClient.patch<Signal>(`/signals/${signalId}/edit/`, { text });
  },

  /**
   * Mark user-selected text as an assumption signal.
   */
  async markAssumption(text: string, caseId: string): Promise<Signal> {
    return apiClient.post<Signal>('/signals/mark-assumption/', {
      text,
      case_id: caseId,
    });
  },

};
