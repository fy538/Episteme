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
  created_at: string;
}

export interface CreateMessageRequest {
  content: string;
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
  | 'plan_diff_proposal';

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
 * Data payload for suggest_case action hint
 */
export interface SuggestCaseHintData {
  suggested_title?: string;
}

/**
 * Data payload for suggest_inquiry action hint
 */
export interface SuggestInquiryHintData {
  question: string;
  topic?: string;
}

/**
 * Data payload for suggest_resolution action hint
 */
export interface SuggestResolutionHintData {
  inquiry_id: string;
  inquiry_title?: string;
  suggested_conclusion?: string;
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

