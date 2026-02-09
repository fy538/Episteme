/**
 * Inquiry-related types
 */

export interface Objection {
  id: string;
  inquiry: string;
  content: string;
  source: 'user' | 'ai' | 'peer';
  status: 'open' | 'addressed' | 'dismissed';
  response: string | null;
  created_at: string;
  updated_at: string;
}
