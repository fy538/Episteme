/**
 * useChatPanelState Hook
 *
 * State management for ChatPanel in the case workspace.
 *
 * Delegates streaming to useStreamingChat and adds:
 * - UI state (collapsed)
 * - Inline action cards (driven by LLM action hints)
 * - Case creation flow state
 *
 * Uses the shared StreamingCallbacks type.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useStreamingChat } from './useStreamingChat';
import type { ActionHint, InlineActionCard } from '@/lib/types/chat';
import type { ModeContext } from '@/lib/types/companion';
import type { StreamingCallbacks } from '@/lib/types/streaming';

interface UseChatPanelStateOptions {
  threadId: string;
  onCreateCase?: () => void;
  /** Callbacks forwarded to parent for reflection, action hints, etc. */
  streamCallbacks?: StreamingCallbacks;
  /** Current chat mode context — forwarded to backend for system prompt selection */
  mode?: ModeContext;
  /** Source context from "chat about" deep links — merged into context for the next message */
  chatSource?: { source_type: string; source_id: string } | null;
  /** Auto-send this message on mount (used by Home hero input handoff) */
  initialMessage?: string;
  /** Called after initialMessage has been sent */
  onInitialMessageSent?: () => void;
}

export function useChatPanelState({ threadId, streamCallbacks, mode, chatSource, initialMessage, onInitialMessageSent }: UseChatPanelStateOptions) {
  // --- Inline action cards state ---
  const [inlineCards, setInlineCards] = useState<InlineActionCard[]>([]);
  const [creatingCase, setCreatingCase] = useState(false);

  // Track the latest assistant message ID so we can anchor cards to it
  const latestAssistantMessageIdRef = useRef<string | null>(null);

  // --- Core streaming (delegated) ---
  // Skip initial message load for brand-new threads (hero input handoff)
  const streaming = useStreamingChat({
    threadId,
    skipInitialLoad: !!initialMessage,
    context: mode ? {
      mode: mode.mode,
      caseId: mode.caseId,
      inquiryId: mode.inquiryId,
      ...(chatSource ? { source_type: chatSource.source_type, source_id: chatSource.source_id } : {}),
    } : undefined,
    streamCallbacks: {
      ...streamCallbacks,
      // Track latest assistant message
      onMessageComplete: (messageId) => {
        if (messageId) {
          latestAssistantMessageIdRef.current = messageId;
        }
        streamCallbacks?.onMessageComplete?.(messageId);
      },
      // Convert action hints to inline cards
      onActionHints: (hints: ActionHint[]) => {
        // Forward to parent (companion panel) first
        streamCallbacks?.onActionHints?.(hints);

        // Convert suggest_case hints to inline cards
        const caseHint = hints.find(h => h.type === 'suggest_case');
        if (caseHint && latestAssistantMessageIdRef.current) {
          const cardId = `case-suggestion-${Date.now()}`;
          const newCard: InlineActionCard = {
            id: cardId,
            type: 'case_creation_prompt',
            afterMessageId: latestAssistantMessageIdRef.current,
            data: {
              aiReason: caseHint.reason,
              suggestedTitle: (caseHint.data as Record<string, unknown>).suggested_title,
              questionCount: (caseHint.data as Record<string, unknown>).question_count || 0,
            },
            createdAt: new Date().toISOString(),
          };
          setInlineCards(prev => [...prev, newCard]);
        }

        // Convert suggest_plan_diff hints to plan diff proposal cards
        const planDiffHint = hints.find(h => h.type === 'suggest_plan_diff');
        if (planDiffHint && latestAssistantMessageIdRef.current) {
          const hintData = planDiffHint.data as Record<string, unknown>;
          const newCard: InlineActionCard = {
            id: `plan-diff-${Date.now()}`,
            type: 'plan_diff_proposal',
            afterMessageId: latestAssistantMessageIdRef.current,
            data: {
              diffSummary: planDiffHint.reason,
              proposedContent: hintData.proposed_content,
              diffData: hintData.diff_data,
            },
            createdAt: new Date().toISOString(),
          };
          setInlineCards(prev => [...prev, newCard]);
        }
      },
    },
  });

  // --- UI state ---
  const [isCollapsed, setIsCollapsed] = useState(false);

  // --- Card actions ---
  const dismissCard = useCallback((cardId: string) => {
    setInlineCards(prev =>
      prev.map(card =>
        card.id === cardId ? { ...card, dismissed: true } : card
      )
    );
  }, []);

  const addInlineCard = useCallback((card: InlineActionCard) => {
    setInlineCards(prev => [...prev, card]);
  }, []);

  // Auto-send initial message (Home hero input → chat handoff)
  //
  // When skipInitialLoad is true (brand-new thread), isLoading stays false
  // so we send immediately on first effect run. When loading does happen
  // (existing thread), we wait for isLoading to become false.
  const initialMessageSentRef = useRef(false);

  useEffect(() => {
    if (!initialMessage || initialMessageSentRef.current || streaming.isLoading) return;

    initialMessageSentRef.current = true;
    streaming.sendMessage(initialMessage);
    onInitialMessageSent?.();
  }, [initialMessage, streaming.isLoading]); // eslint-disable-line react-hooks/exhaustive-deps

  // Wrap sendMessage for consistent interface
  const sendMessage = useCallback(async (content: string) => {
    return streaming.sendMessage(content);
  }, [streaming.sendMessage]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    // Core streaming state (spread from useStreamingChat, with wrapped sendMessage)
    ...streaming,
    sendMessage,

    // UI
    isCollapsed,
    setIsCollapsed,

    // Inline action cards
    inlineCards,
    addInlineCard,
    dismissCard,
    creatingCase,
    setCreatingCase,
  };
}
