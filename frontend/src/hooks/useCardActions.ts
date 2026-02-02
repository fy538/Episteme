import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CardAction } from '@/lib/types/cards';
import { apiClient } from '@/lib/api/client';

interface CardActionParams {
  action: CardAction;
  messageId: string;
  threadId: string;
}

export function useCardActions() {
  const queryClient = useQueryClient();
  
  const executeAction = useMutation({
    mutationFn: async ({ action, threadId }: CardActionParams) => {
      // Route to appropriate handler based on action_type
      switch (action.action_type) {
        case 'validate_assumptions':
          return apiClient.post(`/chat/threads/${threadId}/validate_assumptions/`, {
            assumption_ids: action.payload.assumption_ids || action.payload.signal_ids
          });
        
        case 'organize_questions':
          return apiClient.post(`/chat/threads/${threadId}/organize_questions/`, {
            question_ids: action.payload.question_ids || action.payload.signal_ids
          });
        
        case 'create_inquiry_from_questions':
          return apiClient.post('/inquiries/', {
            thread_id: threadId,
            questions: action.payload.questions
          });
        
        case 'create_case_from_thread':
          return apiClient.post(`/chat/threads/${threadId}/analyze_for_case/`);
        
        case 'dismiss_suggestion':
          return apiClient.post(`/chat/threads/${threadId}/dismiss_suggestion/`, {
            type: action.payload.type
          });
        
        case 'research_assumptions':
          return apiClient.post(`/chat/threads/${threadId}/invoke_agent/`, {
            agent_type: 'research',
            params: {
              targets: action.payload.assumption_ids
            }
          });
        
        case 'preview_case_structure':
          return apiClient.post(`/chat/threads/${threadId}/analyze_for_case/`);
        
        case 'stop_agent':
          // TODO: Implement agent stop endpoint
          console.warn('Stop agent not yet implemented');
          return Promise.resolve({});
        
        case 'view_agent_results':
          // TODO: Navigate to agent results
          console.warn('View agent results not yet implemented');
          return Promise.resolve({});
        
        case 'apply_research_to_case':
          // TODO: Apply research to case
          console.warn('Apply research to case not yet implemented');
          return Promise.resolve({});
        
        default:
          console.warn('Unknown action type:', action.action_type);
          return Promise.resolve({});
      }
    },
    onSuccess: (_, variables) => {
      // Invalidate relevant queries to refresh UI
      queryClient.invalidateQueries({ queryKey: ['thread', variables.threadId] });
      queryClient.invalidateQueries({ queryKey: ['messages', variables.threadId] });
      queryClient.invalidateQueries({ queryKey: ['threads'] });
    }
  });
  
  return {
    executeAction: executeAction.mutate,
    executeActionAsync: executeAction.mutateAsync,
    isExecuting: executeAction.isPending,
    error: executeAction.error
  };
}
