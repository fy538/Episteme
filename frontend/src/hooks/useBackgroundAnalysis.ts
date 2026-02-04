/**
 * useBackgroundAnalysis - Hook for continuous background document analysis
 *
 * Provides:
 * - Automatic analysis when content changes
 * - Cached results with smart invalidation
 * - Health score and issue tracking
 * - Proactive suggestions surfacing
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { documentsAPI } from '@/lib/api/documents';

interface AnalysisIssue {
  type: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  location: string;
}

interface AnalysisSuggestion {
  id: string;
  type: string;
  content: string;
  reason: string;
  confidence: number;
}

interface EvidenceGap {
  claim: string;
  location: string;
  suggestion: string;
}

interface AnalysisResult {
  analyzed_at: string;
  content_hash: string;
  health_score: number;
  issues: AnalysisIssue[];
  suggestions: AnalysisSuggestion[];
  evidence_gaps: EvidenceGap[];
  unlinked_claims: Array<{
    text: string;
    location: string;
    potential_sources: string[];
  }>;
  metrics: {
    claim_count: number;
    linked_claim_count: number;
    assumption_count: number;
    validated_assumption_count: number;
  };
}

interface UseBackgroundAnalysisOptions {
  documentId: string;
  enabled?: boolean;
  pollInterval?: number; // ms, 0 to disable polling
  analyzeOnMount?: boolean;
}

interface UseBackgroundAnalysisReturn {
  analysis: AnalysisResult | null;
  healthScore: number | null;
  issues: AnalysisIssue[];
  suggestions: AnalysisSuggestion[];
  evidenceGaps: EvidenceGap[];
  isAnalyzing: boolean;
  lastAnalyzedAt: string | null;
  triggerAnalysis: (force?: boolean) => Promise<void>;
  getHealthSummary: () => {
    score: number;
    label: string;
    color: string;
    issueCount: number;
  } | null;
}

export function useBackgroundAnalysis({
  documentId,
  enabled = true,
  pollInterval = 0, // Disabled by default
  analyzeOnMount = true,
}: UseBackgroundAnalysisOptions): UseBackgroundAnalysisReturn {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const lastContentHashRef = useRef<string | null>(null);
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const triggerAnalysis = useCallback(
    async (force: boolean = false) => {
      if (!documentId || !enabled) return;

      setIsAnalyzing(true);

      try {
        const result = await documentsAPI.getBackgroundAnalysis(documentId, force);
        setAnalysis(result);
        lastContentHashRef.current = result.content_hash;
      } catch (err) {
        console.error('Background analysis failed:', err);
      } finally {
        setIsAnalyzing(false);
      }
    },
    [documentId, enabled]
  );

  // Initial analysis on mount
  useEffect(() => {
    if (analyzeOnMount && documentId && enabled) {
      // First try to get cached health
      documentsAPI.getDocumentHealth(documentId).then((health) => {
        if (health.health_score !== null) {
          // We have cached data, use it initially
          setAnalysis((prev) =>
            prev
              ? prev
              : ({
                  health_score: health.health_score!,
                  analyzed_at: health.analyzed_at || '',
                  content_hash: '',
                  issues: [],
                  suggestions: [],
                  evidence_gaps: [],
                  unlinked_claims: [],
                  metrics: {
                    claim_count: 0,
                    linked_claim_count: 0,
                    assumption_count: 0,
                    validated_assumption_count: 0,
                  },
                } as AnalysisResult)
          );
        }
        // Then trigger full analysis
        triggerAnalysis();
      });
    }
  }, [documentId, enabled, analyzeOnMount, triggerAnalysis]);

  // Polling for continuous analysis
  useEffect(() => {
    if (!enabled || pollInterval <= 0 || !documentId) return;

    const poll = () => {
      pollTimeoutRef.current = setTimeout(async () => {
        await triggerAnalysis();
        poll();
      }, pollInterval);
    };

    poll();

    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, [enabled, pollInterval, documentId, triggerAnalysis]);

  const getHealthSummary = useCallback(() => {
    if (!analysis) return null;

    const score = analysis.health_score;
    let label: string;
    let color: string;

    if (score >= 80) {
      label = 'Excellent';
      color = 'text-success-600';
    } else if (score >= 60) {
      label = 'Good';
      color = 'text-success-500';
    } else if (score >= 40) {
      label = 'Needs Work';
      color = 'text-warning-600';
    } else {
      label = 'Critical';
      color = 'text-error-600';
    }

    return {
      score,
      label,
      color,
      issueCount: analysis.issues.length,
    };
  }, [analysis]);

  return {
    analysis,
    healthScore: analysis?.health_score ?? null,
    issues: analysis?.issues ?? [],
    suggestions: analysis?.suggestions ?? [],
    evidenceGaps: analysis?.evidence_gaps ?? [],
    isAnalyzing,
    lastAnalyzedAt: analysis?.analyzed_at ?? null,
    triggerAnalysis,
    getHealthSummary,
  };
}
