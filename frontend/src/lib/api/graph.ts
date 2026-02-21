/**
 * Graph API functions — v2 endpoints for the knowledge graph.
 */

import { apiClient } from './client';
import type {
  ProjectGraph,
  ClusteredProjectGraph,
  ProjectSummary,
  GraphDelta,
} from '../types/graph';
import type {
  ClusterHierarchy,
  ProjectInsight,
  InsightStatus,
  HierarchyChunkResult,
} from '../types/hierarchy';
import type { ProjectOrientation } from '../types/orientation';

const V2_BASE = '/v2';

/**
 * Per-project ETag cache for summary requests.
 * Enables 304 Not Modified responses to skip JSON parsing.
 */
const summaryEtags = new Map<string, { etag: string; data: ProjectSummary }>();

export interface GraphQueryOptions {
  limit?: number;
  nodeType?: string;
}

function buildGraphParams(opts?: GraphQueryOptions): string {
  const params = new URLSearchParams();
  if (opts?.limit) params.set('limit', String(opts.limit));
  if (opts?.nodeType) params.set('node_type', opts.nodeType);
  return params.toString();
}

export const graphAPI = {
  /**
   * Get graph (nodes + edges) for a project.
   * Defaults to 2000 node limit server-side.
   */
  async getGraph(projectId: string, opts?: GraphQueryOptions): Promise<ProjectGraph> {
    const qs = buildGraphParams(opts);
    const sep = qs ? `?${qs}` : '';
    return apiClient.get<ProjectGraph>(
      `${V2_BASE}/projects/${projectId}/graph/${sep}`
    );
  },

  /**
   * Get graph with backend-computed clusters and quality metrics.
   * Defaults to 2000 node limit server-side.
   */
  async getClusteredGraph(projectId: string, resolution = 1.0, opts?: GraphQueryOptions): Promise<ClusteredProjectGraph> {
    const extra = buildGraphParams(opts);
    const qs = `resolution=${resolution}${extra ? `&${extra}` : ''}`;
    return apiClient.get<ClusteredProjectGraph>(
      `${V2_BASE}/projects/${projectId}/graph/clustered/?${qs}`
    );
  },

  // ── Case-scoped graph ──────────────────────────────────────

  /**
   * Get composed case graph (case nodes + referenced project nodes + visible edges).
   * Defaults to 2000 node limit server-side.
   */
  async getCaseGraph(projectId: string, caseId: string, opts?: GraphQueryOptions): Promise<ProjectGraph> {
    const qs = buildGraphParams(opts);
    const sep = qs ? `?${qs}` : '';
    return apiClient.get<ProjectGraph>(
      `${V2_BASE}/projects/${projectId}/cases/${caseId}/graph/${sep}`
    );
  },

  // ── Project Summary ──────────────────────────────────────

  /**
   * Get the current project summary with ETag-based caching.
   *
   * Sends If-None-Match with the cached ETag; on 304 returns the
   * cached data without re-parsing JSON. Falls back to a normal
   * request if ETag handling is unavailable.
   */
  async getSummary(projectId: string): Promise<ProjectSummary> {
    const isDevMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
    const token = isDevMode ? null : apiClient.getToken();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    // Include cached ETag if available
    const cached = summaryEtags.get(projectId);
    if (cached) {
      headers['If-None-Match'] = cached.etag;
    }

    const response = await fetch(
      `${apiClient.getBaseURL()}${V2_BASE}/projects/${projectId}/summary/`,
      { method: 'GET', headers, mode: 'cors' },
    );

    if (response.status === 304 && cached) {
      return cached.data;
    }

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      throw new Error(text || `API Error ${response.status}`);
    }

    const data: ProjectSummary = await response.json();

    // Store ETag for next request
    const etag = response.headers.get('ETag');
    if (etag) {
      summaryEtags.set(projectId, { etag, data });
    }

    return data;
  },

  /**
   * Get recent graph deltas for a project.
   */
  async getRecentDeltas(projectId: string, limit = 5): Promise<GraphDelta[]> {
    return apiClient.get<GraphDelta[]>(
      `${V2_BASE}/projects/${projectId}/graph/deltas/?limit=${limit}`
    );
  },

  /**
   * Trigger summary regeneration. Returns 202 with task_id.
   */
  async regenerateSummary(projectId: string): Promise<{ status: string; task_id: string }> {
    return apiClient.post(
      `${V2_BASE}/projects/${projectId}/summary/regenerate/`,
      {}
    );
  },

  /**
   * Stream summary generation progress via SSE.
   * Yields events: status, sections, completed, failed, timeout.
   */
  streamSummary(
    projectId: string,
    onEvent: (event: { event: string; data: unknown }) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    return apiClient.streamGet(
      `${V2_BASE}/projects/${projectId}/summary/stream/`,
      onEvent,
      signal,
    );
  },

  // ── Hierarchical Clustering ──────────────────────────────────

  /**
   * Get the current cluster hierarchy for a project.
   */
  async getHierarchy(projectId: string): Promise<ClusterHierarchy> {
    return apiClient.get<ClusterHierarchy>(
      `${V2_BASE}/projects/${projectId}/hierarchy/`
    );
  },

  /**
   * Trigger a hierarchy rebuild. Returns 202 Accepted.
   */
  async rebuildHierarchy(projectId: string): Promise<{ status: string }> {
    return apiClient.post(
      `${V2_BASE}/projects/${projectId}/hierarchy/rebuild/`,
      {}
    );
  },

  /**
   * Search chunks by query within the project hierarchy.
   */
  async searchHierarchyChunks(
    projectId: string,
    query: string,
    topK = 20,
  ): Promise<{ results: HierarchyChunkResult[] }> {
    return apiClient.get(
      `${V2_BASE}/projects/${projectId}/hierarchy/search/?q=${encodeURIComponent(query)}&top_k=${topK}`
    );
  },

  // ── Project Insights ──────────────────────────────────────────

  /**
   * Get project insights, optionally filtered by status and type.
   */
  async getInsights(
    projectId: string,
    filters?: { status?: string; type?: string },
  ): Promise<ProjectInsight[]> {
    const params = new URLSearchParams();
    if (filters?.status) params.set('status', filters.status);
    if (filters?.type) params.set('type', filters.type);
    const qs = params.toString();
    return apiClient.get<ProjectInsight[]>(
      `${V2_BASE}/projects/${projectId}/insights/${qs ? `?${qs}` : ''}`
    );
  },

  /**
   * Update an insight's status (acknowledge, resolve, dismiss).
   */
  async updateInsight(
    projectId: string,
    insightId: string,
    updates: { status: InsightStatus },
  ): Promise<ProjectInsight> {
    return apiClient.patch(
      `${V2_BASE}/projects/${projectId}/insights/${insightId}/`,
      updates,
    );
  },

  // ── Project Orientation ──────────────────────────────────────

  /**
   * Get the current orientation with findings and exploration angles.
   */
  async getOrientation(projectId: string): Promise<ProjectOrientation> {
    return apiClient.get<ProjectOrientation>(
      `${V2_BASE}/projects/${projectId}/orientation/`
    );
  },

  /**
   * Trigger orientation regeneration from the current hierarchy.
   * Returns 202 with task_id.
   */
  async regenerateOrientation(projectId: string): Promise<{ status: string; task_id: string }> {
    return apiClient.post(
      `${V2_BASE}/projects/${projectId}/orientation/regenerate/`,
      {}
    );
  },

  /**
   * Stream orientation generation progress via SSE.
   * Yields events: status, lead, finding, angle, completed, failed, timeout.
   */
  streamOrientation(
    projectId: string,
    onEvent: (event: { event: string; data: unknown }) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    return apiClient.streamGet(
      `${V2_BASE}/projects/${projectId}/orientation/stream/`,
      onEvent,
      signal,
    );
  },

  /**
   * Generate content for an exploration angle on demand.
   */
  async generateAngle(
    projectId: string,
    insightId: string,
  ): Promise<{ insight_id: string; content: string; cached: boolean }> {
    return apiClient.post(
      `${V2_BASE}/projects/${projectId}/insights/${insightId}/generate/`,
      {}
    );
  },

  /**
   * Trigger background research for a gap-type insight.
   * Returns 202 Accepted.
   */
  async researchInsight(
    projectId: string,
    insightId: string,
  ): Promise<{ status: string; task_id: string }> {
    return apiClient.post(
      `${V2_BASE}/projects/${projectId}/insights/${insightId}/research/`,
      {}
    );
  },

  /**
   * Link a chat thread to an orientation finding (insight).
   * Enables "Continue discussion" on subsequent visits.
   */
  async linkInsightThread(
    projectId: string,
    insightId: string,
    threadId: string,
  ): Promise<void> {
    return apiClient.patch(
      `${V2_BASE}/projects/${projectId}/insights/${insightId}/`,
      { linked_thread: threadId },
    );
  },

  /**
   * Accept an AI-proposed orientation diff from the chat UI.
   */
  async acceptOrientationDiff(
    projectId: string,
    orientationId: string,
    proposedState: Record<string, unknown>,
    diffSummary: string,
    diffData: Record<string, unknown>,
  ): Promise<{ status: string; orientation_id: string; lens_type: string; lead_text: string }> {
    return apiClient.post(
      `${V2_BASE}/projects/${projectId}/orientation/accept-diff/`,
      {
        orientation_id: orientationId,
        proposed_state: proposedState,
        diff_summary: diffSummary,
        diff_data: diffData,
      },
    );
  },
};
