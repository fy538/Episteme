/**
 * Type definitions for Reasoning Companion
 *
 * Core types for the two-voice chat experience:
 * - Chat modes (casual, case, inquiry_focus)
 * - Session receipts (accomplishments tracking)
 * - Background work items
 * - Case state summary
 * - Full companion panel state
 */

// ===== Chat Mode System =====

/**
 * Chat modes determining the context and behavior
 */
export type ChatMode = 'casual' | 'case' | 'inquiry_focus' | 'graph' | 'orientation';

/**
 * Context for the current chat mode
 */
export interface ModeContext {
  mode: ChatMode;
  caseId?: string;
  caseName?: string;
  inquiryId?: string;
  inquiryTitle?: string;
}

// ===== Session Receipts =====

/**
 * Types of session accomplishments that can be recorded
 */
export type SessionReceiptType =
  | 'case_created'
  | 'inquiry_resolved'
  | 'research_completed';

/**
 * A record of something accomplished during the session
 */
export interface SessionReceipt {
  id: string;
  type: SessionReceiptType;
  title: string;
  timestamp: string;
  detail?: string;
  relatedCaseId?: string;
}

// ===== Background Work =====

/**
 * Types of background work
 */
export type BackgroundWorkType = 'research' | 'analysis' | 'extraction';

/**
 * An item representing work happening in the background
 */
export interface BackgroundWorkItem {
  id: string;
  type: BackgroundWorkType;
  title: string;
  status: 'running' | 'completed';
  progress?: number;
  startedAt?: string;
  completedAt?: string;
}

// ===== Case State =====

/**
 * Summary of case state when in case mode
 */
export interface CaseState {
  caseId: string;
  caseName: string;
  inquiries: {
    open: number;
    resolved: number;
  };
  assumptions: {
    validated: number;
    unvalidated: number;
  };
  evidenceGaps: number;
}

// ===== Conversation Structure =====

/**
 * Structure types that the companion can generate
 */
export type StructureType =
  | 'assumption_surface'
  | 'angle_map'
  | 'decision_tree'
  | 'checklist'
  | 'comparison'
  | 'exploration_map'
  | 'flow'
  | 'constraint_list'
  | 'pros_cons'
  | 'concept_map';

/**
 * The organic conversation structure from the companion
 */
export interface ConversationStructure {
  id: string;
  thread_id?: string;
  version: number;
  structure_type: StructureType;
  content: Record<string, unknown>;
  established: string[];
  open_questions: string[];
  eliminated: string[];
  context_summary: string;
  updated_at: string | null;
}

/**
 * Research result from background companion research
 */
export interface ResearchResult {
  id: string;
  question: string;
  answer: string;
  sources: Array<{
    type: 'web' | 'project_chunk';
    title: string;
    snippet: string;
    url?: string;
    chunk_id?: string;
  }>;
  status: 'researching' | 'complete' | 'failed';
  surfaced: boolean;
  created_at?: string;
}

/**
 * Context transferred from companion to case creation
 */
export interface CompanionCaseContext {
  suggested_title: string;
  decision_question: string;
  reason: string;
  companion_state: {
    established: string[];
    open_questions: string[];
    eliminated: string[];
    structure_snapshot: Record<string, unknown>;
    structure_type: string;
  };
}

// ===== Conversation Episodes =====

/**
 * Topic shift type for an episode
 */
export type EpisodeShiftType = 'initial' | 'continuous' | 'partial_shift' | 'discontinuous';

/**
 * A topically coherent conversation segment
 */
export interface ConversationEpisode {
  id: string;
  episode_index: number;
  topic_label: string;
  content_summary: string;
  message_count: number;
  shift_type: EpisodeShiftType;
  sealed: boolean;
  sealed_at: string | null;
  start_message_id: string | null;
  end_message_id: string | null;
  created_at: string;
}

/**
 * Compact current episode info attached to companion_structure SSE payload
 */
export interface CurrentEpisodeInfo {
  id: string;
  episode_index: number;
  topic_label: string;
  sealed: boolean;
}

/**
 * SSE event emitted when an episode is sealed due to topic shift
 */
export interface EpisodeSealedEvent {
  episode: ConversationEpisode;
  new_episode?: {
    id: string;
    episode_index: number;
    topic_label: string;
  } | null;
}

// ===== Companion State =====

/**
 * Full state for the companion panel
 */
export interface CompanionState {
  mode: ModeContext;
  thinking: {
    content: string;
    isStreaming: boolean;
  };
  status: {
    inProgress: BackgroundWorkItem[];
    justCompleted: BackgroundWorkItem[];
  };
  sessionReceipts: SessionReceipt[];
  caseState?: CaseState;
  conversationStructure?: ConversationStructure;
}
