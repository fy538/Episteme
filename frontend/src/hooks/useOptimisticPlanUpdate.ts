/**
 * useOptimisticPlanUpdate — DRY optimistic update for CaseHome plan mutations.
 *
 * Extracts the repeated pattern: snapshot → optimistic set → API call → invalidate/revert.
 */

import { useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { CaseHomeData } from '@/lib/types/plan';

export function useOptimisticPlanUpdate(caseId: string) {
  const queryClient = useQueryClient();
  const [lastError, setLastError] = useState<string | null>(null);

  const optimisticUpdate = useCallback(
    async (
      updater: (old: CaseHomeData) => CaseHomeData,
      apiCall: () => Promise<unknown>,
      context?: string,
    ) => {
      const queryKey = ['case-home', caseId];
      const previous = queryClient.getQueryData<CaseHomeData>(queryKey);
      setLastError(null);

      // Optimistic set
      queryClient.setQueryData<CaseHomeData>(queryKey, (old) => {
        if (!old) return old;
        return updater(old);
      });

      try {
        await apiCall();
        queryClient.invalidateQueries({ queryKey });
      } catch (error) {
        queryClient.setQueryData(queryKey, previous);
        const message = context
          ? `Failed to ${context}. Please try again.`
          : 'Update failed. Please try again.';
        setLastError(message);
      }
    },
    [caseId, queryClient],
  );

  const clearError = useCallback(() => setLastError(null), []);

  return { optimisticUpdate, lastError, clearError };
}
