/**
 * Shared streaming callback types for unified chat streaming.
 *
 * Used by useStreamingChat, useChatPanelState, ChatPanel, and any
 * parent component that receives stream events (reflection, hints).
 */

import type { ActionHint, PlanDiffProposalData, OrientationDiffProposalData, ToolExecutedData, ToolConfirmationData } from './chat';
import type { GraphEditSummary } from './graph';
import type { ConversationStructure, CompanionCaseContext, EpisodeSealedEvent, CurrentEpisodeInfo } from './companion';

/** Callbacks from unified streaming that parent components handle */
export interface StreamingCallbacks {
  /** Called when reflection content updates (streaming delta) */
  onReflectionChunk?: (delta: string) => void;
  /** Called when reflection is complete */
  onReflectionComplete?: (content: string) => void;
  /** Called when action hints are received from AI */
  onActionHints?: (hints: ActionHint[]) => void;
  /** Called when graph edits are applied by the agent */
  onGraphEdits?: (summary: GraphEditSummary) => void;
  /** Called when plan edits are proposed by the AI (case-scoped chat) */
  onPlanEdits?: (data: PlanDiffProposalData) => void;
  /** Called when assistant message is complete */
  onMessageComplete?: (messageId?: string) => void;
  /** Called when the thread title is auto-generated or refreshed */
  onTitleUpdate?: (title: string) => void;
  /** Called when companion structure is updated */
  onCompanionStructure?: (structure: ConversationStructure) => void;
  /** Called when background research starts */
  onResearchStarted?: (data: { question: string; priority: string }) => void;
  /** Called when a case signal is detected from companion */
  onCaseSignal?: (data: CompanionCaseContext) => void;
  /** Called when orientation edits are proposed by the AI (orientation-mode chat) */
  onOrientationEdits?: (data: OrientationDiffProposalData) => void;
  /** Called when a tool action is auto-executed by the AI */
  onToolExecuted?: (data: ToolExecutedData) => void;
  /** Called when a tool action needs user confirmation */
  onToolConfirmation?: (data: ToolConfirmationData) => void;
  /** Called when an episode is sealed due to topic shift */
  onEpisodeSealed?: (data: EpisodeSealedEvent) => void;
  /** Called when current episode info is updated (attached to companion_structure) */
  onCurrentEpisodeUpdate?: (info: CurrentEpisodeInfo) => void;
  /** Called when a loaded message has a pending position update proposal */
  onLoadedPositionProposal?: (messageId: string, proposal: { proposals: Array<{ fact: string; reason: string }>; case_id: string; current_position: string }) => void;
}
