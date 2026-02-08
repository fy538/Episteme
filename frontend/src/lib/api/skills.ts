/**
 * Skills API client
 *
 * For browsing domain-specific research skills.
 * Backend: /api/skills/ (SkillViewSet)
 */

import { apiClient } from './client';
import type { Skill, SkillPack, SkillPackListItem } from '../types/skill';

export const skillsAPI = {
  /**
   * List all accessible skills (personal + team + org + public)
   */
  list: async (): Promise<Skill[]> => {
    const response = await apiClient.get<{ results: Skill[] } | Skill[]>('/skills/');
    return Array.isArray(response) ? response : response.results || [];
  },
};

// ── Skill Packs API ─────────────────────────────────────────────

export const skillPacksAPI = {
  /**
   * List all active skill packs (lightweight list items)
   */
  list: async (): Promise<SkillPackListItem[]> => {
    const response = await apiClient.get<{ results: SkillPackListItem[] } | SkillPackListItem[]>(
      '/skill-packs/'
    );
    return Array.isArray(response) ? response : response.results || [];
  },

  /**
   * Get full pack detail with ordered skills
   */
  get: async (slug: string): Promise<SkillPack> => {
    return apiClient.get(`/skill-packs/${slug}/`);
  },
};
