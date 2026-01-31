/**
 * TypeScript types for chat-related models
 */

export interface ChatThread {
  id: string;
  title: string;
  primary_case?: string;
  project?: string | null;
  user: string;
  archived?: boolean;
  message_count?: number;
  latest_message?: {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at: string;
  } | null;
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
