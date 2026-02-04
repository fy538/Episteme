/**
 * useReadinessChecklist - Hook for user-defined readiness criteria
 *
 * The user defines what "ready to decide" means for them.
 * No computed scores - just checkboxes they control.
 */

import { useState, useEffect, useCallback } from 'react';
import { casesAPI } from '@/lib/api/cases';
import type { ReadinessChecklistItem } from '@/lib/types/case';

interface UseReadinessChecklistOptions {
  caseId: string;
  autoInitDefaults?: boolean; // Initialize with defaults if empty
}

interface ChecklistProgress {
  completed: number;
  required: number;
  requiredCompleted: number;
  total: number;
}

interface UseReadinessChecklistReturn {
  // State
  items: ReadinessChecklistItem[];
  progress: ChecklistProgress;
  isLoading: boolean;
  error: string | null;

  // Actions
  addItem: (description: string, isRequired?: boolean) => Promise<void>;
  toggleItem: (itemId: string) => Promise<void>;
  updateItem: (itemId: string, updates: Partial<ReadinessChecklistItem>) => Promise<void>;
  deleteItem: (itemId: string) => Promise<void>;
  initDefaults: () => Promise<void>;
  refresh: () => Promise<void>;

  // Computed
  allRequiredComplete: boolean;
  allComplete: boolean;
}

export function useReadinessChecklist({
  caseId,
  autoInitDefaults = false,
}: UseReadinessChecklistOptions): UseReadinessChecklistReturn {
  const [items, setItems] = useState<ReadinessChecklistItem[]>([]);
  const [progress, setProgress] = useState<ChecklistProgress>({
    completed: 0,
    required: 0,
    requiredCompleted: 0,
    total: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!caseId) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await casesAPI.getReadinessChecklist(caseId);
      setItems(data.items);
      setProgress({
        completed: data.progress.completed,
        required: data.progress.required,
        requiredCompleted: data.progress.required_completed,
        total: data.progress.total,
      });

      // Auto-init defaults if empty and option is set
      if (autoInitDefaults && data.items.length === 0) {
        await initDefaults();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load checklist');
      console.error('Failed to load readiness checklist:', err);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, autoInitDefaults]);

  // Initial load
  useEffect(() => {
    refresh();
  }, [refresh]);

  const addItem = useCallback(
    async (description: string, isRequired = true) => {
      try {
        const newItem = await casesAPI.addChecklistItem(caseId, description, isRequired);
        setItems((prev) => [...prev, newItem]);
        setProgress((prev) => ({
          ...prev,
          total: prev.total + 1,
          required: isRequired ? prev.required + 1 : prev.required,
        }));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to add item');
        throw err;
      }
    },
    [caseId]
  );

  const toggleItem = useCallback(
    async (itemId: string) => {
      const item = items.find((i) => i.id === itemId);
      if (!item) return;

      const newIsComplete = !item.is_complete;

      // Optimistic update
      setItems((prev) =>
        prev.map((i) => (i.id === itemId ? { ...i, is_complete: newIsComplete } : i))
      );

      try {
        await casesAPI.updateChecklistItem(caseId, itemId, {
          is_complete: newIsComplete,
        });

        // Update progress
        setProgress((prev) => ({
          ...prev,
          completed: newIsComplete ? prev.completed + 1 : prev.completed - 1,
          requiredCompleted:
            item.is_required
              ? newIsComplete
                ? prev.requiredCompleted + 1
                : prev.requiredCompleted - 1
              : prev.requiredCompleted,
        }));
      } catch (err) {
        // Revert optimistic update
        setItems((prev) =>
          prev.map((i) => (i.id === itemId ? { ...i, is_complete: !newIsComplete } : i))
        );
        setError(err instanceof Error ? err.message : 'Failed to update item');
        throw err;
      }
    },
    [caseId, items]
  );

  const updateItem = useCallback(
    async (itemId: string, updates: Partial<ReadinessChecklistItem>) => {
      try {
        const updated = await casesAPI.updateChecklistItem(caseId, itemId, updates);
        setItems((prev) => prev.map((i) => (i.id === itemId ? updated : i)));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to update item');
        throw err;
      }
    },
    [caseId]
  );

  const deleteItem = useCallback(
    async (itemId: string) => {
      const item = items.find((i) => i.id === itemId);
      if (!item) return;

      // Optimistic update
      setItems((prev) => prev.filter((i) => i.id !== itemId));

      try {
        await casesAPI.deleteChecklistItem(caseId, itemId);

        // Update progress
        setProgress((prev) => ({
          ...prev,
          total: prev.total - 1,
          completed: item.is_complete ? prev.completed - 1 : prev.completed,
          required: item.is_required ? prev.required - 1 : prev.required,
          requiredCompleted:
            item.is_required && item.is_complete
              ? prev.requiredCompleted - 1
              : prev.requiredCompleted,
        }));
      } catch (err) {
        // Revert optimistic update
        setItems((prev) => [...prev, item].sort((a, b) => a.order - b.order));
        setError(err instanceof Error ? err.message : 'Failed to delete item');
        throw err;
      }
    },
    [caseId, items]
  );

  const initDefaults = useCallback(async () => {
    try {
      const result = await casesAPI.initDefaultChecklist(caseId);
      setItems(result.items);
      setProgress({
        completed: 0,
        required: result.items.filter((i) => i.is_required).length,
        requiredCompleted: 0,
        total: result.items.length,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize checklist');
      throw err;
    }
  }, [caseId]);

  // Computed
  const allRequiredComplete = progress.required === progress.requiredCompleted;
  const allComplete = progress.total === progress.completed;

  return {
    items,
    progress,
    isLoading,
    error,
    addItem,
    toggleItem,
    updateItem,
    deleteItem,
    initDefaults,
    refresh,
    allRequiredComplete,
    allComplete,
  };
}
