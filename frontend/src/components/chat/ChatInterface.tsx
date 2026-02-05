/**
 * Main chat interface component
 *
 * Now supports unified streaming which combines:
 * - Chat response streaming
 * - Companion reflection streaming
 * - Signal extraction
 *
 * All in a single LLM call for ~75% cost reduction.
 */

'use client';

import { useState, useEffect, startTransition, useCallback, useRef } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { Select } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { chatAPI } from '@/lib/api/chat';
import type { Message, InlineActionCard, ActionHint } from '@/lib/types/chat';
import type { CardAction } from '@/lib/types/cards';
import type { Signal } from '@/lib/types/signal';
import type { InlineCardActions } from './cards/InlineActionCardRenderer';
import { useCardActions } from '@/hooks/useCardActions';

import { TIMEOUT } from '@/lib/constants';

// Feature flag for unified streaming - can be toggled for rollout
const USE_UNIFIED_STREAM = true;

// Timeout constants for streaming (from centralized constants)
const TTFT_TIMEOUT_MS = TIMEOUT.TTFT;
const TOTAL_STREAM_TIMEOUT_MS = TIMEOUT.STREAM_TOTAL;

export interface UnifiedStreamCallbacks {
  /** Called when reflection content updates */
  onReflectionChunk?: (delta: string) => void;
  /** Called when reflection is complete */
  onReflectionComplete?: (content: string) => void;
  /** Called when signals are extracted */
  onSignals?: (signals: Signal[]) => void;
  /** Called when action hints are received from AI */
  onActionHints?: (hints: ActionHint[]) => void;
  /** Called when assistant message is complete (for title generation tracking) */
  onMessageComplete?: (messageId?: string) => void;
}

export function ChatInterface({
  threadId,
  onToggleLeft,
  onToggleRight,
  leftCollapsed,
  rightCollapsed,
  projects,
  projectId,
  onProjectChange,
  unifiedStreamCallbacks,
  inlineCards = [],
  inlineCardActions = {},
}: {
  threadId: string;
  onToggleLeft?: () => void;
  onToggleRight?: () => void;
  leftCollapsed?: boolean;
  rightCollapsed?: boolean;
  projects?: { id: string; title: string }[];
  projectId?: string | null;
  onProjectChange?: (projectId: string | null) => void;
  /** Callbacks for unified stream events (reflection, signals) */
  unifiedStreamCallbacks?: UnifiedStreamCallbacks;
  /** Inline action cards to display after messages */
  inlineCards?: InlineActionCard[];
  /** Actions for inline cards */
  inlineCardActions?: InlineCardActions;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingSince, setPendingSince] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [ttft, setTtft] = useState<number | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);

  // Refs for timeout tracking (need to persist across renders without re-triggering)
  const ttftTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const totalTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const firstTokenReceivedRef = useRef(false);

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

  // Card actions hook
  const { executeAction, isExecuting } = useCardActions();

  // Load messages on mount
  useEffect(() => {
    async function loadMessages() {
      try {
        const msgs = await chatAPI.getMessages(threadId);
        setMessages(msgs);
        setError(null); // Clear any previous errors
      } catch (error) {
        console.error('Failed to load messages:', error);
        setError(error instanceof Error ? error.message : 'Failed to load messages');
      }
    }
    loadMessages();
  }, [threadId]);

  // Poll for new messages only while waiting for response (non-streaming fallback)
  useEffect(() => {
    if (!isWaitingForResponse || isStreaming || isLoading) return;

    let pollCount = 0;
    let interval: NodeJS.Timeout;

    const getPollInterval = () => {
      if (pollCount < 5) return 2000; // 2s for first 10s
      if (pollCount < 10) return 4000; // 4s for next 20s
      return 8000; // 8s after 30s
    };

    const poll = async () => {
      try {
        const msgs = await chatAPI.getMessages(threadId);

        setMessages(prev => {
          // Merge server messages with optimistic messages
          const serverById = new Map(msgs.map(m => [m.id, m]));
          const merged: Message[] = [];

          // Keep optimistic messages (local ids) if server hasn't returned them yet
          for (const prevMsg of prev) {
            if (prevMsg.id.startsWith('local-')) {
              merged.push(prevMsg);
              continue;
            }
            const serverMsg = serverById.get(prevMsg.id);
            if (serverMsg) {
              merged.push(serverMsg);
              serverById.delete(prevMsg.id);
            } else {
              merged.push(prevMsg);
            }
          }

          // Append any new server messages not seen before
          for (const msg of serverById.values()) {
            merged.push(msg);
          }

          return merged;
        });

        if (pendingSince) {
          const hasNewAssistant = msgs.some(
            msg =>
              msg.role === 'assistant' &&
              new Date(msg.created_at).getTime() > pendingSince
          );
          if (hasNewAssistant) {
            setIsWaitingForResponse(false);
            setPendingSince(null);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
      } finally {
        pollCount += 1;
        clearInterval(interval);
        interval = setInterval(poll, getPollInterval());
      }
    };

    interval = setInterval(poll, getPollInterval());

    return () => clearInterval(interval);
  }, [threadId, isStreaming, isLoading, isWaitingForResponse, pendingSince]);

  /**
   * Send message using unified streaming (single LLM call for response + reflection + signals)
   */
  const handleSendMessageUnified = useCallback(async (content: string) => {
    setIsLoading(true);
    setIsWaitingForResponse(true);
    const requestStart = Date.now();
    setPendingSince(requestStart);
    setError(null);
    setTtft(null);
    setLastFailedMessage(null);
    firstTokenReceivedRef.current = false;
    clearStreamTimeouts();

    // Create AbortController for cancellation
    const controller = new AbortController();
    setAbortController(controller);

    // Set up TTFT timeout - abort if no first token within 30s
    ttftTimeoutRef.current = setTimeout(() => {
      if (!firstTokenReceivedRef.current && !controller.signal.aborted) {
        console.warn(`[Chat] TTFT timeout: no response after ${TTFT_TIMEOUT_MS}ms`);
        setLastFailedMessage(content);
        setError(`Response timed out. The server didn't respond within ${TTFT_TIMEOUT_MS / 1000} seconds.`);
        controller.abort();
      }
    }, TTFT_TIMEOUT_MS);

    // Set up total stream timeout - abort if stream takes too long
    totalTimeoutRef.current = setTimeout(() => {
      if (!controller.signal.aborted) {
        console.warn(`[Chat] Total stream timeout: stream exceeded ${TOTAL_STREAM_TIMEOUT_MS}ms`);
        setLastFailedMessage(content);
        setError(`Stream timed out after ${TOTAL_STREAM_TIMEOUT_MS / 1000} seconds.`);
        controller.abort();
      }
    }, TOTAL_STREAM_TIMEOUT_MS);

    try {
      const now = new Date().toISOString();
      const tempUserId = `local-user-${Date.now()}`;
      const tempAssistantId = `local-assistant-${Date.now()}`;

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
              // Track TTFT (time to first token) and clear TTFT timeout
              if (!firstTokenReceivedRef.current) {
                firstTokenReceivedRef.current = true;
                const ttftMs = Date.now() - requestStart;
                setTtft(ttftMs);
                // TTFT tracked

                // Clear TTFT timeout - we got our first token
                if (ttftTimeoutRef.current) {
                  clearTimeout(ttftTimeoutRef.current);
                  ttftTimeoutRef.current = null;
                }
              }

              // Use startTransition to batch rapid token updates (non-urgent)
              startTransition(() => {
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === tempAssistantId
                      ? { ...msg, content: `${msg.content}${delta}` }
                      : msg
                  )
                );
              });
            },
            onReflectionChunk: (delta) => {
              // Forward to unified stream callbacks
              unifiedStreamCallbacks?.onReflectionChunk?.(delta);
            },
            onReflectionComplete: (content) => {
              unifiedStreamCallbacks?.onReflectionComplete?.(content);
            },
            onSignals: (signals) => {
              // Signals extracted
              unifiedStreamCallbacks?.onSignals?.(signals as Signal[]);
            },
            onActionHints: (hints) => {
              // Action hints received
              unifiedStreamCallbacks?.onActionHints?.(hints);
            },
            onDone: (result) => {
              clearStreamTimeouts();
              setIsWaitingForResponse(false);
              setIsStreaming(false);
              setPendingSince(null);

              // Replace temp IDs with real message ID
              if (result.messageId) {
                setMessages(prev =>
                  prev.map(msg => {
                    if (msg.id === tempAssistantId) {
                      return { ...msg, id: result.messageId!, metadata: { ...msg.metadata, streaming: false } };
                    }
                    return msg;
                  })
                );
              }

              // Notify parent that message is complete (for title generation and inline cards)
              unifiedStreamCallbacks?.onMessageComplete?.(result.messageId);

              // Stream complete
            },
            onError: (errorMsg) => {
              console.error('[Chat] Unified stream error:', errorMsg);
              clearStreamTimeouts();
              setLastFailedMessage(content);
              setError(errorMsg);
              setIsStreaming(false);
              setIsWaitingForResponse(false);
            }
          },
          controller.signal
        );
      } catch (streamError) {
        clearStreamTimeouts();

        // Check if aborted - could be user-initiated or timeout
        if (streamError instanceof Error && streamError.name === 'AbortError') {
          // Timeout aborts are handled in the timeout callbacks which set error state
          // User-initiated aborts (via stop button) don't need error handling here
          // Stream aborted
          setIsStreaming(false);
          setIsWaitingForResponse(false);
          setPendingSince(null);
          return;
        }

        // Fallback to legacy streaming if unified isn't available
        console.warn('[Chat] Unified streaming failed, falling back to legacy.', streamError);
        setLastFailedMessage(content);
        throw streamError;
      }
    } catch (err) {
      console.error('Failed to send message:', err);
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
  }, [threadId, unifiedStreamCallbacks, clearStreamTimeouts]);

  /**
   * Send message using legacy streaming (separate LLM call)
   */
  const handleSendMessageLegacy = useCallback(async (content: string) => {
    setIsLoading(true);
    setIsWaitingForResponse(true);
    const requestStart = Date.now();
    setPendingSince(requestStart);
    setError(null);
    setTtft(null);

    // Create AbortController for cancellation
    const controller = new AbortController();
    setAbortController(controller);

    try {
      const now = new Date().toISOString();
      const tempUserId = `local-user-${Date.now()}`;
      const tempAssistantId = `local-assistant-${Date.now()}`;

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
        metadata: { streaming: true },
        created_at: now,
      };

      setMessages(prev => [...prev, optimisticUserMessage, optimisticAssistantMessage]);
      setIsStreaming(true);

      let firstTokenReceived = false;

      try {
        await chatAPI.sendMessageStream(
          threadId,
          content,
          (delta) => {
            // Track TTFT (time to first token)
            if (!firstTokenReceived) {
              const ttftMs = Date.now() - requestStart;
              setTtft(ttftMs);
              // TTFT tracked
              firstTokenReceived = true;
            }

            // Use startTransition to batch rapid token updates (non-urgent)
            startTransition(() => {
              setMessages(prev =>
                prev.map(msg =>
                  msg.id === tempAssistantId
                    ? { ...msg, content: `${msg.content}${delta}` }
                    : msg
                )
              );
            });
          },
          async (messageId) => {
            setIsWaitingForResponse(false);
            setIsStreaming(false);
            setPendingSince(null);

            // Replace temp IDs with real message ID (no refetch needed)
            if (messageId) {
              setMessages(prev =>
                prev.map(msg => {
                  if (msg.id === tempAssistantId) {
                    return { ...msg, id: messageId, metadata: { ...msg.metadata, streaming: false } };
                  }
                  if (msg.id === tempUserId) {
                    // User message is already saved, just keep optimistic for now
                    // Polling will eventually replace it with real ID
                    return msg;
                  }
                  return msg;
                })
              );
            }
          },
          controller.signal
        );
      } catch (streamError) {
        // Check if aborted by user
        if (streamError instanceof Error && streamError.name === 'AbortError') {
          // Stream aborted by user
          setIsStreaming(false);
          setIsWaitingForResponse(false);
          setPendingSince(null);
          return; // Don't fallback, user cancelled
        }

        // Fallback to non-streaming if stream isn't available
        console.warn('Streaming unavailable, falling back to polling.', streamError);
        setIsStreaming(false);

        // Keep optimistic user message, remove only the assistant placeholder
        setMessages(prev =>
          prev.filter(msg => msg.id !== tempAssistantId)
        );

        const userMessage = await chatAPI.sendMessage(threadId, content);
        setMessages(prev =>
          prev.map(msg => (msg.id === tempUserId ? userMessage : msg))
        );
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setError(error instanceof Error ? error.message : 'Failed to send message. Please try again.');
      setIsWaitingForResponse(false);
      setIsStreaming(false);
      setPendingSince(null);
    } finally {
      setIsLoading(false);
      setAbortController(null);
    }
  }, [threadId]);

  // Choose streaming method based on feature flag
  const handleSendMessage = USE_UNIFIED_STREAM ? handleSendMessageUnified : handleSendMessageLegacy;

  function handleStopGeneration() {
    if (abortController) {
      // Aborting stream
      clearStreamTimeouts();
      abortController.abort();
      setAbortController(null);
      setIsStreaming(false);
      setIsWaitingForResponse(false);
      setIsLoading(false);

      // Clean up optimistic assistant message
      setMessages(prev =>
        prev.filter(msg => msg.metadata?.streaming !== true)
      );
    }
  }

  function handleRetry() {
    if (lastFailedMessage) {
      const messageToRetry = lastFailedMessage;
      setError(null);
      setLastFailedMessage(null);

      // Remove any failed optimistic messages before retrying
      setMessages(prev =>
        prev.filter(msg => !msg.id.startsWith('local-'))
      );

      // Retry the message
      handleSendMessage(messageToRetry);
    }
  }

  function handleCardAction(action: CardAction, messageId: string) {
    // Card action executed

    executeAction({
      action,
      messageId,
      threadId
    });
  }

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="border-b border-neutral-200 p-4 space-y-3">
        <Breadcrumbs items={[{ label: 'Chat' }]} />

        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            {projects && onProjectChange && (
              <div className="flex items-center gap-2">
                <Label htmlFor="project-select" className="text-xs text-neutral-600">
                  Project
                </Label>
                <Select
                  id="project-select"
                  value={projectId || ''}
                  onChange={(e) => onProjectChange(e.target.value || null)}
                  className="h-8 text-xs w-48"
                >
                  <option value="">No Project</option>
                  {projects.map(project => (
                    <option key={project.id} value={project.id}>
                      {project.title}
                    </option>
                  ))}
                </Select>
              </div>
            )}
          </div>
          {/* Collapse buttons moved to panel edges - removed from header */}
        </div>
      </div>
      {error && (
        <div className="bg-error-50 border-l-4 border-error-500 p-4 mx-4 mt-4">
          <div className="flex items-start">
            <div className="flex-1">
              <p className="text-sm text-error-700">{error}</p>
              {lastFailedMessage && (
                <button
                  onClick={handleRetry}
                  className="mt-2 text-sm font-medium text-error-700 hover:text-error-900 underline"
                >
                  Retry message
                </button>
              )}
            </div>
            <button
              onClick={() => {
                setError(null);
                setLastFailedMessage(null);
                // Also clean up any orphaned local messages
                setMessages(prev => prev.filter(msg => !msg.id.startsWith('local-')));
              }}
              className="ml-4 text-error-700 hover:text-error-900"
            >
              ✕
            </button>
          </div>
        </div>
      )}
      <MessageList
        messages={messages}
        isWaitingForResponse={isWaitingForResponse}
        isStreaming={isStreaming}
        ttft={ttft}
        onCardAction={handleCardAction}
        inlineCards={inlineCards}
        inlineCardActions={inlineCardActions}
      />
      <MessageInput
        onSend={handleSendMessage}
        disabled={isLoading}
        isProcessing={isLoading || isWaitingForResponse}
        isStreaming={isStreaming}
        onStop={handleStopGeneration}
      />
    </div>
  );
}
