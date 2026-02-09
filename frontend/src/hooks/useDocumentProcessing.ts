/**
 * Hook for streaming document processing progress via SSE.
 *
 * Replaces the old polling-based useDocumentDelta hook with real-time
 * SSE streaming. Connects to GET /api/documents/{id}/processing-stream/
 * and tracks stage-by-stage progress.
 */

'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { documentsAPI } from '@/lib/api/documents';

export interface ProcessingProgress {
  stage: string;
  stage_label: string;
  stage_index: number;
  total_stages: number;
  counts: Record<string, number>;
  started_at?: string;
  updated_at?: string;
  error: string | null;
}

interface UseDocumentProcessingReturn {
  progress: ProcessingProgress | null;
  isProcessing: boolean;
  isComplete: boolean;
  isFailed: boolean;
  error: string | null;
  abort: (() => void) | null;
}

export function useDocumentProcessing(
  documentId: string | null
): UseDocumentProcessingReturn {
  const [progress, setProgress] = useState<ProcessingProgress | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setProgress(null);
    setIsComplete(false);
    setIsFailed(false);
    setError(null);
  }, []);

  useEffect(() => {
    if (!documentId) {
      reset();
      return;
    }

    // Reset state for new document
    reset();

    const abortController = new AbortController();
    abortRef.current = abortController;

    documentsAPI
      .streamProcessing(
        documentId,
        (event) => {
          if (event.event === 'progress' || event.event === 'completed' || event.event === 'failed') {
            const data = event.data as ProcessingProgress;
            setProgress(data);

            if (data.stage === 'completed') {
              setIsComplete(true);
            } else if (data.stage === 'failed') {
              setIsFailed(true);
              setError(data.error || data.stage_label || 'Processing failed');
            }
          } else if (event.event === 'timeout') {
            setIsFailed(true);
            setError('Processing timed out');
          }
        },
        abortController.signal,
      )
      .catch((err) => {
        // Ignore abort errors
        if (err instanceof DOMException && err.name === 'AbortError') return;
        console.error('Processing stream error:', err);
        setIsFailed(true);
        setError(err instanceof Error ? err.message : 'Stream connection failed');
      });

    return () => {
      abortController.abort();
      abortRef.current = null;
    };
  }, [documentId, reset]);

  const isProcessing = !!progress && !isComplete && !isFailed;

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  return { progress, isProcessing, isComplete, isFailed, error, abort: isProcessing ? abort : null };
}
