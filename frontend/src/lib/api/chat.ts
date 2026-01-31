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

  async sendMessage(threadId: string, content: string): Promise<Message> {
    return apiClient.post<Message>(`/chat/threads/${threadId}/messages/`, { content });
  },

  async getMessages(threadId: string): Promise<Message[]> {
    const response = await apiClient.get<{ results: Message[] }>(
      `/chat/messages/?thread=${threadId}`
    );
    return response.results || [];
  },
};
