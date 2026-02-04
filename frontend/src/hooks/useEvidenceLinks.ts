/**
 * useEvidenceLinks - Hook for managing evidence links in documents
 *
 * Provides:
 * - Claim extraction and evidence linking
 * - Coverage metrics
 * - Inline citation generation
 */

import { useState, useCallback } from 'react';
import { documentsAPI } from '@/lib/api/documents';

interface LinkedSignal {
  signal_id: string;
  signal_type: string;
  relevance: number;
  excerpt: string;
}

interface LinkedClaim {
  id: string;
  text: string;
  location: string;
  claim_type: 'fact' | 'assumption' | 'opinion' | 'prediction' | 'conclusion';
  linked_signals: LinkedSignal[];
  confidence: number;
  is_substantiated: boolean;
  suggestion?: string;
}

interface EvidenceSummary {
  total_claims: number;
  substantiated: number;
  unsubstantiated: number;
  average_confidence: number;
}

interface UseEvidenceLinksOptions {
  documentId: string;
  autoLoad?: boolean;
}

interface UseEvidenceLinksReturn {
  // State
  claims: LinkedClaim[];
  summary: EvidenceSummary | null;
  evidenceCoverage: number;
  isLoading: boolean;
  error: string | null;

  // Actions
  loadEvidenceLinks: () => Promise<void>;
  addCitations: (save?: boolean) => Promise<string | null>;

  // Computed
  substantiatedClaims: LinkedClaim[];
  unsubstantiatedClaims: LinkedClaim[];
  highConfidenceClaims: LinkedClaim[];
  lowConfidenceClaims: LinkedClaim[];

  // Helpers
  getClaimById: (id: string) => LinkedClaim | undefined;
  getClaimsForSignal: (signalId: string) => LinkedClaim[];
}

export function useEvidenceLinks({
  documentId,
  autoLoad = false,
}: UseEvidenceLinksOptions): UseEvidenceLinksReturn {
  const [claims, setClaims] = useState<LinkedClaim[]>([]);
  const [summary, setSummary] = useState<EvidenceSummary | null>(null);
  const [evidenceCoverage, setEvidenceCoverage] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEvidenceLinks = useCallback(async () => {
    if (!documentId) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await documentsAPI.getEvidenceLinks(documentId);
      setClaims(result.claims as LinkedClaim[]);
      setSummary(result.summary);
      setEvidenceCoverage(result.evidence_coverage);
    } catch (err) {
      console.error('Failed to load evidence links:', err);
      setError(err instanceof Error ? err.message : 'Failed to load evidence links');
    } finally {
      setIsLoading(false);
    }
  }, [documentId]);

  const addCitations = useCallback(
    async (save: boolean = false): Promise<string | null> => {
      if (!documentId) return null;

      setIsLoading(true);
      setError(null);

      try {
        const result = await documentsAPI.addCitations(documentId, save);
        return result.cited_content;
      } catch (err) {
        console.error('Failed to add citations:', err);
        setError(err instanceof Error ? err.message : 'Failed to add citations');
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [documentId]
  );

  // Auto-load on mount if enabled
  // useEffect(() => {
  //   if (autoLoad && documentId) {
  //     loadEvidenceLinks();
  //   }
  // }, [autoLoad, documentId, loadEvidenceLinks]);

  // Computed values
  const substantiatedClaims = claims.filter((c) => c.is_substantiated);
  const unsubstantiatedClaims = claims.filter((c) => !c.is_substantiated);
  const highConfidenceClaims = claims.filter((c) => c.confidence >= 0.7);
  const lowConfidenceClaims = claims.filter((c) => c.confidence < 0.5);

  const getClaimById = useCallback(
    (id: string) => claims.find((c) => c.id === id),
    [claims]
  );

  const getClaimsForSignal = useCallback(
    (signalId: string) =>
      claims.filter((c) =>
        c.linked_signals.some((s) => s.signal_id === signalId)
      ),
    [claims]
  );

  return {
    claims,
    summary,
    evidenceCoverage,
    isLoading,
    error,

    loadEvidenceLinks,
    addCitations,

    substantiatedClaims,
    unsubstantiatedClaims,
    highConfidenceClaims,
    lowConfidenceClaims,

    getClaimById,
    getClaimsForSignal,
  };
}
