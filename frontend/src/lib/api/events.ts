/**
 * Events API client
 *
 * Read-only access to the append-only event store.
 * Events power the home page timeline and case-level timelines.
 */

import { apiClient } from './client';

export interface EventItem {
  id: string;
  timestamp: string;
  actor_type: 'user' | 'assistant' | 'system';
  type: string;
  category?: string;
  payload: Record<string, any>;
  correlation_id: string | null;
  case_id: string | null;
  thread_id: string | null;
}

export const eventsAPI = {
  /** Fetch all events for a workflow by correlation_id (chronological) */
  async getWorkflowEvents(correlationId: string): Promise<EventItem[]> {
    return apiClient.get<EventItem[]>(
      `/events/workflow/${correlationId}/`
    );
  },
};
