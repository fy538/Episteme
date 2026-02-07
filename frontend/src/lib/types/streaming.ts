/**
 * Shared streaming callback types for unified chat streaming.
 *
 * Used by useStreamingChat, useChatPanelState, ChatPanel, and any
 * parent component that receives stream events (reflection, signals, hints).
 */

import type { ActionHint } from './chat';
import type { Signal } from './signal';

/** Callbacks from unified streaming that parent components handle */
export interface StreamingCallbacks {
  /** Called when reflection content updates (streaming delta) */
  onReflectionChunk?: (delta: string) => void;
  /** Called when reflection is complete */
  onReflectionComplete?: (content: string) => void;
  /** Called when signals are extracted from the stream */
  onSignals?: (signals: Signal[]) => void;
  /** Called when action hints are received from AI */
  onActionHints?: (hints: ActionHint[]) => void;
  /** Called when assistant message is complete */
  onMessageComplete?: (messageId?: string) => void;
}
