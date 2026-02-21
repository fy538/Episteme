/**
 * Chat API functions
 */

import { apiClient } from './client';
import type { ChatThread, Message, ActionHint, SourceChunk, PlanDiffProposalData, OrientationDiffProposalData, ToolExecutedData, ToolConfirmationData } from '../types/chat';
import type { GraphEditSummary } from '../types/graph';
import type { ScaffoldResult } from '../types/case';
import type { ConversationStructure, ConversationEpisode, ResearchResult, CompanionCaseContext, EpisodeSealedEvent, CurrentEpisodeInfo } from '../types/companion';

export const chatAPI = {
  async createThread(projectId?: string | null, metadata?: Record<string, unknown>): Promise<ChatThread> {
    return apiClient.post<ChatThread>('/chat/threads/', {
      ...(projectId ? { project: projectId } : {}),
      ...(metadata ? { metadata } : {}),
    });
  },

  async getThread(threadId: string): Promise<ChatThread> {
    return apiClient.get<ChatThread>(`/chat/threads/${threadId}/`);
  },

  async listThreads(params?: { archived?: 'true' | 'false' | 'all'; q?: string; project_id?: string }): Promise<ChatThread[]> {
    const query = new URLSearchParams();
    if (params?.archived) query.set('archived', params.archived);
    if (params?.q) query.set('q', params.q);
    if (params?.project_id) query.set('project_id', params.project_id);
    const suffix = query.toString() ? `?${query.toString()}` : '';
    const response = await apiClient.get<{ results: ChatThread[] }>(`/chat/threads/${suffix}`);
    return response.results || [];
  },

  async updateThread(threadId: string, data: Partial<ChatThread>): Promise<ChatThread> {
    return apiClient.patch<ChatThread>(`/chat/threads/${threadId}/`, data);
  },

  async getMessages(threadId: string): Promise<Message[]> {
    const response = await apiClient.get<{ results: Message[] }>(
      `/chat/messages/?thread=${threadId}`
    );
    return response.results || [];
  },

  async analyzeForCase(threadId: string, userFocus?: string, insightId?: string): Promise<{
    should_suggest: boolean;
    suggested_title: string;
    suggested_question: string;
    position_draft: string;
    key_questions: string[];
    assumptions: string[];
    constraints: Array<{ type: string; description: string }>;
    success_criteria: Array<{ criterion: string; measurable?: string }>;
    confidence: number;
    correlation_id: string;
    message_count: number;
    decision_criteria?: Array<{ criterion: string; measurable?: string }>;
    assumption_test_strategies?: Record<string, string>;
  }> {
    return apiClient.post(`/chat/threads/${threadId}/analyze_for_case/`, {
      ...(userFocus ? { user_focus: userFocus } : {}),
      ...(insightId ? { insight_id: insightId } : {}),
    });
  },

  async createCaseFromAnalysis(
    threadId: string,
    analysis: Record<string, unknown>,
    userEdits?: Record<string, unknown>
  ): Promise<ScaffoldResult & { correlation_id: string }> {
    return apiClient.post(`/chat/threads/${threadId}/create_case_from_analysis/`, {
      analysis,
      correlation_id: analysis.correlation_id,
      user_edits: userEdits,
    });
  },

  /**
   * Send message with unified streaming (response + reflection + action hints)
   */
  async sendUnifiedStream(
    threadId: string,
    content: string,
    callbacks: {
      onResponseChunk?: (delta: string) => void;
      onReflectionChunk?: (delta: string) => void;
      onResponseComplete?: (content: string) => void;
      onReflectionComplete?: (content: string) => void;
      onActionHints?: (hints: ActionHint[]) => void;
      onGraphEdits?: (summary: GraphEditSummary) => void;
      onPlanEdits?: (data: PlanDiffProposalData) => void;
      onOrientationEdits?: (data: OrientationDiffProposalData) => void;
      onTitleUpdate?: (title: string) => void;
      onCompanionStructure?: (structure: ConversationStructure) => void;
      onResearchStarted?: (data: { question: string; priority: string }) => void;
      onSourceChunks?: (chunks: SourceChunk[]) => void;
      onCaseSignal?: (data: CompanionCaseContext) => void;
      onToolExecuted?: (data: ToolExecutedData) => void;
      onToolConfirmation?: (data: ToolConfirmationData) => void;
      onEpisodeSealed?: (data: EpisodeSealedEvent) => void;
      onCurrentEpisodeUpdate?: (info: CurrentEpisodeInfo) => void;
      onDone?: (result: { messageId?: string; reflectionId?: string; actionHintsCount?: number; graphEditsApplied?: boolean; hasCompanionStructure?: boolean }) => void;
      onError?: (error: string) => void;
    },
    signal?: AbortSignal,
    /** Optional mode context for backend system prompt selection */
    context?: { mode?: string; caseId?: string; inquiryId?: string; source_type?: string; source_id?: string }
  ): Promise<void> {
    await apiClient.stream(
      `/chat/threads/${threadId}/unified-stream/`,
      { content, ...(context ? { context } : {}) },
      ({ event, data }) => {
        switch (event) {
          case 'response_chunk':
            callbacks.onResponseChunk?.(data?.delta || '');
            break;
          case 'reflection_chunk':
            callbacks.onReflectionChunk?.(data?.delta || '');
            break;
          case 'response_complete':
            callbacks.onResponseComplete?.(data?.content || '');
            break;
          case 'reflection_complete':
            callbacks.onReflectionComplete?.(data?.content || '');
            break;
          case 'action_hints':
            callbacks.onActionHints?.(data?.action_hints || []);
            break;
          case 'graph_edits':
            callbacks.onGraphEdits?.(data as GraphEditSummary);
            break;
          case 'plan_edits':
            if (data?.plan_edits && data.plan_edits.proposed_content) {
              callbacks.onPlanEdits?.({
                diffSummary: data.plan_edits.diff_summary || 'Proposed plan changes',
                proposedContent: data.plan_edits.proposed_content,
                diffData: data.plan_edits.diff_data || {},
              } as PlanDiffProposalData);
            }
            break;
          case 'orientation_edits':
            if (data?.orientation_edits && data.orientation_edits.proposed_state) {
              callbacks.onOrientationEdits?.({
                orientationId: data.orientation_edits.orientation_id || '',
                diffSummary: data.orientation_edits.diff_summary || 'Proposed orientation changes',
                proposedState: data.orientation_edits.proposed_state,
                diffData: data.orientation_edits.diff_data || {},
              } as OrientationDiffProposalData);
            }
            break;
          case 'title_update':
            callbacks.onTitleUpdate?.(data?.title || '');
            break;
          case 'companion_structure':
            callbacks.onCompanionStructure?.(data?.structure);
            // Extract current episode info if attached
            if (data?.structure?.current_episode) {
              callbacks.onCurrentEpisodeUpdate?.(data.structure.current_episode as CurrentEpisodeInfo);
            }
            break;
          case 'episode_sealed':
            callbacks.onEpisodeSealed?.(data as EpisodeSealedEvent);
            break;
          case 'research_started':
            callbacks.onResearchStarted?.(data as { question: string; priority: string });
            break;
          case 'source_chunks':
            callbacks.onSourceChunks?.(data?.chunks || []);
            break;
          case 'case_signal':
            callbacks.onCaseSignal?.(data as unknown as CompanionCaseContext);
            break;
          case 'tool_executed':
            callbacks.onToolExecuted?.({
              tool: data?.tool || '',
              displayName: data?.display_name || data?.tool || '',
              success: data?.success ?? false,
              output: data?.output || {},
              error: data?.error,
            });
            break;
          case 'tool_confirmation':
            callbacks.onToolConfirmation?.({
              tool: data?.tool || '',
              displayName: data?.display_name || data?.tool || '',
              params: data?.params || {},
              reason: data?.reason || '',
              confirmationId: data?.confirmation_id || '',
            });
            break;
          case 'done':
            callbacks.onDone?.({
              messageId: data?.message_id,
              reflectionId: data?.reflection_id,
              actionHintsCount: data?.action_hints_count || 0,
              graphEditsApplied: data?.graph_edits_applied || false,
              hasCompanionStructure: data?.has_companion_structure || false,
            });
            break;
          case 'error':
            callbacks.onError?.(data?.error || 'Unknown error');
            break;
        }
      },
      signal
    );
  },

  /**
   * Get the current conversation structure for a thread
   */
  async getConversationStructure(threadId: string): Promise<ConversationStructure | null> {
    const response = await apiClient.get<{ structure: ConversationStructure | null }>(`/chat/threads/${threadId}/structure/`);
    return response.structure;
  },

  /**
   * Get conversation episodes for a thread
   */
  async getEpisodes(threadId: string): Promise<{ episodes: ConversationEpisode[]; current_episode_id: string | null }> {
    return apiClient.get<{ episodes: ConversationEpisode[]; current_episode_id: string | null }>(
      `/chat/threads/${threadId}/episodes/`
    );
  },

  /**
   * Get research results for a thread
   */
  async getResearchResults(threadId: string): Promise<ResearchResult[]> {
    const response = await apiClient.get<{ results: ResearchResult[] }>(`/chat/threads/${threadId}/research/`);
    return response.results || [];
  },

  /**
   * Confirm or dismiss a pending tool action.
   *
   * Response contract:
   *   Dismiss (approved=false): { success: true, dismissed: true }
   *   Execution success:        { success: true, tool, display_name, output, error: null }
   *   Execution failure:         { success: false, tool, display_name, output: {}, error: "..." }
   *
   * Consumer check: `!result.success && !result.dismissed` detects real failures.
   * A dismissed response has `success=true` so it passes through cleanly.
   */
  async confirmToolAction(
    threadId: string,
    confirmationId: string,
    approved: boolean,
  ): Promise<{
    success: boolean;
    tool?: string;
    display_name?: string;
    output?: Record<string, unknown>;
    error?: string | null;
    dismissed?: boolean;
  }> {
    return apiClient.post(`/chat/threads/${threadId}/confirm-tool/`, {
      confirmation_id: confirmationId,
      approved,
    });
  },
};
