/**
 * useChatPanelState Hook
 *
 * State management for ChatPanel in the case workspace.
 *
 * Delegates streaming to useStreamingChat and adds:
 * - Signals state (loaded once, updated via stream)
 * - UI state (collapsed, signals expanded)
 * - Case analysis state (auto-trigger after 4 turns)
 *
 * Uses the shared StreamingCallbacks type.
 */

import { useState, useEffect, useRef } from 'react';
import { chatAPI } from '@/lib/api/chat';
import { signalsAPI } from '@/lib/api/signals';
import { useStreamingChat } from './useStreamingChat';
import type { Signal } from '@/lib/types/signal';
import type { ModeContext } from '@/lib/types/companion';
import type { StreamingCallbacks } from '@/lib/types/streaming';

interface UseChatPanelStateOptions {
  threadId: string;
  onCreateCase?: () => void;
  /** Callbacks forwarded to parent for reflection, action hints, etc. */
  streamCallbacks?: StreamingCallbacks;
  /** Current chat mode context — forwarded to backend for system prompt selection */
  mode?: ModeContext;
  /** Auto-send this message on mount (used by Home hero input handoff) */
  initialMessage?: string;
  /** Called after initialMessage has been sent */
  onInitialMessageSent?: () => void;
}

export function useChatPanelState({ threadId, onCreateCase, streamCallbacks, mode, initialMessage, onInitialMessageSent }: UseChatPanelStateOptions) {
  // --- Core streaming (delegated) ---
  const streaming = useStreamingChat({
    threadId,
    context: mode ? {
      mode: mode.mode,
      caseId: mode.caseId,
      inquiryId: mode.inquiryId,
    } : undefined,
    streamCallbacks: {
      ...streamCallbacks,
      // Intercept signals to merge into local state
      onSignals: (newSignals) => {
        setSignals(prev => {
          const existingIds = new Set(prev.map(s => s.id));
          const unique = newSignals.filter(s => !existingIds.has(s.id));
          return unique.length > 0 ? [...prev, ...unique] : prev;
        });
        // Also forward to parent
        streamCallbacks?.onSignals?.(newSignals);
      },
      // Intercept onMessageComplete for case analysis trigger
      onMessageComplete: (messageId) => {
        conversationTurns.current += 1;
        streamCallbacks?.onMessageComplete?.(messageId);

        // Trigger case analysis after 4 turns
        if (conversationTurns.current >= 4 && onCreateCase && !showCaseSuggestion && !analyzing) {
          setAnalyzing(true);
          chatAPI.analyzeForCase(threadId).then(analysis => {
            setCaseAnalysis(analysis);
            setShowCaseSuggestion(true);
          }).catch(err => {
            console.error('Failed to analyze for case:', err);
          }).finally(() => {
            setAnalyzing(false);
          });
        }
      },
    },
  });

  // --- Signals state ---
  const [signals, setSignals] = useState<Signal[]>([]);

  // --- UI state ---
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [signalsExpanded, setSignalsExpanded] = useState(false);

  // --- Case analysis state ---
  const [showCaseSuggestion, setShowCaseSuggestion] = useState(false);
  const [caseAnalysis, setCaseAnalysis] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [creatingCase, setCreatingCase] = useState(false);
  const [showAssembly, setShowAssembly] = useState(false);

  const conversationTurns = useRef(0);

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

  return {
    // Core streaming state (spread from useStreamingChat)
    ...streaming,

    // Signals
    signals,
    signalsExpanded,
    setSignalsExpanded,

    // UI
    isCollapsed,
    setIsCollapsed,

    // Case analysis
    showCaseSuggestion,
    setShowCaseSuggestion,
    caseAnalysis,
    creatingCase,
    setCreatingCase,
    showAssembly,
    setShowAssembly,
  };
}
