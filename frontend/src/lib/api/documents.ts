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

  async update(docId: string, data: Partial<CaseDocument>): Promise<CaseDocument> {
    return apiClient.patch<CaseDocument>(`/cases/documents/${docId}/`, data);
  },

  async integrateContent(
    docId: string,
    content: string,
    hint?: string,
    messageId?: string
  ): Promise<{
    updated_content: string;
    insertion_section: string;
    rewritten_content: string;
  }> {
    return apiClient.post(`/cases/documents/${docId}/integrate_content/`, {
      content,
      hint,
      message_id: messageId,
    });
  },

  async detectAssumptions(docId: string): Promise<Array<{
    text: string;
    status: 'untested' | 'investigating' | 'validated';
    risk_level: 'low' | 'medium' | 'high';
    inquiry_id: string | null;
    validation_approach: string;
  }>> {
    return apiClient.post(`/cases/documents/${docId}/detect_assumptions/`, {});
  },

  /**
   * Generate AI suggestions for improving the document
   */
  async generateSuggestions(
    docId: string,
    maxSuggestions: number = 5
  ): Promise<Array<{
    id: string;
    section_id: string;
    suggestion_type: 'add' | 'replace' | 'delete' | 'cite' | 'clarify';
    current_content: string | null;
    suggested_content: string;
    reason: string;
    linked_signal_id: string | null;
    confidence: number;
    status: 'pending' | 'accepted' | 'rejected';
  }>> {
    return apiClient.post(`/cases/documents/${docId}/generate-suggestions/`, {
      max_suggestions: maxSuggestions,
    });
  },

  /**
   * Apply a suggestion to the document
   */
  async applySuggestion(
    docId: string,
    suggestion: {
      id: string;
      suggestion_type: string;
      current_content?: string | null;
      suggested_content: string;
      section_id?: string;
    }
  ): Promise<{
    updated_content: string;
    suggestion_applied: string;
  }> {
    return apiClient.post(`/cases/documents/${docId}/apply-suggestion/`, {
      suggestion,
    });
  },

  /**
   * Get inline completion for ghost text
   */
  async getInlineCompletion(
    docId: string,
    contextBefore: string,
    contextAfter: string,
    maxLength: number = 50
  ): Promise<{ completion: string | null }> {
    return apiClient.post(`/cases/documents/${docId}/inline-complete/`, {
      context_before: contextBefore,
      context_after: contextAfter,
      max_length: maxLength,
    });
  },

  /**
   * Get background analysis for a document
   */
  async getBackgroundAnalysis(
    docId: string,
    force: boolean = false
  ): Promise<{
    analyzed_at: string;
    content_hash: string;
    health_score: number;
    issues: Array<{
      type: string;
      severity: 'low' | 'medium' | 'high';
      message: string;
      location: string;
    }>;
    suggestions: Array<{
      id: string;
      type: string;
      content: string;
      reason: string;
      confidence: number;
    }>;
    evidence_gaps: Array<{
      claim: string;
      location: string;
      suggestion: string;
    }>;
    unlinked_claims: Array<{
      text: string;
      location: string;
      potential_sources: string[];
    }>;
    metrics: {
      claim_count: number;
      linked_claim_count: number;
      assumption_count: number;
      validated_assumption_count: number;
    };
  }> {
    return apiClient.get(
      `/cases/documents/${docId}/background-analysis/?force=${force}`
    );
  },

  /**
   * Get quick health metrics for a document
   */
  async getDocumentHealth(docId: string): Promise<{
    health_score: number | null;
    issue_count?: number;
    suggestion_count?: number;
    evidence_gap_count?: number;
    analyzed_at?: string;
    message?: string;
  }> {
    return apiClient.get(`/cases/documents/${docId}/health/`);
  },

  /**
   * Execute an agentic document editing task
   */
  async executeTask(
    docId: string,
    task: string
  ): Promise<{
    task_id: string;
    status: string;
    plan: Array<{
      id: string;
      description: string;
      status: string;
      action_type: string;
      target_section?: string;
      error?: string;
    }>;
    original_content: string;
    final_content: string;
    diff_summary: string;
    review_notes: string;
    review_score: number;
    changes: Array<{
      step_id: string;
      type: string;
      description: string;
      before: string;
      after: string;
    }>;
  }> {
    return apiClient.post(`/cases/documents/${docId}/execute-task/`, { task });
  },

  /**
   * Execute an agentic task with SSE streaming for real-time progress.
   * Returns an EventSource-like interface that yields events as the task progresses.
   *
   * Events: phase, plan, step_start, step_complete, review, done, error
   */
  executeTaskStream(
    docId: string,
    task: string,
    onEvent: (event: { type: string; data: any }) => void,
    onDone: (result: any) => void,
    onError: (error: string) => void,
  ): { abort: () => void } {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
    const url = `${API_BASE}/cases/documents/${docId}/execute-task-stream/`;
    const controller = new AbortController();

    // Use fetch with ReadableStream since EventSource doesn't support POST
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(typeof window !== 'undefined' && localStorage.getItem('auth_token')
          ? { Authorization: `Bearer ${localStorage.getItem('auth_token')}` }
          : {}),
      },
      body: JSON.stringify({ task }),
      signal: controller.signal,
      credentials: 'include',
    })
      .then(async (response) => {
        if (!response.ok) {
          onError(`HTTP ${response.status}: ${response.statusText}`);
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          onError('No response body');
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE format: "event: type\ndata: json\n\n"
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || ''; // Keep incomplete chunk

          for (const block of lines) {
            if (!block.trim()) continue;

            let eventType = 'message';
            let eventData = '';

            for (const line of block.split('\n')) {
              if (line.startsWith('event: ')) {
                eventType = line.slice(7).trim();
              } else if (line.startsWith('data: ')) {
                eventData = line.slice(6);
              }
            }

            if (eventData) {
              try {
                const parsed = JSON.parse(eventData);
                onEvent({ type: eventType, data: parsed });

                if (eventType === 'done') {
                  onDone(parsed);
                } else if (eventType === 'error') {
                  onError(parsed.error || 'Unknown error');
                }
              } catch {
                // Ignore parse errors for partial data
              }
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          onError(err.message || 'Stream failed');
        }
      });

    return { abort: () => controller.abort() };
  },

  /**
   * Apply the result of an agentic task
   */
  async applyTaskResult(
    docId: string,
    finalContent: string
  ): Promise<{ success: boolean; message: string }> {
    return apiClient.post(`/cases/documents/${docId}/apply-task-result/`, {
      final_content: finalContent,
    });
  },

  /**
   * Get evidence links for claims in a document
   */
  async getEvidenceLinks(docId: string): Promise<{
    claims: Array<{
      id: string;
      text: string;
      location: string;
      claim_type: string;
      linked_signals: Array<{
        signal_id: string;
        signal_type: string;
        relevance: number;
        excerpt: string;
      }>;
      confidence: number;
      is_substantiated: boolean;
      suggestion?: string;
    }>;
    summary: {
      total_claims: number;
      substantiated: number;
      unsubstantiated: number;
      average_confidence: number;
    };
    evidence_coverage: number;
  }> {
    return apiClient.get(`/cases/documents/${docId}/evidence-links/`);
  },

  /**
   * Add inline citations to the document
   */
  async addCitations(
    docId: string,
    save: boolean = false
  ): Promise<{
    cited_content: string;
    claims_cited: number;
    saved: boolean;
  }> {
    return apiClient.post(`/cases/documents/${docId}/add-citations/`, { save });
  },

  /**
   * Get version history for a document
   */
  async getVersionHistory(docId: string): Promise<Array<{
    id: string;
    version: number;
    diff_summary: string;
    created_by: 'user' | 'ai_suggestion' | 'ai_task' | 'auto_save' | 'restore';
    task_description: string;
    created_at: string;
  }>> {
    return apiClient.get(`/cases/documents/${docId}/version-history/`);
  },

  /**
   * Get version history with full content (for diff comparison).
   */
  async getVersionHistoryWithContent(docId: string): Promise<Array<{
    id: string;
    version: number;
    diff_summary: string;
    created_by: 'user' | 'ai_suggestion' | 'ai_task' | 'auto_save' | 'restore';
    task_description: string;
    created_at: string;
    content_markdown: string;
  }>> {
    return apiClient.get(`/cases/documents/${docId}/version-history/?include_content=true`);
  },

  /**
   * Restore document content from a version snapshot
   */
  async restoreVersion(
    docId: string,
    versionId: string
  ): Promise<{
    success: boolean;
    restored_to_version: number;
    content: string;
  }> {
    return apiClient.post(`/cases/documents/${docId}/restore-version/`, {
      version_id: versionId,
    });
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

  // Alias for backwards compatibility
  get: async function(docId: string) {
    return this.getDocument(docId);
  },
};
