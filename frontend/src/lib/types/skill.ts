/**
 * Skill types — domain-specific templates for AI agents.
 *
 * Skills are versioned SKILL.md files with YAML frontmatter
 * that configure research, critique, and brief agents.
 */

export type SkillScope = 'personal' | 'team' | 'organization' | 'public';
export type SkillStatus = 'draft' | 'active' | 'archived';

export interface Skill {
  id: string;
  name: string;
  description: string;
  domain: string;
  scope: SkillScope;
  status: SkillStatus;
  owner: number;
  applies_to_agents: string[];  // e.g. ["research", "critique", "brief"]
  current_version: number;
  source_case: string | null;
  forked_from: string | null;
  created_at: string;
  updated_at: string;
}

export interface SkillVersion {
  id: string;
  skill: string;
  version: number;
  skill_md_content: string;
  resources: Record<string, string>;
  created_by: number;
  changelog: string;
  created_at: string;
}

export interface SkillWithVersion extends Skill {
  current_version_content?: SkillVersion;
}

export interface SkillSuggestion {
  skill: Skill;
  relevance_score: number;
  reason: string;
}

// ── Skill Packs ──────────────────────────────────────────────────

export type SkillPackScope = 'public' | 'organization';
export type MembershipRole = 'domain' | 'methodology' | 'quality' | 'general';

export interface SkillPackMembership {
  skill: Skill;
  order: number;
  role: MembershipRole;
}

export interface SkillPack {
  id: string;
  name: string;
  description: string;
  slug: string;
  icon: string;
  scope: SkillPackScope;
  status: 'active' | 'archived';
  organization?: string | null;
  organization_name?: string | null;
  created_by?: number | null;
  created_by_name?: string | null;
  skill_count: number;
  skills_detail: SkillPackMembership[];
  created_at: string;
  updated_at: string;
}

export interface SkillPackListItem {
  id: string;
  name: string;
  description: string;
  slug: string;
  icon: string;
  scope: SkillPackScope;
  status: 'active' | 'archived';
  skill_count: number;
  skill_names: string[];
  created_at: string;
}

/** Lightweight summary returned inline in Case responses */
export interface ActiveSkillSummary {
  id: string;
  name: string;
  domain: string;
}
