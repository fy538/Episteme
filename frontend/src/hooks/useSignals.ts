/**
 * React Query hooks for signal operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface Signal {
  id: string;
  type: 'assumption' | 'question' | 'evidence' | 'claim';
  text: string;
  normalized_text: string;
  confidence: number;
  span: {
    message_id: string;
    start: number;
    end: number;
  };
  sequence_index: number;
  dismissed_at: string | null;
  created_at: string;
}

/**
 * Fetch signals for a specific thread
 */
export function useSignals(threadId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['signals', threadId],
    queryFn: async () => {
      const response = await apiClient.get<Signal[]>(`/signals/?thread_id=${threadId}`);
      return response;
    },
    enabled: enabled && !!threadId,
  });
}

/**
 * Fetch signals for a specific message
 * Now uses server-side filtering for efficiency
 */
export function useSignalsForMessage(messageId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['signals', 'message', messageId],
    queryFn: async () => {
      // Use server-side filtering with message_id parameter
      const signals = await apiClient.get<Signal[]>(`/signals/?message_id=${messageId}`);
      return signals;
    },
    enabled: enabled && !!messageId,
  });
}

/**
 * Dismiss a signal
 */
export function useDismissSignal() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (signalId: string) => {
      return await apiClient.patch(`/signals/${signalId}/`, {
        dismissed_at: new Date().toISOString()
      });
    },
    onSuccess: () => {
      // Invalidate signal queries to refetch
      queryClient.invalidateQueries({ queryKey: ['signals'] });
    },
  });
}

/**
 * Convert signal to inquiry (placeholder - implement when needed)
 */
export function useConvertSignalToInquiry() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ signalId, caseId }: { signalId: string; caseId: string }) => {
      // This would call an endpoint that creates an inquiry from a signal
      // For now, placeholder
      return await apiClient.post(`/inquiries/create_from_signal/`, {
        signal_id: signalId,
        case_id: caseId
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inquiries'] });
      queryClient.invalidateQueries({ queryKey: ['signals'] });
    },
  });
}
