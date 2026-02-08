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
  source_url: string;
  source_title: string;
  source_domain: string;
  source_published_date: string | null;
  retrieval_method: string;
  extracted_at: string;
  created_at: string;
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
   * Rate evidence credibility (1-5 stars)
   */
  rate: async (id: string, rating: number): Promise<Evidence> => {
    return apiClient.patch(`/evidence/${id}/rate/`, { rating });
  },

  /**
   * Create inquiry evidence (user observation from chat)
   *
   * Uses the inquiry evidence endpoint which supports full CRUD
   * and 'user_observation' evidence type for chat-sourced evidence.
   */
  createForInquiry: async (data: {
    inquiry_id: string;
    evidence_text: string;
    direction?: 'supports' | 'contradicts' | 'neutral';
    strength?: number;
    credibility?: number;
  }): Promise<InquiryEvidence> => {
    return apiClient.post(`/inquiries/${data.inquiry_id}/add-evidence/`, {
      evidence_type: 'user_observation',
      evidence_text: data.evidence_text,
      direction: data.direction || 'neutral',
      strength: data.strength || 0.5,
      credibility: data.credibility || 0.5,
    });
  },

  /**
   * Ingest external evidence (pasted text, research from other tools, etc.)
   *
   * Evidence flows through the universal ingestion pipeline:
   * create → embed → auto-reason (signal linking) → cascade → grounding
   */
  ingestExternal: async (data: {
    case_id: string;
    items: Array<{
      text: string;
      source_url?: string;
      source_title?: string;
      evidence_type?: string;
      source_published_date?: string;
    }>;
    source_label?: string;
  }): Promise<{ status: string; task_id: string; items_queued: number }> => {
    return apiClient.post('/evidence/ingest/', data);
  },

  /**
   * Fetch a URL, extract content, and ingest as evidence.
   *
   * Creates a Document from the fetched content and processes it
   * through the full document pipeline (chunk → embed → extract → auto-reason).
   */
  fetchUrl: async (data: {
    url: string;
    case_id: string;
  }): Promise<{ status: string; task_id: string }> => {
    return apiClient.post('/evidence/fetch-url/', data);
  },
};

export interface InquiryEvidence {
  id: string;
  inquiry: string;
  evidence_type: 'document_full' | 'document_chunks' | 'experiment' | 'external_data' | 'user_observation';
  source_document: string | null;
  evidence_text: string;
  direction: 'supports' | 'contradicts' | 'neutral';
  strength: number;
  credibility: number;
  verified: boolean;
  notes: string;
  created_at: string;
  created_by: number;
}
