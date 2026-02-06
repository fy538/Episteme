/**
 * useCaseReadiness Hook
 *
 * Computes and returns the readiness state for a case.
 * Aggregates inquiry completion, tensions, and blind spots.
 *
 * Connects to real backend APIs for:
 * - Evidence landscape (inquiry counts)
 * - Readiness checklist (checklist progress)
 * - Blind spot prompts / gap analysis (tensions + blind spots)
 */

import { useState, useEffect, useCallback } from 'react';
import { casesAPI } from '@/lib/api/cases';
import {
  transformBlindSpotToIntelligenceItem,
  transformContradictionToTension,
  calculateReadinessScore,
} from '@/lib/utils/intelligence-transforms';
import type { CaseReadiness, IntelligenceItem } from '@/lib/types/intelligence';
import type { BlindSpotPrompt } from '@/lib/types/case';

interface UseCaseReadinessOptions {
  caseId: string;
  caseTitle?: string;
}

export function useCaseReadiness(options: UseCaseReadinessOptions): CaseReadiness & {
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
} {
  const { caseId, caseTitle = '' } = options;

  const [readiness, setReadiness] = useState<CaseReadiness>({
    caseId,
    caseTitle,
    score: 0,
    inquiries: { total: 0, resolved: 0, investigating: 0, open: 0 },
    tensionsCount: 0,
    blindSpotsCount: 0,
    isReady: false,
    blockers: [],
  });

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReadiness = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch all data in parallel
      const [landscape, checklist, gaps] = await Promise.all([
        casesAPI.getEvidenceLandscape(caseId).catch(() => null),
        casesAPI.getReadinessChecklist(caseId).catch(() => null),
        casesAPI.getBlindSpotPrompts(caseId).catch(() => null),
      ]);

      // Extract inquiry counts from evidence landscape
      const inquiries = landscape?.inquiries || { total: 0, resolved: 0, investigating: 0, open: 0 };

      // Extract checklist progress
      const checklistProgress = checklist?.progress || { required: 0, required_completed: 0, completed: 0, total: 0 };

      // Count tensions (contradictions) and blind spots
      const contradictions = gaps?.contradictions || [];
      const blindSpotPrompts = gaps?.prompts || [];
      const tensionsCount = contradictions.length;
      const blindSpotsCount = blindSpotPrompts.length;

      // Calculate score using shared utility
      const score = calculateReadinessScore(
        inquiries,
        checklistProgress,
        tensionsCount,
        blindSpotsCount
      );

      // Transform to blockers using shared utilities
      const blockers: IntelligenceItem[] = [
        // Tensions first (blocking priority)
        ...contradictions.map((c: string) => transformContradictionToTension(c, caseId, caseTitle)),
        // Then blind spots
        ...blindSpotPrompts.map((p: BlindSpotPrompt) => transformBlindSpotToIntelligenceItem(p, caseId, caseTitle)),
      ];

      setReadiness({
        caseId,
        caseTitle,
        score,
        inquiries,
        tensionsCount,
        blindSpotsCount,
        isReady: score >= 90 && tensionsCount === 0,
        topBlocker: blockers[0] || undefined,
        blockers,
      });
    } catch (err) {
      console.error('Failed to fetch case readiness:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch readiness data');

      // Set defaults on error
      setReadiness({
        caseId,
        caseTitle,
        score: 0,
        inquiries: { total: 0, resolved: 0, investigating: 0, open: 0 },
        tensionsCount: 0,
        blindSpotsCount: 0,
        isReady: false,
        blockers: [],
      });
    } finally {
      setIsLoading(false);
    }
  }, [caseId, caseTitle]);

  // Initial fetch
  useEffect(() => {
    fetchReadiness();
  }, [fetchReadiness]);

  // Refresh function
  const refresh = useCallback(() => {
    fetchReadiness();
  }, [fetchReadiness]);

  return {
    ...readiness,
    isLoading,
    error,
    refresh,
  };
}

export default useCaseReadiness;
