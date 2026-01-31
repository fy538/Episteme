/**
 * Artifact types
 */

export interface Block {
  id: string;
  type: 'heading' | 'paragraph' | 'list' | 'quote' | 'citation';
  content: string;
  cites?: string[];  // Signal/Evidence UUIDs
  metadata?: any;
  level?: number;  // For headings
}

export interface Artifact {
  id: string;
  title: string;
  type: 'research' | 'critique' | 'brief' | 'deck';
  case: string;
  user: number;
  current_version: string;
  current_version_blocks: Block[];
  version_count: number;
  input_signal_count: number;
  input_evidence_count: number;
  generated_by: string;
  is_published: boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ArtifactVersion {
  id: string;
  artifact: string;
  version: number;
  blocks: Block[];
  parent_version: string | null;
  diff: {
    added_blocks?: string[];
    removed_blocks?: string[];
    modified_blocks?: Array<{
      block_id: string;
      old_content: string;
      new_content: string;
    }>;
  };
  created_at: string;
  created_by: number;
  generation_time_ms: number | null;
}
