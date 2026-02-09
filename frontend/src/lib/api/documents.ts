/**
 * Documents API functions
 */

import { apiClient } from './client';
import type { WorkingDocument } from '../types/case';
import type { UploadedDocument } from '../types/document';

export const documentsAPI = {
  async getByCase(caseId: string): Promise<WorkingDocument[]> {
    const response = await apiClient.get<WorkingDocument[]>(
      `/working-documents/?case=${caseId}`
    );
    return Array.isArray(response) ? response : [];
  },

  async getDocument(docId: string): Promise<WorkingDocument> {
    return apiClient.get<WorkingDocument>(`/working-documents/${docId}/`);
  },

  async updateDocument(
    docId: string,
    content: string
  ): Promise<WorkingDocument> {
    return apiClient.put<WorkingDocument>(`/working-documents/${docId}/`, {
      content_markdown: content,
    });
  },

  async update(docId: string, data: Partial<WorkingDocument>): Promise<WorkingDocument> {
    return apiClient.patch<WorkingDocument>(`/working-documents/${docId}/`, data);
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
    return apiClient.post(`/working-documents/${docId}/integrate_content/`, {
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
    return apiClient.post(`/working-documents/${docId}/detect_assumptions/`, {});
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
    confidence: number;
    status: 'pending' | 'accepted' | 'rejected';
  }>> {
    return apiClient.post(`/working-documents/${docId}/generate-suggestions/`, {
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
    return apiClient.post(`/working-documents/${docId}/apply-suggestion/`, {
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
    return apiClient.post(`/working-documents/${docId}/inline-complete/`, {
      context_before: contextBefore,
      context_after: contextAfter,
      max_length: maxLength,
    });
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
    const url = `${API_BASE}/working-documents/${docId}/execute-task-stream/`;
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
    return apiClient.get(`/working-documents/${docId}/version-history/`);
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
    return apiClient.get(`/working-documents/${docId}/version-history/?include_content=true`);
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
    return apiClient.post(`/working-documents/${docId}/restore-version/`, {
      version_id: versionId,
    });
  },

  // ─── Uploaded Source Documents (projects.Document) ──────────────────────────

  /**
   * List uploaded source documents, optionally filtered by case or project.
   * Hits /api/documents/ (projects.Document model).
   */
  async listUploadedDocuments(params?: {
    caseId?: string;
    projectId?: string;
  }): Promise<UploadedDocument[]> {
    const query = new URLSearchParams();
    if (params?.caseId) query.set('case_id', params.caseId);
    if (params?.projectId) query.set('project_id', params.projectId);
    const qs = query.toString();
    const response = await apiClient.get<UploadedDocument[]>(
      `/documents/${qs ? `?${qs}` : ''}`
    );
    return Array.isArray(response) ? response : [];
  },

  /**
   * Delete an uploaded source document.
   */
  async deleteUploadedDocument(docId: string): Promise<void> {
    return apiClient.delete(`/documents/${docId}/`);
  },

  /**
   * Re-trigger processing for a failed document.
   * Creates a new processing task on the backend.
   */
  async reprocessDocument(docId: string): Promise<UploadedDocument> {
    return apiClient.post<UploadedDocument>(
      `/documents/${docId}/reprocess/`,
      {}
    );
  },

  /**
   * Create a text-based source document (pasted text).
   * Hits /api/documents/ (projects.Document model).
   */
  async create(data: {
    title: string;
    source_type: string;
    content_text: string;
    project_id: string;
    case_id?: string;
  }): Promise<UploadedDocument> {
    return apiClient.post('/documents/', data);
  },

  /**
   * Upload a file (PDF, DOCX, TXT, MD) via FormData.
   * The backend extracts text from the file using PyPDF2/python-docx.
   * Hits /api/documents/ (projects.Document model).
   */
  async upload(data: {
    file: File;
    title: string;
    project_id: string;
    case_id?: string;
  }): Promise<UploadedDocument> {
    const formData = new FormData();
    formData.append('file', data.file);
    formData.append('title', data.title);
    formData.append('source_type', 'upload');
    formData.append('project_id', data.project_id);
    if (data.case_id) formData.append('case_id', data.case_id);
    return apiClient.upload('/documents/', formData);
  },

  /**
   * Stream processing progress for a document via SSE.
   */
  streamProcessing(
    documentId: string,
    onEvent: (event: { event: string; data: any }) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    return apiClient.streamGet(
      `/documents/${documentId}/processing-stream/`,
      onEvent,
      signal,
    );
  },

  /**
   * Trigger async research generation via the multi-step research loop.
   * Returns a task ID; the research runs in the background.
   */
  async generateResearch(caseId: string, topic: string): Promise<{
    task_id: string;
    status: string;
  }> {
    return apiClient.post('/working-documents/generate-research-async/', {
      case_id: caseId,
      topic,
    });
  },

  // Alias for backwards compatibility
  get: async function(docId: string) {
    return this.getDocument(docId);
  },

};
