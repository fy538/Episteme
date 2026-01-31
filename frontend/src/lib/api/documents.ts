/**
 * Documents API functions
 */

import { apiClient } from './client';
import type { CaseDocument } from '../types/case';

interface CitationsResponse {
  outgoing: Array<{
    id: string;
    to_document: string;
    to_title: string;
    citation_text: string;
    cited_section: string;
  }>;
  incoming: Array<{
    id: string;
    from_document: string;
    from_title: string;
    citation_text: string;
  }>;
  outgoing_count: number;
  incoming_count: number;
}

export const documentsAPI = {
  async getByCase(caseId: string): Promise<CaseDocument[]> {
    const response = await apiClient.get<CaseDocument[]>(
      `/cases/documents/?case=${caseId}`
    );
    return Array.isArray(response) ? response : [];
  },

  async getByInquiry(inquiryId: string): Promise<CaseDocument[]> {
    const response = await apiClient.get<CaseDocument[]>(
      `/cases/documents/?inquiry=${inquiryId}`
    );
    return Array.isArray(response) ? response : [];
  },

  async getDocument(docId: string): Promise<CaseDocument> {
    return apiClient.get<CaseDocument>(`/cases/documents/${docId}/`);
  },

  async updateDocument(
    docId: string,
    content: string
  ): Promise<CaseDocument> {
    return apiClient.put<CaseDocument>(`/cases/documents/${docId}/`, {
      content_markdown: content,
    });
  },

  async getCitations(docId: string): Promise<CitationsResponse> {
    return apiClient.get<CitationsResponse>(`/cases/documents/${docId}/citations/`);
  },

  async reparseCitations(docId: string): Promise<{ citations_created: number }> {
    return apiClient.post(`/cases/documents/${docId}/reparse_citations/`, {});
  },

  // Phase 2: Create document
  async create(data: {
    title: string;
    source_type: string;
    content_text: string;
    project_id: string;
    case_id?: string;
  }): Promise<CaseDocument> {
    return apiClient.post('/documents/', data);
  },
};
