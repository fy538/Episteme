/**
 * Chat API functions
 */

import { apiClient } from './client';
import type { ChatThread, Message } from '../types/chat';

export const chatAPI = {
  async createThread(): Promise<ChatThread> {
    return apiClient.post<ChatThread>('/chat/threads/', {});
  },

  async getThread(threadId: string): Promise<ChatThread> {
    return apiClient.get<ChatThread>(`/chat/threads/${threadId}/`);
  },

  async listThreads(): Promise<ChatThread[]> {
    const response = await apiClient.get<{ results: ChatThread[] }>('/chat/threads/');
    return response.results || [];
  },

  async updateThread(threadId: string, data: Partial<ChatThread>): Promise<ChatThread> {
    return apiClient.patch<ChatThread>(`/chat/threads/${threadId}/`, data);
  },

  async sendMessage(threadId: string, content: string): Promise<Message> {
    return apiClient.post<Message>(`/chat/threads/${threadId}/messages/`, { content });
  },

  async sendMessageStream(
    threadId: string,
    content: string,
    onChunk: (delta: string) => void,
    onDone: (messageId?: string) => void
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
      }
    );
  },

  async getMessages(threadId: string): Promise<Message[]> {
    const response = await apiClient.get<{ results: Message[] }>(
      `/chat/messages/?thread=${threadId}`
    );
    return response.results || [];
  },
};
