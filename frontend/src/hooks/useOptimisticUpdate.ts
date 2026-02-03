/**
 * Optimistic update hook
 * Updates UI immediately, rolls back on error
 */

'use client';

import { useState, useCallback } from 'react';
import { useToast } from '@/components/ui/toast';

interface OptimisticUpdateOptions<T> {
  onSuccess?: (result: T) => void;
  onError?: (error: Error) => void;
  successMessage?: string;
  errorMessage?: string;
}

export function useOptimisticUpdate<T = any>() {
  const [isOptimistic, setIsOptimistic] = useState(false);
  const { addToast } = useToast();

  const execute = useCallback(
    async <TData = T>(
      optimisticUpdate: () => void,
      apiCall: () => Promise<TData>,
      rollback: () => void,
      options?: OptimisticUpdateOptions<TData>
    ): Promise<TData | null> => {
      try {
        // 1. Immediately update UI (optimistic)
        setIsOptimistic(true);
        optimisticUpdate();

        // 2. Call API
        const result = await apiCall();

        // 3. Success - keep the optimistic update
        setIsOptimistic(false);
        
        if (options?.successMessage) {
          addToast({
            title: 'Success',
            description: options.successMessage,
            variant: 'success',
          });
        }

        options?.onSuccess?.(result);
        return result;
      } catch (error) {
        // 4. Error - rollback the optimistic update
        setIsOptimistic(false);
        rollback();

        const errorMessage = options?.errorMessage || 'Something went wrong';
        addToast({
          title: 'Error',
          description: errorMessage,
          variant: 'error',
        });

        options?.onError?.(error as Error);
        return null;
      }
    },
    [addToast]
  );

  return { execute, isOptimistic };
}

// Convenience hook for common CRUD operations
export function useOptimisticList<T extends { id: string }>(
  initialItems: T[]
) {
  const [items, setItems] = useState<T[]>(initialItems);
  const { execute, isOptimistic } = useOptimisticUpdate();

  const addItem = useCallback(
    async (
      newItem: T,
      apiCall: () => Promise<T>,
      options?: OptimisticUpdateOptions<T>
    ) => {
      return execute(
        () => setItems(prev => [...prev, newItem]),
        apiCall,
        () => setItems(prev => prev.filter(item => item.id !== newItem.id)),
        options
      );
    },
    [execute]
  );

  const removeItem = useCallback(
    async (
      itemId: string,
      apiCall: () => Promise<void>,
      options?: OptimisticUpdateOptions<void>
    ) => {
      const removedItem = items.find(item => item.id === itemId);
      if (!removedItem) return null;

      return execute(
        () => setItems(prev => prev.filter(item => item.id !== itemId)),
        apiCall,
        () => setItems(prev => [...prev, removedItem]),
        options
      );
    },
    [execute, items]
  );

  const updateItem = useCallback(
    async (
      itemId: string,
      updates: Partial<T>,
      apiCall: () => Promise<T>,
      options?: OptimisticUpdateOptions<T>
    ) => {
      const originalItem = items.find(item => item.id === itemId);
      if (!originalItem) return null;

      return execute(
        () =>
          setItems(prev =>
            prev.map(item =>
              item.id === itemId ? { ...item, ...updates } : item
            )
          ),
        apiCall,
        () =>
          setItems(prev =>
            prev.map(item => (item.id === itemId ? originalItem : item))
          ),
        options
      );
    },
    [execute, items]
  );

  return {
    items,
    setItems,
    addItem,
    removeItem,
    updateItem,
    isOptimistic,
  };
}
