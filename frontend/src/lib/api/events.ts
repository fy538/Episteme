/**
 * Events API client
 *
 * Read-only access to the append-only event store.
 * Events power the home page timeline.
 */

import { apiClient } from './client';

export interface EventItem {
  id: string;
  timestamp: string;
  actor_type: 'user' | 'assistant' | 'system';
  type: string;
  payload: Record<string, any>;
  correlation_id: string | null;
  case_id: string | null;
  thread_id: string | null;
}

/** Event types worth surfacing on the home page timeline */
const TIMELINE_TYPES = [
  'CaseCreated',
  'CaseCreatedFromAnalysis',
  'InquiryCreated',
  'InquiryResolved',
  'BriefEvolved',
  'CaseScaffolded',
  'WorkflowCompleted',
].join(',');

export const eventsAPI = {
  /** Fetch recent timeline-worthy events across all cases */
  async getRecent(limit = 20): Promise<EventItem[]> {
    const response = await apiClient.get<{ results: EventItem[] }>(
      `/events/?types=${TIMELINE_TYPES}&limit=${limit}`
    );
    return response.results || [];
  },

  /** Fetch all events for a specific case */
  async getCaseTimeline(caseId: string): Promise<EventItem[]> {
    return apiClient.get<EventItem[]>(`/events/case/${caseId}/timeline/`);
  },
};
