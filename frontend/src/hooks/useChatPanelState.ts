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
import { chatAPI } from '@/lib/api/chat';
import type { ActionHint, InlineActionCard, ToolExecutedData, ToolConfirmationData } from '@/lib/types/chat';
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

  // Dedup guard: track which message IDs already have a plan_diff_proposal card
  // to prevent duplicates from onPlanEdits (SSE) vs onActionHints (suggest_plan_diff)
  const planDiffMessageIdsRef = useRef<Set<string>>(new Set());

  // --- Core streaming (delegated) ---
  // Skip initial message load for brand-new threads (hero input handoff)
  const streaming = useStreamingChat({
    threadId,
    skipInitialLoad: !!initialMessage,
    context: (mode || chatSource) ? {
      ...(mode ? { mode: mode.mode, caseId: mode.caseId, inquiryId: mode.inquiryId } : {}),
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
        // (skip if onPlanEdits already created a card for this message)
        const planDiffHint = hints.find(h => h.type === 'suggest_plan_diff');
        if (planDiffHint && latestAssistantMessageIdRef.current) {
          const msgId = latestAssistantMessageIdRef.current;
          if (!planDiffMessageIdsRef.current.has(msgId)) {
            planDiffMessageIdsRef.current.add(msgId);
            const hintData = planDiffHint.data as Record<string, unknown>;
            const newCard: InlineActionCard = {
              id: `plan-diff-${Date.now()}`,
              type: 'plan_diff_proposal',
              afterMessageId: msgId,
              data: {
                diffSummary: planDiffHint.reason,
                proposedContent: hintData.proposed_content,
                diffData: hintData.diff_data,
              },
              createdAt: new Date().toISOString(),
            };
            setInlineCards(prev => [...prev, newCard]);
          }
        }
      },
      // Wire plan_edits SSE event to plan diff proposal inline card
      // (preferred source — takes priority over suggest_plan_diff action hints)
      onPlanEdits: (planEditsData) => {
        streamCallbacks?.onPlanEdits?.(planEditsData);

        if (planEditsData?.proposedContent && latestAssistantMessageIdRef.current) {
          const msgId = latestAssistantMessageIdRef.current;
          // Mark this message as having a plan diff card (dedup guard)
          planDiffMessageIdsRef.current.add(msgId);
          const newCard: InlineActionCard = {
            id: `plan-edits-${Date.now()}`,
            type: 'plan_diff_proposal',
            afterMessageId: msgId,
            data: {
              diffSummary: planEditsData.diffSummary || 'Proposed plan changes',
              proposedContent: planEditsData.proposedContent,
              diffData: planEditsData.diffData || {},
            },
            createdAt: new Date().toISOString(),
          };
          setInlineCards(prev => [...prev, newCard]);
        }
      },
      // Wire orientation_edits SSE event to orientation diff proposal inline card
      onOrientationEdits: (orientationEditsData) => {
        streamCallbacks?.onOrientationEdits?.(orientationEditsData);

        if (orientationEditsData?.proposedState && latestAssistantMessageIdRef.current) {
          const msgId = latestAssistantMessageIdRef.current;
          const newCard: InlineActionCard = {
            id: `orientation-edits-${Date.now()}`,
            type: 'orientation_diff_proposal',
            afterMessageId: msgId,
            data: {
              orientationId: orientationEditsData.orientationId,
              diffSummary: orientationEditsData.diffSummary || 'Proposed orientation changes',
              proposedState: orientationEditsData.proposedState,
              diffData: orientationEditsData.diffData || {},
            },
            createdAt: new Date().toISOString(),
          };
          setInlineCards(prev => [...prev, newCard]);
        }
      },
      // Wire companion case signal to inline card (companion-detected "decision shape")
      onCaseSignal: (data) => {
        streamCallbacks?.onCaseSignal?.(data);

        if (latestAssistantMessageIdRef.current) {
          const newCard: InlineActionCard = {
            id: `companion-case-signal-${Date.now()}`,
            type: 'case_creation_prompt',
            afterMessageId: latestAssistantMessageIdRef.current,
            data: {
              aiReason: data.reason || 'Your conversation has a decision structure that could benefit from structured analysis.',
              suggestedTitle: data.suggested_title || data.decision_question,
              companionState: data.companion_state,
              source: 'companion',
            },
            createdAt: new Date().toISOString(),
          };
          setInlineCards(prev => [...prev, newCard]);
        }
      },
      // Wire tool_executed SSE event to inline card (auto-executed tool results)
      onToolExecuted: (data: ToolExecutedData) => {
        streamCallbacks?.onToolExecuted?.(data);

        if (latestAssistantMessageIdRef.current) {
          const newCard: InlineActionCard = {
            id: `tool-executed-${Date.now()}-${data.tool}`,
            type: 'tool_executed',
            afterMessageId: latestAssistantMessageIdRef.current,
            data: data as unknown as Record<string, unknown>,
            createdAt: new Date().toISOString(),
          };
          setInlineCards(prev => [...prev, newCard]);
        } else {
          // M6: Observability — tool event arrived before onMessageComplete set the ref
          console.warn('[useChatPanelState] tool_executed event dropped: no assistant message ID yet', data.tool);
        }
      },
      // Wire position update proposals from loaded messages to inline cards
      onLoadedPositionProposal: (messageId, proposal) => {
        // Avoid duplicates if this message already has a card
        setInlineCards(prev => {
          const exists = prev.some(c =>
            c.type === 'position_update_proposal' && c.afterMessageId === messageId
          );
          if (exists) return prev;
          return [...prev, {
            id: `position-update-${messageId}`,
            type: 'position_update_proposal' as const,
            afterMessageId: messageId,
            data: {
              proposals: proposal.proposals,
              caseId: proposal.case_id,
              currentPosition: proposal.current_position,
              messageId,
            },
            createdAt: new Date().toISOString(),
          }];
        });
      },
      // Wire tool_confirmation SSE event to inline card (requires user approval)
      onToolConfirmation: (data: ToolConfirmationData) => {
        streamCallbacks?.onToolConfirmation?.(data);

        if (latestAssistantMessageIdRef.current) {
          const newCard: InlineActionCard = {
            id: `tool-confirm-${Date.now()}-${data.tool}`,
            type: 'tool_confirmation',
            afterMessageId: latestAssistantMessageIdRef.current,
            data: data as unknown as Record<string, unknown>,
            createdAt: new Date().toISOString(),
          };
          setInlineCards(prev => [...prev, newCard]);
        } else {
          // M6: Observability — confirmation event arrived before onMessageComplete set the ref
          console.warn('[useChatPanelState] tool_confirmation event dropped: no assistant message ID yet', data.tool);
        }
      },
    },
  });

  // --- Clear stale cards when thread changes ---
  // Without this, cards from a previous thread could persist if the component
  // is reused without remounting (e.g. switching threads in the same ChatPanel).
  useEffect(() => {
    setInlineCards([]);
    planDiffMessageIdsRef.current.clear();
    latestAssistantMessageIdRef.current = null;
  }, [threadId]);

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

  // Confirm or dismiss a pending tool action
  const confirmToolAction = useCallback(async (confirmationId: string, approved: boolean) => {
    const result = await chatAPI.confirmToolAction(threadId, confirmationId, approved);
    if (!result.success && !result.dismissed) {
      throw new Error(result.error || 'Failed to execute tool action');
    }
  }, [threadId]);

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
    confirmToolAction,
    creatingCase,
    setCreatingCase,
  };
}
