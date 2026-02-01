/**
 * Chat API functions
 */

import { apiClient } from './client';
import type { ChatThread, Message } from '../types/chat';

export const chatAPI = {
  async createThread(projectId?: string | null): Promise<ChatThread> {
    return apiClient.post<ChatThread>('/chat/threads/', {
      ...(projectId ? { project: projectId } : {}),
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

  async sendMessage(threadId: string, content: string): Promise<Message> {
    return apiClient.post<Message>(`/chat/threads/${threadId}/messages/`, { content });
  },

  async sendMessageStream(
    threadId: string,
    content: string,
    onChunk: (delta: string) => void,
    onDone: (messageId?: string) => void,
    signal?: AbortSignal
  ): Promise<void> {
    await apiClient.stream(
      `/chat/threads/${threadId}/messages/?stream=true`,
      { content },
      ({ event, data }) => {
        if (event === 'chunk' && data?.delta) {
          onChunk(data.delta);
        } else if (event === 'done') {
          onDone(data?.message_id);
        }
      },
      signal
    );
  },

  async getMessages(threadId: string): Promise<Message[]> {
    const response = await apiClient.get<{ results: Message[] }>(
      `/chat/messages/?thread=${threadId}`
    );
    return response.results || [];
  },

  async analyzeForCase(threadId: string): Promise<{
    suggested_title: string;
    position_draft: string;
    key_questions: string[];
    assumptions: string[];
    background_summary: string;
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
};
