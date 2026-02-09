/**
 * Shared streaming callback types for unified chat streaming.
 *
 * Used by useStreamingChat, useChatPanelState, ChatPanel, and any
 * parent component that receives stream events (reflection, hints).
 */

import type { ActionHint } from './chat';
import type { GraphEditSummary } from './graph';

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
  /** Called when assistant message is complete */
  onMessageComplete?: (messageId?: string) => void;
  /** Called when the thread title is auto-generated or refreshed */
  onTitleUpdate?: (title: string) => void;
}
