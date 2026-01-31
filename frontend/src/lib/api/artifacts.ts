/**
 * Artifacts API client
 * 
 * For AI-generated and user-edited documents (research, critique, brief).
 */

import { apiClient } from './client';

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

export interface Block {
  id: string;
  type: 'heading' | 'paragraph' | 'list' | 'quote' | 'citation';
  content: string;
  cites?: string[];  // Signal/Evidence UUIDs
  metadata?: any;
  level?: number;  // For headings
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

export const artifactsAPI = {
  /**
   * List artifacts for a case
   */
  list: async (caseId?: string): Promise<Artifact[]> => {
    const params = caseId ? `?case_id=${caseId}` : '';
    return apiClient.get(`/artifacts/${params}`);
  },

  /**
   * Get single artifact with current version
   */
  get: async (id: string): Promise<Artifact> => {
    return apiClient.get(`/artifacts/${id}/`);
  },

  /**
   * Get version history for artifact
   */
  versions: async (id: string): Promise<ArtifactVersion[]> => {
    return apiClient.get(`/artifacts/${id}/versions/`);
  },

  /**
   * Edit a specific block (creates new version)
   */
  editBlock: async (
    artifactId: string,
    blockId: string,
    content: string
  ): Promise<Artifact> => {
    return apiClient.patch(`/artifacts/${artifactId}/edit_block/`, {
      block_id: blockId,
      content,
    });
  },

  /**
   * Publish artifact
   */
  publish: async (id: string): Promise<Artifact> => {
    return apiClient.post(`/artifacts/${id}/publish/`, {});
  },

  /**
   * Generate research artifact
   */
  generateResearch: async (caseId: string, topic: string): Promise<{
    task_id: string;
    status: string;
  }> => {
    return apiClient.post('/artifacts/generate_research/', {
      case_id: caseId,
      topic,
    });
  },

  /**
   * Generate critique artifact
   */
  generateCritique: async (
    caseId: string,
    targetSignalId: string
  ): Promise<{
    task_id: string;
    status: string;
  }> => {
    return apiClient.post('/artifacts/generate_critique/', {
      case_id: caseId,
      target_signal_id: targetSignalId,
    });
  },

  /**
   * Generate brief artifact
   */
  generateBrief: async (caseId: string): Promise<{
    task_id: string;
    status: string;
  }> => {
    return apiClient.post('/artifacts/generate_brief/', {
      case_id: caseId,
    });
  },
};
