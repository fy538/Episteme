/**
 * Types for the hierarchical cluster tree and project insights.
 *
 * The hierarchy is a multi-level tree of document chunk clusters:
 * Level 0 = individual chunks, Level 1 = topics, Level 2 = themes, Level 3 = root.
 */

export interface ClusterTreeNode {
  id: string;
  level: number; // 0=chunk, 1=topic, 2=theme, 3=root
  label: string;
  summary: string;
  children: ClusterTreeNode[];
  chunk_ids: string[];
  document_ids: string[];
  chunk_count: number;
  coverage_pct: number;
  /** Summary embedding for Level 1-2 nodes; used by backend for hierarchy-aware retrieval. */
  embedding?: number[];
}

// ── Hierarchy Diff types (Plan 6) ────────────────────────────────

export interface HierarchyDiffTheme {
  label: string;
  summary?: string;
  chunk_count?: number;
  old_chunk_count?: number;
  new_chunk_count?: number;
  growth?: number;
}

export interface HierarchyDiffMergedTheme {
  old_label: string;
  merged_into: string;
}

export interface HierarchyDiffDocument {
  document_id: string;
  document_title: string;
  chunk_count: number;
}

export interface HierarchyDiff {
  new_themes: HierarchyDiffTheme[];
  removed_themes: HierarchyDiffTheme[];
  merged_themes: HierarchyDiffMergedTheme[];
  expanded_themes: HierarchyDiffTheme[];
  new_documents: HierarchyDiffDocument[];
  removed_documents: HierarchyDiffDocument[];
  chunks_added: number;
  chunks_removed: number;
  themes_before: number;
  themes_after: number;
}

export interface ClusterHierarchy {
  id: string;
  project: string;
  version: number;
  status: 'building' | 'ready' | 'failed' | 'none';
  tree: ClusterTreeNode | null;
  metadata: {
    total_chunks: number;
    total_clusters: number;
    levels: number;
    duration_ms: number;
    document_manifest?: HierarchyDiffDocument[];
    document_count?: number;
    diff?: HierarchyDiff;
    diff_summary?: string;
  };
  diff_summary: string | null;
  is_current: boolean;
  created_at: string;
  updated_at: string;
}

export type InsightType =
  | 'tension'
  | 'blind_spot'
  | 'pattern'
  | 'stale_finding'
  | 'connection'
  | 'consensus'
  | 'gap'
  | 'weak_evidence'
  | 'exploration_angle';

export type InsightSource =
  | 'agent_discovery'
  | 'case_promotion'
  | 'user_created'
  | 'orientation';

export type InsightStatus =
  | 'active'
  | 'acknowledged'
  | 'resolved'
  | 'dismissed'
  | 'superseded'
  | 'researching';

export interface ProjectInsight {
  id: string;
  project: string;
  insight_type: InsightType;
  title: string;
  content: string;
  source_type: InsightSource;
  source_cluster_ids: string[];
  source_case: string | null;
  status: InsightStatus;
  confidence: number;
  metadata: Record<string, unknown>;
  orientation: string | null;
  display_order: number;
  action_type: '' | 'discuss' | 'research';
  linked_thread: string | null;
  research_result: ResearchResult;
  created_at: string;
  updated_at: string;
}

export interface ResearchResult {
  answer?: string;
  sources?: Array<{ title: string; snippet: string; document_id?: string }>;
  researched_at?: string;
}

export interface HierarchyChunkResult {
  chunk_id: string;
  chunk_text: string;
  document_id: string;
  document_title: string;
  similarity: number;
  topic_label: string;
  theme_label: string;
}
