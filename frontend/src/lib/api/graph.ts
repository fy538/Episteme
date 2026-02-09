/**
 * Graph API functions — v2 endpoints for the knowledge graph.
 */

import { apiClient } from './client';
import type {
  ProjectGraph,
  ClusteredProjectGraph,
  ProjectSummary,
} from '../types/graph';

const V2_BASE = '/v2';

export const graphAPI = {
  /**
   * Get full graph (nodes + edges) for a project.
   */
  async getGraph(projectId: string): Promise<ProjectGraph> {
    return apiClient.get<ProjectGraph>(
      `${V2_BASE}/projects/${projectId}/graph/`
    );
  },

  /**
   * Get full graph with backend-computed clusters and quality metrics.
   */
  async getClusteredGraph(projectId: string, resolution = 1.0): Promise<ClusteredProjectGraph> {
    return apiClient.get<ClusteredProjectGraph>(
      `${V2_BASE}/projects/${projectId}/graph/clustered/?resolution=${resolution}`
    );
  },

  // ── Case-scoped graph ──────────────────────────────────────

  /**
   * Get composed case graph (case nodes + referenced project nodes + visible edges).
   */
  async getCaseGraph(projectId: string, caseId: string): Promise<ProjectGraph> {
    return apiClient.get<ProjectGraph>(
      `${V2_BASE}/projects/${projectId}/cases/${caseId}/graph/`
    );
  },

  // ── Project Summary ──────────────────────────────────────

  /**
   * Get the current project summary.
   */
  async getSummary(projectId: string): Promise<ProjectSummary> {
    return apiClient.get<ProjectSummary>(
      `${V2_BASE}/projects/${projectId}/summary/`
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
};
