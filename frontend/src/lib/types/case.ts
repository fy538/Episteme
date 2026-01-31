/**
 * TypeScript types for cases and inquiries
 */

export interface Case {
  id: string;
  title: string;
  status: 'draft' | 'active' | 'archived';
  stakes: 'low' | 'medium' | 'high';
  position: string;
  confidence?: number;
  main_brief?: string;
  user: string;
  project?: string;
  created_at: string;
  updated_at: string;
}

export interface Inquiry {
  id: string;
  case: string;
  title: string;
  description: string;
  elevation_reason: string;
  status: 'open' | 'investigating' | 'resolved' | 'archived';
  conclusion: string;
  conclusion_confidence?: number;
  resolved_at?: string;
  priority: number;
  sequence_index: number;
  brief?: string;
  created_at: string;
  updated_at: string;
}

export interface CaseDocument {
  id: string;
  case: string;
  inquiry?: string;
  document_type: 'case_brief' | 'inquiry_brief' | 'research' | 'debate' | 'critique' | 'source' | 'notes';
  title: string;
  content_markdown: string;
  edit_friction: 'low' | 'high' | 'readonly';
  ai_structure: Record<string, any>;
  generated_by_ai: boolean;
  agent_type: string;
  times_cited: number;
  can_edit: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}
