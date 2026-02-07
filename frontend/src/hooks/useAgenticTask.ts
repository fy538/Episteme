/**
 * useAgenticTask - Hook for executing complex document editing tasks
 *
 * Provides:
 * - Task execution with planning, execution, and review phases
 * - Progress tracking for each step
 * - Diff preview before applying changes
 * - Ability to accept or reject the result
 */

import { useState, useCallback, useRef } from 'react';
import { documentsAPI } from '@/lib/api/documents';

interface TaskStep {
  id: string;
  description: string;
  status: string;
  action_type: string;
  target_section?: string;
  error?: string;
}

interface TaskChange {
  step_id: string;
  type: string;
  description: string;
  before: string;
  after: string;
}

interface TaskResult {
  task_id: string;
  status: string;
  plan: TaskStep[];
  original_content: string;
  final_content: string;
  diff_summary: string;
  review_notes: string;
  review_score: number;
  changes: TaskChange[];
}

type TaskPhase = 'idle' | 'planning' | 'executing' | 'reviewing' | 'completed' | 'failed';

interface UseAgenticTaskOptions {
  documentId: string;
  onSuccess?: (result: TaskResult) => void;
  onError?: (error: string) => void;
}

interface UseAgenticTaskReturn {
  // State
  phase: TaskPhase;
  result: TaskResult | null;
  error: string | null;
  isRunning: boolean;

  // Actions
  executeTask: (taskDescription: string) => Promise<void>;
  applyResult: () => Promise<void>;
  discardResult: () => void;
  reset: () => void;

  /** Accept a single change by step_id (keeps change, rejects others not yet accepted) */
  acceptChange: (stepId: string) => void;
  /** Reject a single change by step_id */
  rejectChange: (stepId: string) => void;

  // Computed
  plan: TaskStep[];
  changes: TaskChange[];
  /** Changes with per-hunk accept/reject state */
  changeStates: Record<string, 'pending' | 'accepted' | 'rejected'>;
  diffSummary: string;
  reviewScore: number | null;
  reviewNotes: string | null;
}

export function useAgenticTask({
  documentId,
  onSuccess,
  onError,
}: UseAgenticTaskOptions): UseAgenticTaskReturn {
  const [phase, setPhase] = useState<TaskPhase>('idle');
  const [result, setResult] = useState<TaskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [changeStates, setChangeStates] = useState<Record<string, 'pending' | 'accepted' | 'rejected'>>({});
  const [streamPlan, setStreamPlan] = useState<TaskStep[]>([]);
  const abortRef = useRef<{ abort: () => void } | null>(null);

  const executeTask = useCallback(
    async (taskDescription: string) => {
      if (!documentId || !taskDescription.trim()) return;

      setPhase('planning');
      setError(null);
      setResult(null);
      setStreamPlan([]);
      setChangeStates({});

      // Try streaming first, fall back to non-streaming
      const stream = documentsAPI.executeTaskStream(
        documentId,
        taskDescription,
        // onEvent - real-time phase/step updates
        (event) => {
          switch (event.type) {
            case 'phase':
              setPhase(event.data.phase as TaskPhase);
              break;
            case 'plan':
              setStreamPlan(
                (event.data.steps || []).map((s: any) => ({
                  ...s,
                  status: 'pending',
                }))
              );
              break;
            case 'step_start':
              setStreamPlan((prev) =>
                prev.map((s) =>
                  s.id === event.data.step_id ? { ...s, status: 'in_progress' } : s
                )
              );
              break;
            case 'step_complete':
              setStreamPlan((prev) =>
                prev.map((s) =>
                  s.id === event.data.step_id
                    ? { ...s, status: event.data.status, error: event.data.error }
                    : s
                )
              );
              break;
            case 'review':
              // Review score comes before done
              break;
          }
        },
        // onDone
        (taskResult) => {
          setResult(taskResult);
          const states: Record<string, 'pending' | 'accepted' | 'rejected'> = {};
          for (const change of taskResult.changes || []) {
            states[change.step_id] = 'pending';
          }
          setChangeStates(states);
          setPhase('completed');
          onSuccess?.(taskResult);
          abortRef.current = null;
        },
        // onError
        (errMsg) => {
          setError(errMsg);
          setPhase('failed');
          onError?.(errMsg);
          abortRef.current = null;
        },
      );

      abortRef.current = stream;
    },
    [documentId, onSuccess, onError]
  );

  const applyResult = useCallback(async () => {
    if (!result || !documentId) return;

    try {
      await documentsAPI.applyTaskResult(documentId, result.final_content);
      // Keep the result for reference but mark as applied
      setPhase('idle');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to apply result';
      setError(errorMsg);
    }
  }, [result, documentId]);

  const discardResult = useCallback(() => {
    setResult(null);
    setChangeStates({});
    setPhase('idle');
  }, []);

  const reset = useCallback(() => {
    setPhase('idle');
    setResult(null);
    setError(null);
    setChangeStates({});
    setStreamPlan([]);
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  const acceptChange = useCallback((stepId: string) => {
    setChangeStates((prev) => ({ ...prev, [stepId]: 'accepted' }));
  }, []);

  const rejectChange = useCallback((stepId: string) => {
    setChangeStates((prev) => ({ ...prev, [stepId]: 'rejected' }));
  }, []);

  return {
    phase,
    result,
    error,
    isRunning: phase === 'planning' || phase === 'executing' || phase === 'reviewing',

    executeTask,
    applyResult,
    discardResult,
    reset,
    acceptChange,
    rejectChange,

    plan: result?.plan ?? streamPlan,
    changes: result?.changes ?? [],
    changeStates,
    diffSummary: result?.diff_summary ?? '',
    reviewScore: result?.review_score ?? null,
    reviewNotes: result?.review_notes ?? null,
  };
}
