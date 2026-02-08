/**
 * useChatPanelState Hook
 *
 * State management for ChatPanel in the case workspace.
 *
 * Delegates streaming to useStreamingChat and adds:
 * - Signals state (loaded once, updated via stream)
 * - UI state (collapsed, signals expanded)
 * - Inline action cards (driven by LLM action hints)
 * - Case creation flow state
 *
 * Uses the shared StreamingCallbacks type.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { signalsAPI } from '@/lib/api/signals';
import { useStreamingChat } from './useStreamingChat';
import type { Signal } from '@/lib/types/signal';
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

  // Accumulate signals during a single stream so we can create an inline card on completion
  // Uses a Map keyed by signal ID to deduplicate across multiple onSignals callbacks
  const pendingSignalsRef = useRef<Map<string, { text: string; type: string }>>(new Map());

  // --- Core streaming (delegated) ---
  const streaming = useStreamingChat({
    threadId,
    context: mode ? {
      mode: mode.mode,
      caseId: mode.caseId,
      inquiryId: mode.inquiryId,
      ...(chatSource ? { source_type: chatSource.source_type, source_id: chatSource.source_id } : {}),
    } : undefined,
    streamCallbacks: {
      ...streamCallbacks,
      // Intercept signals to merge into local state + accumulate for inline card
      onSignals: (newSignals) => {
        setSignals(prev => {
          const existingIds = new Set(prev.map(s => s.id));
          const unique = newSignals.filter(s => !existingIds.has(s.id));
          return unique.length > 0 ? [...prev, ...unique] : prev;
        });
        // Accumulate for inline card creation on message complete (deduplicated by ID)
        for (const sig of newSignals) {
          if (!pendingSignalsRef.current.has(sig.id)) {
            pendingSignalsRef.current.set(sig.id, { text: sig.text, type: sig.type });
          }
        }
        // Also forward to parent
        streamCallbacks?.onSignals?.(newSignals);
      },
      // Track latest assistant message + create signals inline card
      onMessageComplete: (messageId) => {
        if (messageId) {
          latestAssistantMessageIdRef.current = messageId;

          // Create signals_collapsed inline card if signals were extracted during this stream
          const pending = Array.from(pendingSignalsRef.current.values());
          if (pending.length > 0) {
            const newCard: InlineActionCard = {
              id: `signals-${messageId}`,
              type: 'signals_collapsed',
              afterMessageId: messageId,
              data: { signals: pending, totalCount: pending.length },
              createdAt: new Date().toISOString(),
            };
            setInlineCards(prev => [...prev, newCard]);
            pendingSignalsRef.current = new Map();
          }
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
              signalCount: (caseHint.data as Record<string, unknown>).signal_count || 0,
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

  // --- Signals state ---
  const [signals, setSignals] = useState<Signal[]>([]);

  // --- UI state ---
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [signalsExpanded, setSignalsExpanded] = useState(false);

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

  // Load signals once on thread change
  useEffect(() => {
    async function loadSignals() {
      try {
        const sigs = await signalsAPI.getByThread(threadId);
        setSignals(sigs);
      } catch (err) {
        console.error('Failed to load signals:', err);
      }
    }
    loadSignals();
  }, [threadId]);

  // Auto-send initial message (Home hero input → chat handoff)
  //
  // Race condition fix: On mount, isLoading starts false (before the
  // loadMessages effect runs), then goes true→false as messages load.
  // We must wait for loading to *complete* (the true→false transition),
  // not fire on the initial pre-load false — otherwise sendMessage races
  // with loadMessages and the loaded [] overwrites optimistic messages.
  const initialMessageSentRef = useRef(false);
  const hasStartedLoadingRef = useRef(false);

  useEffect(() => {
    if (streaming.isLoading) {
      hasStartedLoadingRef.current = true;
    }

    if (
      initialMessage &&
      !initialMessageSentRef.current &&
      !streaming.isLoading &&
      hasStartedLoadingRef.current
    ) {
      initialMessageSentRef.current = true;
      const timer = setTimeout(() => {
        streaming.sendMessage(initialMessage);
        onInitialMessageSent?.();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [initialMessage, streaming.isLoading]); // eslint-disable-line react-hooks/exhaustive-deps

  // Wrap sendMessage to clear pending signals before each new message
  const sendMessage = useCallback(async (content: string) => {
    pendingSignalsRef.current = new Map();
    return streaming.sendMessage(content);
  }, [streaming.sendMessage]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    // Core streaming state (spread from useStreamingChat, with wrapped sendMessage)
    ...streaming,
    sendMessage,

    // Signals
    signals,
    signalsExpanded,
    setSignalsExpanded,

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
