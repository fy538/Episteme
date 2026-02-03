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
  type: 'reflection_chunk' | 'reflection_complete' | 'background_update' | 'confidence_change';
  text?: string;
  delta?: string;  // For streaming chunks
  activity?: BackgroundActivity;
  patterns?: Reflection['patterns'];
}
