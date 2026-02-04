/**
 * Type definitions for Reasoning Companion
 */

export interface Reflection {
  id: string;
  text: string;
  trigger_type: 'user_message' | 'document_upload' | 'contradiction_detected' | 'periodic' | 'confidence_change';
  patterns: {
    ungrounded_assumptions: Array<{ id: string; text: string; mentioned_times: number }>;
    contradictions: Array<{ signal_id: string; signal_text: string; contradicts_id: string; contradicts_text: string }>;
    strong_claims: Array<{ id: string; text: string; evidence_count: number; avg_confidence: number }>;
    recurring_themes: Array<{ theme: string; count: number; signal_ids: string[] }>;
    missing_considerations: Array<{ id: string; text: string }>;
  };
  created_at: string;
}

export interface BackgroundActivity {
  signals_extracted: {
    count: number;
    by_type: Record<string, Array<{ text: string; status: string }>>;
    items: Array<{ text: string; type: string }>;
  };
  evidence_linked: {
    count: number;
    sources: string[];
  };
  connections_built: {
    count: number;
  };
  confidence_updates: Array<{
    inquiry_id: string;
    title: string;
    old: number | null;
    new: number;
  }>;
}

export interface CompanionEvent {
  type: 'reflection_chunk' | 'reflection_complete' | 'background_update' | 'confidence_change' | 'status';
  text?: string;
  delta?: string;  // For streaming chunks
  message?: string;  // For status events
  activity?: BackgroundActivity;
  patterns?: Reflection['patterns'];
}

/**
 * Unified stream state for combined chat + companion streaming
 */
export interface UnifiedStreamState {
  /** Whether unified streaming is enabled */
  enabled: boolean;
  /** Current reflection text from unified stream */
  reflectionText: string;
  /** Whether reflection is streaming */
  isReflectionStreaming: boolean;
  /** Current reflection patterns */
  patterns: Reflection['patterns'] | null;
}

/**
 * Action types that can be performed from the companion
 */
export type ActionType =
  | 'research_assumption'
  | 'validate_assumptions'
  | 'organize_questions'
  | 'create_case'
  | 'create_inquiry';

/**
 * Status of a signal (for validation tracking)
 */
export type SignalValidationStatus =
  | 'pending'
  | 'validating'
  | 'validated'
  | 'refuted'
  | 'partially_true'
  | 'dismissed';

/**
 * Enhanced signal with validation info for companion display
 */
export interface CompanionSignal {
  id: string;
  type: string;
  text: string;
  confidence: number;
  validationStatus: SignalValidationStatus;
  validationResult?: {
    verdict: 'true' | 'false' | 'partial';
    summary: string;
    sources?: string[];
  };
  createdAt: string;
}

/**
 * Active action being performed
 */
export interface ActiveAction {
  id: string;
  type: ActionType;
  status: 'running' | 'complete' | 'error';
  target: string;  // What's being acted on (e.g., assumption text)
  targetIds?: string[];  // Signal IDs if applicable
  progress: number;  // 0-100
  steps: ActionStep[];
  result?: ActionResult;
  error?: string;
  startedAt: string;
}

export interface ActionStep {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'complete' | 'error';
}

export interface ActionResult {
  verdict?: 'true' | 'false' | 'partial';
  summary: string;
  details?: string;
  sources?: Array<{ title: string; url?: string }>;
  updatedSignals?: string[];  // IDs of signals that were updated
}

/**
 * Suggested action based on patterns
 */
export interface SuggestedAction {
  id: string;
  type: ActionType;
  label: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  targetIds?: string[];
  targetCount?: number;
  /** Suggested title for case/inquiry creation */
  suggestedTitle?: string;
}
