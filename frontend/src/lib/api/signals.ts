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

  // Phase 2.3: Graph queries
  async getDependencies(signalId: string): Promise<any> {
    return apiClient.get(`/signals/${signalId}/dependencies/`);
  },

  async getEvidence(signalId: string): Promise<any> {
    return apiClient.get(`/signals/${signalId}/evidence/`);
  },

  async getContradictions(signalId: string): Promise<any> {
    return apiClient.get(`/signals/${signalId}/contradictions/`);
  },

  async linkSignal(
    signalId: string,
    targetSignalId: string,
    relationship: 'depends_on' | 'contradicts'
  ): Promise<Signal> {
    return apiClient.post(`/signals/${signalId}/link/`, {
      target_signal_id: targetSignalId,
      relationship,
    });
  },
};
