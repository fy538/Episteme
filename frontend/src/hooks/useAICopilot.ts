/**
 * useAICopilot - Hook for AI co-pilot features in case workspace
 *
 * Provides:
 * - Gap analysis ("What am I missing?")
 * - Inquiry suggestions
 * - Evidence source suggestions
 * - Case-aware AI assistance
 */

import { useState, useCallback } from 'react';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';

// Types
interface InquirySuggestion {
  title: string;
  description: string;
  reason: string;
  priority: number;
}

interface GapAnalysis {
  missing_perspectives: string[];
  unvalidated_assumptions: string[];
  contradictions: string[];
  evidence_gaps: string[];
  recommendations: string[];
}

interface EvidenceSuggestion {
  inquiry_id: string;
  suggestion: string;
  source_type: string;
  why_helpful: string;
  how_to_find: string;
}

type CopilotAction = 'idle' | 'analyzing-gaps' | 'suggesting-inquiries' | 'suggesting-evidence';

interface UseAICopilotOptions {
  caseId: string;
  onInquiryCreated?: (inquiryId: string) => void;
}

interface UseAICopilotReturn {
  // State
  isLoading: boolean;
  action: CopilotAction;
  error: string | null;

  // Gap analysis
  gapAnalysis: GapAnalysis | null;
  analyzeGaps: () => Promise<void>;

  // Inquiry suggestions
  inquirySuggestions: InquirySuggestion[];
  suggestInquiries: () => Promise<void>;
  acceptInquirySuggestion: (suggestion: InquirySuggestion) => Promise<void>;
  dismissInquirySuggestion: (index: number) => void;

  // Evidence suggestions
  evidenceSuggestions: EvidenceSuggestion[];
  suggestEvidence: (inquiryId: string) => Promise<void>;

  // General
  clearAll: () => void;
}

export function useAICopilot({
  caseId,
  onInquiryCreated,
}: UseAICopilotOptions): UseAICopilotReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [action, setAction] = useState<CopilotAction>('idle');
  const [error, setError] = useState<string | null>(null);

  const [gapAnalysis, setGapAnalysis] = useState<GapAnalysis | null>(null);
  const [inquirySuggestions, setInquirySuggestions] = useState<InquirySuggestion[]>([]);
  const [evidenceSuggestions, setEvidenceSuggestions] = useState<EvidenceSuggestion[]>([]);

  // Gap analysis - "What am I missing?"
  const analyzeGaps = useCallback(async () => {
    if (!caseId) return;

    setIsLoading(true);
    setAction('analyzing-gaps');
    setError(null);

    try {
      const result = await casesAPI.getBlindSpotPrompts(caseId);
      // Extract gap analysis from blind spot prompts response
      setGapAnalysis({
        missing_perspectives: result.missing_perspectives,
        unvalidated_assumptions: result.unvalidated_assumptions,
        contradictions: result.contradictions,
        evidence_gaps: result.evidence_gaps,
        recommendations: result.recommendations,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze gaps');
      console.error('Gap analysis failed:', err);
    } finally {
      setIsLoading(false);
      setAction('idle');
    }
  }, [caseId]);

  // Inquiry suggestions
  const suggestInquiries = useCallback(async () => {
    if (!caseId) return;

    setIsLoading(true);
    setAction('suggesting-inquiries');
    setError(null);

    try {
      const result = await casesAPI.suggestInquiries(caseId);
      setInquirySuggestions(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get suggestions');
      console.error('Inquiry suggestion failed:', err);
    } finally {
      setIsLoading(false);
      setAction('idle');
    }
  }, [caseId]);

  // Accept an inquiry suggestion
  const acceptInquirySuggestion = useCallback(
    async (suggestion: InquirySuggestion) => {
      if (!caseId) return;

      try {
        // Create description that includes the reason
        const fullDescription = suggestion.description
          ? `${suggestion.description}\n\nReason: ${suggestion.reason}`
          : suggestion.reason;

        const inquiry = await inquiriesAPI.create({
          case: caseId,
          title: suggestion.title,
          description: fullDescription,
          status: 'open',
        });

        // Remove from suggestions
        setInquirySuggestions((prev) =>
          prev.filter((s) => s.title !== suggestion.title)
        );

        onInquiryCreated?.(inquiry.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to create inquiry');
        console.error('Failed to create inquiry:', err);
      }
    },
    [caseId, onInquiryCreated]
  );

  // Dismiss an inquiry suggestion
  const dismissInquirySuggestion = useCallback((index: number) => {
    setInquirySuggestions((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // Evidence suggestions for a specific inquiry
  const suggestEvidence = useCallback(
    async (inquiryId: string) => {
      if (!caseId) return;

      setIsLoading(true);
      setAction('suggesting-evidence');
      setError(null);

      try {
        const result = await casesAPI.suggestEvidenceSources(caseId, inquiryId);
        setEvidenceSuggestions(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to get evidence suggestions');
        console.error('Evidence suggestion failed:', err);
      } finally {
        setIsLoading(false);
        setAction('idle');
      }
    },
    [caseId]
  );

  // Clear all suggestions
  const clearAll = useCallback(() => {
    setGapAnalysis(null);
    setInquirySuggestions([]);
    setEvidenceSuggestions([]);
    setError(null);
  }, []);

  return {
    isLoading,
    action,
    error,

    gapAnalysis,
    analyzeGaps,

    inquirySuggestions,
    suggestInquiries,
    acceptInquirySuggestion,
    dismissInquirySuggestion,

    evidenceSuggestions,
    suggestEvidence,

    clearAll,
  };
}

/**
 * Get action label for display
 */
export function getCopilotActionLabel(action: CopilotAction): string {
  switch (action) {
    case 'analyzing-gaps':
      return 'Analyzing gaps...';
    case 'suggesting-inquiries':
      return 'Generating suggestions...';
    case 'suggesting-evidence':
      return 'Finding evidence sources...';
    default:
      return '';
  }
}
