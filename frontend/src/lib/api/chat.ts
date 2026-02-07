/**
 * Chat API functions
 */

import { apiClient } from './client';
import type { ChatThread, Message } from '../types/chat';

export const chatAPI = {
  async createThread(projectId?: string | null, metadata?: Record<string, any>): Promise<ChatThread> {
    return apiClient.post<ChatThread>('/chat/threads/', {
      ...(projectId ? { project: projectId } : {}),
      ...(metadata ? { metadata } : {}),
    });
  },

  async getThread(threadId: string): Promise<ChatThread> {
    return apiClient.get<ChatThread>(`/chat/threads/${threadId}/`);
  },

  async listThreads(params?: { archived?: 'true' | 'false' | 'all'; q?: string; project_id?: string }): Promise<ChatThread[]> {
    const query = new URLSearchParams();
    if (params?.archived) query.set('archived', params.archived);
    if (params?.q) query.set('q', params.q);
    if (params?.project_id) query.set('project_id', params.project_id);
    const suffix = query.toString() ? `?${query.toString()}` : '';
    const response = await apiClient.get<{ results: ChatThread[] }>(`/chat/threads/${suffix}`);
    return response.results || [];
  },

  async updateThread(threadId: string, data: Partial<ChatThread>): Promise<ChatThread> {
    return apiClient.patch<ChatThread>(`/chat/threads/${threadId}/`, data);
  },

  async deleteThread(threadId: string): Promise<void> {
    await apiClient.delete(`/chat/threads/${threadId}/`);
  },

  async getMessages(threadId: string): Promise<Message[]> {
    const response = await apiClient.get<{ results: Message[] }>(
      `/chat/messages/?thread=${threadId}`
    );
    return response.results || [];
  },

  async analyzeForCase(threadId: string): Promise<{
    should_suggest: boolean;
    suggested_title: string;
    suggested_question: string;
    position_draft: string;
    key_questions: string[];
    assumptions: string[];
    constraints: Array<{ type: string; description: string }>;
    success_criteria: Array<{ criterion: string; measurable?: string }>;
    signals_summary: {
      assumptions: number;
      questions: number;
      claims: number;
      constraints: number;
      goals: number;
    };
    confidence: number;
    correlation_id: string;
    message_count: number;
  }> {
    return apiClient.post(`/chat/threads/${threadId}/analyze_for_case/`, {});
  },

  async createCaseFromAnalysis(
    threadId: string,
    analysis: any,
    userEdits?: any
  ): Promise<{
    case: any;
    brief: any;
    inquiries: any[];
    correlation_id: string;
  }> {
    return apiClient.post(`/chat/threads/${threadId}/create_case_from_analysis/`, {
      analysis,
      correlation_id: analysis.correlation_id,
      user_edits: userEdits,
    });
  },

  /**
   * List all threads for a specific case
   */
  async listCaseThreads(caseId: string): Promise<ChatThread[]> {
    return apiClient.get<ChatThread[]>(`/cases/${caseId}/threads/`);
  },

  /**
   * Create a new thread for a case
   */
  async createCaseThread(caseId: string, data?: { title?: string; thread_type?: string }): Promise<ChatThread> {
    return apiClient.post<ChatThread>(`/cases/${caseId}/threads/create/`, data || {});
  },

  /**
   * Get session receipts for a thread
   */
  async getSessionReceipts(
    threadId: string,
    options?: { sessionOnly?: boolean; limit?: number }
  ): Promise<Array<{
    id: string;
    type: string;
    title: string;
    detail?: string;
    timestamp: string;
    relatedCaseId?: string;
    relatedInquiryId?: string;
  }>> {
    const params = new URLSearchParams();
    if (options?.sessionOnly !== undefined) {
      params.set('session_only', String(options.sessionOnly));
    }
    if (options?.limit !== undefined) {
      params.set('limit', String(options.limit));
    }
    const suffix = params.toString() ? `?${params.toString()}` : '';
    return apiClient.get(`/chat/threads/${threadId}/session_receipts/${suffix}`);
  },

  /**
   * Send message with unified streaming (response + reflection + signals + action hints)
   */
  async sendUnifiedStream(
    threadId: string,
    content: string,
    callbacks: {
      onResponseChunk?: (delta: string) => void;
      onReflectionChunk?: (delta: string) => void;
      onResponseComplete?: (content: string) => void;
      onReflectionComplete?: (content: string) => void;
      onSignals?: (signals: any[]) => void;
      onActionHints?: (hints: any[]) => void;
      onDone?: (result: { messageId?: string; reflectionId?: string; signalsCount?: number; actionHintsCount?: number }) => void;
      onError?: (error: string) => void;
    },
    signal?: AbortSignal,
    /** Optional mode context for backend system prompt selection */
    context?: { mode?: string; caseId?: string; inquiryId?: string }
  ): Promise<void> {
    await apiClient.stream(
      `/chat/threads/${threadId}/unified-stream/`,
      { content, ...(context ? { context } : {}) },
      ({ event, data }) => {
        switch (event) {
          case 'response_chunk':
            callbacks.onResponseChunk?.(data?.delta || '');
            break;
          case 'reflection_chunk':
            callbacks.onReflectionChunk?.(data?.delta || '');
            break;
          case 'response_complete':
            callbacks.onResponseComplete?.(data?.content || '');
            break;
          case 'reflection_complete':
            callbacks.onReflectionComplete?.(data?.content || '');
            break;
          case 'signals':
            callbacks.onSignals?.(data?.signals || []);
            break;
          case 'action_hints':
            callbacks.onActionHints?.(data?.action_hints || []);
            break;
          case 'done':
            callbacks.onDone?.({
              messageId: data?.message_id,
              reflectionId: data?.reflection_id,
              signalsCount: data?.signals_count || 0,
              actionHintsCount: data?.action_hints_count || 0,
            });
            break;
          case 'error':
            callbacks.onError?.(data?.error || 'Unknown error');
            break;
        }
      },
      signal
    );
  },

};
