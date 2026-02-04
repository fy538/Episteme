/**
 * useUserConfidence - Hook for user's self-assessed confidence
 *
 * The user owns their confidence assessment, not the system.
 * This is subjective and that's the point.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { casesAPI } from '@/lib/api/cases';

interface UseUserConfidenceOptions {
  caseId: string;
  initialConfidence?: number | null;
  initialWhatWouldChange?: string;
  debounceMs?: number;
}

interface UseUserConfidenceReturn {
  // State
  confidence: number | null;
  whatWouldChangeMind: string;
  updatedAt: Date | null;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;

  // Actions
  setConfidence: (value: number, whatWouldChange?: string) => Promise<void>;
  setWhatWouldChangeMind: (value: string) => void;
  save: () => Promise<void>;
}

export function useUserConfidence({
  caseId,
  initialConfidence,
  initialWhatWouldChange = '',
  debounceMs = 1000,
}: UseUserConfidenceOptions): UseUserConfidenceReturn {
  const [confidence, setConfidenceState] = useState<number | null>(initialConfidence ?? null);
  const [whatWouldChangeMind, setWhatWouldChangeMindState] = useState(initialWhatWouldChange);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Debounce timer ref
  const saveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Pending values for debounced save
  const pendingRef = useRef<{ confidence: number | null; whatWouldChange: string }>({
    confidence: initialConfidence ?? null,
    whatWouldChange: initialWhatWouldChange,
  });

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
    };
  }, []);

  // Save function
  const save = useCallback(async () => {
    if (pendingRef.current.confidence === null) return;

    setIsSaving(true);
    setError(null);

    try {
      const result = await casesAPI.setUserConfidence(
        caseId,
        pendingRef.current.confidence,
        pendingRef.current.whatWouldChange
      );

      setConfidenceState(result.user_confidence);
      setWhatWouldChangeMindState(result.what_would_change_mind);
      setUpdatedAt(new Date(result.user_confidence_updated_at));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save confidence');
      console.error('Failed to save user confidence:', err);
    } finally {
      setIsSaving(false);
    }
  }, [caseId]);

  // Debounced save
  const debouncedSave = useCallback(() => {
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
    }

    saveTimerRef.current = setTimeout(() => {
      save();
    }, debounceMs);
  }, [save, debounceMs]);

  // Set confidence (triggers debounced save)
  const setConfidence = useCallback(
    async (value: number, whatWouldChange?: string) => {
      setConfidenceState(value);
      pendingRef.current.confidence = value;

      if (whatWouldChange !== undefined) {
        setWhatWouldChangeMindState(whatWouldChange);
        pendingRef.current.whatWouldChange = whatWouldChange;
      }

      debouncedSave();
    },
    [debouncedSave]
  );

  // Set what would change mind (updates local state, will be saved with next confidence change)
  const setWhatWouldChangeMind = useCallback((value: string) => {
    setWhatWouldChangeMindState(value);
    pendingRef.current.whatWouldChange = value;
  }, []);

  return {
    confidence,
    whatWouldChangeMind,
    updatedAt,
    isLoading,
    isSaving,
    error,
    setConfidence,
    setWhatWouldChangeMind,
    save,
  };
}
