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
export type ChatMode = 'casual' | 'case' | 'inquiry_focus' | 'graph';

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
}
