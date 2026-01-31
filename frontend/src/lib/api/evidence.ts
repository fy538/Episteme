/**
 * Evidence API client
 * 
 * For interacting with evidence extracted from documents.
 */

import { apiClient } from './client';

export interface Evidence {
  id: string;
  text: string;
  type: 'fact' | 'metric' | 'claim' | 'quote' | 'benchmark';
  chunk: string;
  document: string;
  document_title: string;
  chunk_preview: {
    chunk_index: number;
    text_preview: string;
    token_count: number;
    span: any;
  };
  extraction_confidence: number;
  user_credibility_rating: number | null;
  embedding: number[] | null;
  extracted_at: string;
  created_at: string;
}

export interface RateEvidenceRequest {
  rating: number;  // 1-5 stars
}

export interface LinkSignalRequest {
  signal_id: string;
  relationship: 'supports' | 'contradicts';
}

export const evidenceAPI = {
  /**
   * List evidence with optional filters
   */
  list: async (filters?: {
    document_id?: string;
    case_id?: string;
    project_id?: string;
    type?: string;
    min_rating?: number;
  }): Promise<Evidence[]> => {
    const params = new URLSearchParams();
    if (filters?.document_id) params.append('document_id', filters.document_id);
    if (filters?.case_id) params.append('case_id', filters.case_id);
    if (filters?.project_id) params.append('project_id', filters.project_id);
    if (filters?.type) params.append('type', filters.type);
    if (filters?.min_rating) params.append('min_rating', filters.min_rating.toString());
    
    const query = params.toString();
    return apiClient.get(`/evidence/${query ? `?${query}` : ''}`);
  },

  /**
   * Get single evidence item
   */
  get: async (id: string): Promise<Evidence> => {
    return apiClient.get(`/evidence/${id}/`);
  },

  /**
   * Rate evidence credibility (1-5 stars)
   */
  rate: async (id: string, rating: number): Promise<Evidence> => {
    return apiClient.patch(`/evidence/${id}/rate/`, { rating });
  },

  /**
   * Link evidence to a signal
   */
  linkSignal: async (
    evidenceId: string,
    signalId: string,
    relationship: 'supports' | 'contradicts'
  ): Promise<Evidence> => {
    return apiClient.post(`/evidence/${evidenceId}/link-signal/`, {
      signal_id: signalId,
      relationship,
    });
  },

  /**
   * Get signals related to this evidence
   */
  relatedSignals: async (id: string): Promise<{
    supports: any[];
    contradicts: any[];
  }> => {
    return apiClient.get(`/evidence/${id}/related-signals/`);
  },

  /**
   * Get high-confidence evidence
   */
  highConfidence: async (): Promise<Evidence[]> => {
    return apiClient.get('/evidence/high_confidence/');
  },
};
