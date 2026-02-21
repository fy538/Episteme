/**
 * TypeScript types for chat-related models
 */

import type { RichCard } from './cards';

export interface ChatThread {
  id: string;
  title: string;
  title_manually_edited?: boolean;
  thread_type?: 'general' | 'research' | 'inquiry' | 'document';
  primary_case?: string;
  project?: string | null;
  user: string;
  archived?: boolean;
  metadata?: Record<string, any>;
  message_count?: number;
  latest_message?: {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at: string;
  } | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  thread: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  content_type?: string;
  structured_content?: RichCard;
  is_rich_content?: boolean;
  event_id: string;
  metadata: Record<string, any>;
  source_chunks?: SourceChunk[];
  created_at: string;
}

// ===== Inline Action Cards =====

/**
 * Types of inline action cards that appear after messages
 */
export type InlineCardType =
  | 'case_creation_prompt'
  | 'case_preview'
  | 'inquiry_resolution'
  | 'research_results'
  | 'inquiry_focus_prompt'
  | 'plan_diff_proposal'
  | 'orientation_diff_proposal'
  | 'position_update_proposal'
  | 'tool_executed'
  | 'tool_confirmation';

/**
 * An action card that appears inline after a message
 */
export interface InlineActionCard {
  id: string;
  type: InlineCardType;
  afterMessageId: string;
  data: Record<string, unknown>;
  dismissed?: boolean;
  createdAt?: string;
}

/**
 * Data payload for case creation prompt card
 */
export interface CaseCreationPromptData {
  suggestedTitle?: string;
  keyQuestions?: string[];
  /** AI-generated reason for suggesting case creation */
  aiReason?: string;
}

/**
 * Data payload for case preview card (shown after analysis)
 */
export interface CasePreviewData {
  suggestedTitle: string;
  positionDraft: string;
  keyQuestions: string[];
  assumptions: string[];
  confidence: number;
  correlationId: string;
  /** Full analysis object needed for case creation */
  analysis: Record<string, unknown>;
  /** Decision criteria extracted from analysis */
  decisionCriteria?: Array<{ criterion: string; measurable?: string }>;
  /** Per-assumption test strategies from analysis */
  assumptionTestStrategies?: Record<string, string>;
}

/**
 * Data payload for inquiry resolution prompt card
 */
export interface InquiryResolutionPromptData {
  inquiryId: string;
  inquiryTitle: string;
  suggestedConclusion?: string;
  /** AI-generated reason for suggesting resolution */
  aiReason?: string;
}

/**
 * Data payload for research results card
 */
export interface ResearchResultsData {
  researchId: string;
  title: string;
  summary: string;
  sourceCount: number;
}

/**
 * Data payload for inquiry focus prompt card
 */
export interface InquiryFocusPromptData {
  inquiryId: string;
  inquiryTitle: string;
  matchedTopic: string;
  /** AI-generated reason for suggesting focus */
  aiReason?: string;
}

// ===== RAG Source Citations =====

/**
 * A document chunk used as RAG context, for citation rendering
 */
export interface SourceChunk {
  index: number;          // Matches [N] in response (0-indexed)
  chunk_id: string;
  document_id: string;
  document_title: string;
  chunk_index: number;
  excerpt: string;
  similarity?: number;
}

// ===== AI Action Hints =====

/**
 * Types of action hints the AI can suggest
 */
export type ActionHintType =
  | 'suggest_case'
  | 'suggest_inquiry'
  | 'suggest_resolution'
  | 'suggest_plan_diff';

/**
 * An action hint from the AI suggesting what the user might do next
 */
export interface ActionHint {
  type: ActionHintType;
  reason: string;
  data: Record<string, unknown>;
}

/**
 * Data payload for plan diff proposal card
 */
export interface PlanDiffProposalData {
  diffSummary: string;
  proposedContent: Record<string, unknown>;
  diffData: {
    added_assumptions?: Array<{ text: string; risk_level: string }>;
    removed_assumptions?: string[];
    updated_assumptions?: Array<{ id: string; status: string; evidence_summary?: string }>;
    added_criteria?: Array<{ text: string }>;
    removed_criteria?: string[];
    updated_criteria?: Array<{ id: string; is_met: boolean }>;
    stage_change?: { from: string; to: string; rationale: string };
  };
}

/**
 * Data payload for orientation diff proposal card
 */
export interface OrientationDiffProposalData {
  orientationId: string;
  diffSummary: string;
  proposedState: {
    lead_text: string;
    lens_type: string;
    findings: Array<{
      id: string;
      insight_type: string;
      title: string;
      content: string;
      status: string;
      confidence: number;
      action_type?: string;
    }>;
    angles: Array<{
      id: string;
      title: string;
    }>;
  };
  diffData: {
    update_lead?: string;
    suggest_lens_change?: string;
    added_findings?: Array<{ type: string; title: string; content: string; action_type?: string }>;
    updated_findings?: Array<{ id: string; title?: string; content?: string; status?: string }>;
    removed_finding_ids?: string[];
    added_angles?: Array<{ title: string }>;
    removed_angle_ids?: string[];
  };
}

/**
 * Data payload for position update proposal card
 */
export interface PositionUpdateProposalData {
  proposals: Array<{ fact: string; reason: string }>;
  caseId: string;
  currentPosition: string;
  /** Message ID where the proposal is stored (for cleanup on accept/dismiss) */
  messageId?: string;
}

// ===== Tool Action Cards =====

/**
 * Data payload for tool_executed card (auto-executed tools)
 */
export interface ToolExecutedData {
  tool: string;
  displayName: string;
  success: boolean;
  output: Record<string, unknown>;
  error?: string;
}

/**
 * Data payload for tool_confirmation card (requires user approval)
 */
export interface ToolConfirmationData {
  tool: string;
  displayName: string;
  params: Record<string, unknown>;
  reason: string;
  confirmationId: string;
}

