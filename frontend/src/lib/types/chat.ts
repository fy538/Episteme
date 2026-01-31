/**
 * TypeScript types for chat-related models
 */

export interface ChatThread {
  id: string;
  title: string;
  primary_case?: string;
  user: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  thread: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  event_id: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface CreateMessageRequest {
  content: string;
}
