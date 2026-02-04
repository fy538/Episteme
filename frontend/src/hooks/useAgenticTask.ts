/**
 * useAgenticTask - Hook for executing complex document editing tasks
 *
 * Provides:
 * - Task execution with planning, execution, and review phases
 * - Progress tracking for each step
 * - Diff preview before applying changes
 * - Ability to accept or reject the result
 */

import { useState, useCallback } from 'react';
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

  // Computed
  plan: TaskStep[];
  changes: TaskChange[];
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

  const executeTask = useCallback(
    async (taskDescription: string) => {
      if (!documentId || !taskDescription.trim()) return;

      setPhase('planning');
      setError(null);
      setResult(null);

      try {
        // The backend handles all phases, we just track the overall progress
        setPhase('executing');

        const taskResult = await documentsAPI.executeTask(documentId, taskDescription);

        setPhase('reviewing');

        // Small delay to show review phase
        await new Promise((resolve) => setTimeout(resolve, 500));

        if (taskResult.status === 'completed') {
          setResult(taskResult);
          setPhase('completed');
          onSuccess?.(taskResult);
        } else {
          setError('Task execution failed');
          setPhase('failed');
          onError?.('Task execution failed');
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Task execution failed';
        setError(errorMsg);
        setPhase('failed');
        onError?.(errorMsg);
      }
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
    setPhase('idle');
  }, []);

  const reset = useCallback(() => {
    setPhase('idle');
    setResult(null);
    setError(null);
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

    plan: result?.plan ?? [],
    changes: result?.changes ?? [],
    diffSummary: result?.diff_summary ?? '',
    reviewScore: result?.review_score ?? null,
    reviewNotes: result?.review_notes ?? null,
  };
}
