/**
 * useEvidenceLandscape - Hook for evidence landscape data
 *
 * Replaces useConfidence. Shows evidence counts, not computed scores.
 * The philosophy: show what you have, let the user judge readiness.
 */

import { useState, useEffect, useCallback } from 'react';
import { casesAPI } from '@/lib/api/cases';
import type { EvidenceLandscape } from '@/lib/types/case';

interface UseEvidenceLandscapeOptions {
  caseId: string;
  autoRefresh?: boolean;
  refreshInterval?: number; // ms
}

interface UseEvidenceLandscapeReturn {
  // State
  landscape: EvidenceLandscape | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  refresh: () => Promise<void>;

  // Computed helpers
  totalEvidence: number;
  hasContradictions: boolean;
  untestedAssumptionCount: number;
  openInquiryCount: number;
}

export function useEvidenceLandscape({
  caseId,
  autoRefresh = false,
  refreshInterval = 30000,
}: UseEvidenceLandscapeOptions): UseEvidenceLandscapeReturn {
  const [landscape, setLandscape] = useState<EvidenceLandscape | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!caseId) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await casesAPI.getEvidenceLandscape(caseId);
      setLandscape(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load evidence landscape');
      console.error('Failed to load evidence landscape:', err);
    } finally {
      setIsLoading(false);
    }
  }, [caseId]);

  // Initial load
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh || !refreshInterval) return;

    const interval = setInterval(refresh, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, refresh]);

  // Computed values
  const totalEvidence = landscape
    ? landscape.evidence.supporting +
      landscape.evidence.contradicting +
      landscape.evidence.neutral
    : 0;

  const hasContradictions = (landscape?.evidence.contradicting ?? 0) > 0;
  const untestedAssumptionCount = landscape?.assumptions.untested ?? 0;
  const openInquiryCount = (landscape?.inquiries.open ?? 0) + (landscape?.inquiries.investigating ?? 0);

  return {
    landscape,
    isLoading,
    error,
    refresh,
    totalEvidence,
    hasContradictions,
    untestedAssumptionCount,
    openInquiryCount,
  };
}
