/**
 * Graph types — Node, Edge, GraphDelta.
 *
 * Matches backend serializer shapes exactly.
 */

// ── Node types ──────────────────────────────────────────────────

export type NodeType = 'claim' | 'evidence' | 'assumption' | 'tension';

export type NodeStatus =
  // Claim
  | 'supported' | 'contested' | 'unsubstantiated'
  // Evidence
  | 'confirmed' | 'uncertain' | 'disputed'
  // Assumption
  | 'untested' | 'assumption_confirmed' | 'challenged' | 'refuted'
  // Tension
  | 'surfaced' | 'acknowledged' | 'resolved';

export type EdgeType = 'supports' | 'contradicts' | 'depends_on';

export type NodeSourceType =
  | 'document_extraction'
  | 'chat_edit'
  | 'agent_analysis'
  | 'user_edit'
  | 'integration';

export type DeltaTrigger =
  | 'document_upload'
  | 'chat_edit'
  | 'agent_analysis'
  | 'user_edit';

// ── Core interfaces ─────────────────────────────────────────────

export interface GraphNode {
  id: string;
  node_type: NodeType;
  status: NodeStatus;
  content: string;
  properties: Record<string, any>;
  project: string;
  case: string | null;
  scope: 'project' | 'case';
  source_type: NodeSourceType;
  source_document: string | null;
  source_document_title: string | null;
  confidence: number;
  created_at: string;
  updated_at: string;
}

export interface GraphEdge {
  id: string;
  edge_type: EdgeType;
  source_node: string;
  target_node: string;
  source_content: string;
  target_content: string;
  strength: number | null;
  provenance: string;
  source_type: NodeSourceType;
  created_at: string;
}

export interface GraphNodeDetail extends GraphNode {
  edges: GraphEdge[];
  neighbors: GraphNode[];
}

export interface GraphDelta {
  id: string;
  project: string;
  trigger: DeltaTrigger;
  patch: Record<string, any>;
  narrative: string;
  nodes_created: number;
  nodes_updated: number;
  edges_created: number;
  tensions_surfaced: number;
  assumptions_challenged: number;
  source_document: string | null;
  source_document_title: string | null;
  source_message: string | null;
  created_at: string;
}

// ── View interfaces ─────────────────────────────────────────────

export interface ProjectGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface BackendCluster {
  node_ids: string[];
  centroid_node_id: string;
  edge_count: number;
  node_types: Record<string, number>;
  label?: string;
}

export interface ClusterQuality {
  modularity: number;
  mean_conductance: number;
  per_cluster: Array<{
    cluster_index: number;
    conductance: number;
    density: number;
    node_count: number;
  }>;
}

export interface ClusteredProjectGraph extends ProjectGraph {
  clusters: BackendCluster[];
  cluster_quality: ClusterQuality;
}

export type InclusionType = 'auto' | 'manual' | 'document';

export interface CaseNodeReference {
  id: string;
  case: string;
  node: string;
  node_content: string;
  node_type: NodeType;
  inclusion_type: InclusionType;
  relevance: number;
  excluded: boolean;
  created_at: string;
}

// ── Edit action types (from chat) ───────────────────────────────

export type GraphEditAction =
  | {
      action: 'create_node';
      type: NodeType;
      content: string;
      status?: NodeStatus;
      properties?: Record<string, any>;
    }
  | {
      action: 'create_edge';
      source_ref: string;
      target_ref: string;
      edge_type: EdgeType;
      provenance?: string;
      strength?: number;
    }
  | {
      action: 'update_node';
      ref: string;
      content?: string;
      status?: NodeStatus;
      properties?: Record<string, any>;
      confidence?: number;
    }
  | {
      action: 'remove_node';
      ref: string;
    };

export interface GraphEditSummary {
  nodes_created: number;
  nodes_updated: number;
  edges_created: number;
  nodes_removed: number;
  tensions_surfaced: number;
  created_node_ids: string[];
  /** Individual edit actions applied (for expandable detail view) */
  edits?: Array<{
    action: string;
    type?: string;
    content?: string;
    edge_type?: string;
    ref?: string;
  }>;
}

// ── Project Summary ─────────────────────────────────────────────

export type SummaryStatus = 'none' | 'seed' | 'generating' | 'partial' | 'full' | 'failed';

export interface SummaryTheme {
  theme_label: string;
  narrative: string;
  cited_nodes: string[];
}

export interface ProjectSummarySections {
  overview: string;
  key_findings: SummaryTheme[];
  emerging_picture: string;
  attention_needed: string;
  what_changed: string;
}

export interface ProjectSummaryCluster {
  label: string;
  node_ids: string[];
  centroid_node_id: string;
}

export interface ProjectSummary {
  id?: string;
  project?: string;
  status: SummaryStatus;
  sections: ProjectSummarySections;
  is_stale: boolean;
  stale_since?: string | null;
  generation_metadata?: Record<string, any>;
  version?: number;
  clusters: ProjectSummaryCluster[];
  created_at?: string;
  updated_at?: string;
}
