/**
 * useStreamingChat — Shared streaming core for unified chat.
 *
 * Extracts the ~200 lines of identical streaming logic previously duplicated
 * between ChatPanel and useChatPanelState:
 * - Message loading on threadId change
 * - Optimistic message creation (local-user-* / local-assistant-*)
 * - chatAPI.sendUnifiedStream() call with all callback wiring
 * - TTFT + total stream timeout with AbortController
 * - Error state + retry
 *
 * Consumers (ChatPanel via useChatPanelState) add their own UI and
 * domain-specific state on top.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { chatAPI } from '@/lib/api/chat';
import { TIMEOUT } from '@/lib/constants';
import type { Message } from '@/lib/types/chat';
import type { StreamingCallbacks } from '@/lib/types/streaming';

const TTFT_TIMEOUT_MS = TIMEOUT.TTFT;
const TOTAL_STREAM_TIMEOUT_MS = TIMEOUT.STREAM_TOTAL;

export interface UseStreamingChatOptions {
  threadId: string;
  /** Mode context forwarded to backend for system prompt selection and metadata */
  context?: { mode?: string; caseId?: string; inquiryId?: string; source_type?: string; source_id?: string };
  /** Callbacks for reflection, action hints forwarded to parent */
  streamCallbacks?: StreamingCallbacks;
  /** Skip loading existing messages on mount (for brand-new threads with initial message handoff) */
  skipInitialLoad?: boolean;
}

export interface UseStreamingChatReturn {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  isLoading: boolean;
  isWaitingForResponse: boolean;
  isStreaming: boolean;
  ttft: number | null;
  error: string | null;
  lastFailedMessage: string | null;
  sendMessage: (content: string) => Promise<void>;
  stopGeneration: () => void;
  handleRetry: () => void;
  clearError: () => void;
}

export function useStreamingChat({
  threadId,
  context,
  streamCallbacks,
  skipInitialLoad,
}: UseStreamingChatOptions): UseStreamingChatReturn {
  // --- Chat state ---
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingSince, setPendingSince] = useState<number | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [ttft, setTtft] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);

  // Refs for timeout tracking
  const ttftTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const totalTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const firstTokenReceivedRef = useRef(false);

  // Stable ref for streamCallbacks to avoid re-creating sendMessage on every render
  const streamCallbacksRef = useRef(streamCallbacks);
  streamCallbacksRef.current = streamCallbacks;

  // Stable ref for context
  const contextRef = useRef(context);
  contextRef.current = context;

  // Helper to clear all stream-related timeouts
  const clearStreamTimeouts = useCallback(() => {
    if (ttftTimeoutRef.current) {
      clearTimeout(ttftTimeoutRef.current);
      ttftTimeoutRef.current = null;
    }
    if (totalTimeoutRef.current) {
      clearTimeout(totalTimeoutRef.current);
      totalTimeoutRef.current = null;
    }
  }, []);

  // Load messages on thread change (skip for brand-new threads with initial message handoff)
  useEffect(() => {
    if (skipInitialLoad) return;
    async function loadMessages() {
      setIsLoading(true);
      try {
        const msgs = await chatAPI.getMessages(threadId);
        setMessages(msgs);
        setError(null);
      } catch (err) {
        console.error('Failed to load messages:', err);
        setError(err instanceof Error ? err.message : 'Failed to load messages');
      } finally {
        setIsLoading(false);
      }
    }
    loadMessages();
  }, [threadId, skipInitialLoad]);

  // Send message with unified streaming
  const sendMessage = useCallback(async (content: string) => {
    setIsLoading(true);
    setIsWaitingForResponse(true);
    const requestStart = Date.now();
    setPendingSince(requestStart);
    setTtft(null);
    setError(null);
    setLastFailedMessage(null);
    firstTokenReceivedRef.current = false;
    clearStreamTimeouts();

    const controller = new AbortController();
    setAbortController(controller);

    // Set up TTFT timeout
    ttftTimeoutRef.current = setTimeout(() => {
      if (!firstTokenReceivedRef.current && !controller.signal.aborted) {
        console.warn(`[useStreamingChat] TTFT timeout: no response after ${TTFT_TIMEOUT_MS}ms`);
        setLastFailedMessage(content);
        setError(`Response timed out. The server didn't respond within ${TTFT_TIMEOUT_MS / 1000} seconds.`);
        controller.abort();
      }
    }, TTFT_TIMEOUT_MS);

    // Set up total stream timeout
    totalTimeoutRef.current = setTimeout(() => {
      if (!controller.signal.aborted) {
        console.warn(`[useStreamingChat] Total stream timeout: stream exceeded ${TOTAL_STREAM_TIMEOUT_MS}ms`);
        setLastFailedMessage(content);
        setError(`Stream timed out after ${TOTAL_STREAM_TIMEOUT_MS / 1000} seconds.`);
        controller.abort();
      }
    }, TOTAL_STREAM_TIMEOUT_MS);

    const now = new Date().toISOString();
    const tempUserId = `local-user-${Date.now()}`;
    const tempAssistantId = `local-assistant-${Date.now()}`;

    try {
      // Optimistic messages
      const optimisticUserMessage: Message = {
        id: tempUserId,
        thread: threadId,
        role: 'user',
        content,
        event_id: '',
        metadata: {},
        created_at: now,
      };

      const optimisticAssistantMessage: Message = {
        id: tempAssistantId,
        thread: threadId,
        role: 'assistant',
        content: '',
        event_id: '',
        metadata: { streaming: true, unified: true },
        created_at: now,
      };

      setMessages(prev => [...prev, optimisticUserMessage, optimisticAssistantMessage]);
      setIsStreaming(true);

      try {
        await chatAPI.sendUnifiedStream(
          threadId,
          content,
          {
            onResponseChunk: (delta) => {
              // Track TTFT and clear TTFT timeout
              if (!firstTokenReceivedRef.current) {
                firstTokenReceivedRef.current = true;
                setTtft(Date.now() - requestStart);
                if (ttftTimeoutRef.current) {
                  clearTimeout(ttftTimeoutRef.current);
                  ttftTimeoutRef.current = null;
                }
              }

              // Update synchronously — no startTransition batching, so tokens
              // render immediately as they arrive from the SSE stream.
              setMessages(prev =>
                prev.map(msg =>
                  msg.id === tempAssistantId
                    ? { ...msg, content: msg.content + delta }
                    : msg
                )
              );
            },
            onReflectionChunk: (delta) => {
              streamCallbacksRef.current?.onReflectionChunk?.(delta);
            },
            onReflectionComplete: (reflectionContent) => {
              streamCallbacksRef.current?.onReflectionComplete?.(reflectionContent);
            },
            onActionHints: (hints) => {
              streamCallbacksRef.current?.onActionHints?.(hints);
            },
            onGraphEdits: (summary) => {
              streamCallbacksRef.current?.onGraphEdits?.(summary);
            },
            onTitleUpdate: (title) => {
              streamCallbacksRef.current?.onTitleUpdate?.(title);
            },
            onDone: (result) => {
              clearStreamTimeouts();
              setIsWaitingForResponse(false);
              setIsStreaming(false);
              setPendingSince(null);

              // Replace temp ID with real message ID
              if (result.messageId) {
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === tempAssistantId
                      ? { ...msg, id: result.messageId!, metadata: { ...msg.metadata, streaming: false } }
                      : msg
                  )
                );
              }

              // Notify parent
              streamCallbacksRef.current?.onMessageComplete?.(result.messageId);
            },
            onError: (errorMsg) => {
              console.error('[useStreamingChat] Unified stream error:', errorMsg);
              clearStreamTimeouts();
              setLastFailedMessage(content);
              setError(errorMsg);
              setIsStreaming(false);
              setIsWaitingForResponse(false);
            },
          },
          controller.signal,
          contextRef.current
        );
      } catch (streamError) {
        clearStreamTimeouts();

        if (streamError instanceof Error && streamError.name === 'AbortError') {
          // Timeout aborts handled in timeout callbacks; user-initiated aborts are clean
          setIsStreaming(false);
          setIsWaitingForResponse(false);
          setPendingSince(null);
          return;
        }

        console.error('[useStreamingChat] Streaming failed:', streamError);
        setLastFailedMessage(content);
        setError(streamError instanceof Error ? streamError.message : 'Streaming failed. Please try again.');
        setMessages(prev => prev.filter(m => m.id !== tempAssistantId));
        setIsWaitingForResponse(false);
        setIsStreaming(false);
        setPendingSince(null);
      }
    } catch (err) {
      console.error('[useStreamingChat] Send error:', err);
      clearStreamTimeouts();
      setLastFailedMessage(content);
      setError(err instanceof Error ? err.message : 'Failed to send message. Please try again.');
      setIsWaitingForResponse(false);
      setIsStreaming(false);
      setPendingSince(null);
    } finally {
      setIsLoading(false);
      setAbortController(null);
    }
  }, [threadId, clearStreamTimeouts]);

  // Stop generation
  const stopGeneration = useCallback(() => {
    if (abortController) {
      clearStreamTimeouts();
      abortController.abort();
      setAbortController(null);
      setIsStreaming(false);
      setIsWaitingForResponse(false);
      setIsLoading(false);

      // Clean up optimistic streaming messages
      setMessages(prev =>
        prev.filter(msg => msg.metadata?.streaming !== true)
      );
    }
  }, [abortController, clearStreamTimeouts]);

  // Retry last failed message
  const handleRetry = useCallback(() => {
    if (lastFailedMessage) {
      const messageToRetry = lastFailedMessage;
      setError(null);
      setLastFailedMessage(null);
      // Remove orphaned local messages
      setMessages(prev => prev.filter(msg => !msg.id.startsWith('local-')));
      sendMessage(messageToRetry);
    }
  }, [lastFailedMessage, sendMessage]);

  // Clear error state
  const clearError = useCallback(() => {
    setError(null);
    setLastFailedMessage(null);
    setMessages(prev => prev.filter(msg => !msg.id.startsWith('local-')));
  }, []);

  return {
    messages,
    setMessages,
    isLoading,
    isWaitingForResponse,
    isStreaming,
    ttft,
    error,
    lastFailedMessage,
    sendMessage,
    stopGeneration,
    handleRetry,
    clearError,
  };
}
