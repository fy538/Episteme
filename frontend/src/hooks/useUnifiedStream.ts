/**
 * Hook for unified streaming of chat response, reflection, and signals
 *
 * Consolidates chat streaming, companion reflection, and signal extraction
 * into a single SSE connection with sectioned streaming.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import type { Signal } from '@/lib/types/signal';

interface UnifiedStreamState {
  /** Current response content (streaming) */
  response: string;
  /** Current reflection content (streaming) */
  reflection: string;
  /** Extracted signals (after stream completes) */
  signals: Signal[];
  /** Whether currently streaming */
  isStreaming: boolean;
  /** Whether response section is complete */
  isResponseComplete: boolean;
  /** Whether reflection section is complete */
  isReflectionComplete: boolean;
  /** Error message if any */
  error: string | null;
  /** Last completed message ID */
  messageId: string | null;
  /** Last completed reflection ID */
  reflectionId: string | null;
}

interface UseUnifiedStreamOptions {
  /** Called when response content updates */
  onResponseChunk?: (delta: string, fullContent: string) => void;
  /** Called when reflection content updates */
  onReflectionChunk?: (delta: string, fullContent: string) => void;
  /** Called when response is complete */
  onResponseComplete?: (content: string) => void;
  /** Called when reflection is complete */
  onReflectionComplete?: (content: string) => void;
  /** Called when signals are extracted */
  onSignals?: (signals: Signal[]) => void;
  /** Called when stream is done */
  onDone?: (result: {
    messageId: string | null;
    reflectionId: string | null;
    signalsCount: number;
  }) => void;
  /** Called on error */
  onError?: (error: string) => void;
}

export function useUnifiedStream(
  threadId: string | null,
  options: UseUnifiedStreamOptions = {}
) {
  const [state, setState] = useState<UnifiedStreamState>({
    response: '',
    reflection: '',
    signals: [],
    isStreaming: false,
    isResponseComplete: false,
    isReflectionComplete: false,
    error: null,
    messageId: null,
    reflectionId: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  // Use ref for options to avoid recreating sendMessage on every render
  const optionsRef = useRef(options);
  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  /**
   * Send a message and stream the unified response
   */
  const sendMessage = useCallback(
    async (content: string): Promise<void> => {
      if (!threadId) {
        throw new Error('No thread ID provided');
      }

      // Reset state
      setState({
        response: '',
        reflection: '',
        signals: [],
        isStreaming: true,
        isResponseComplete: false,
        isReflectionComplete: false,
        error: null,
        messageId: null,
        reflectionId: null,
      });

      // Create abort controller
      const controller = new AbortController();
      abortControllerRef.current = controller;

      const backendUrl =
        process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
      const token = localStorage.getItem('auth_token');

      try {
        const response = await fetch(
          `${backendUrl}/chat/threads/${threadId}/unified-stream/`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Accept: 'text/event-stream',
              ...(token && { Authorization: `Bearer ${token}` }),
            },
            body: JSON.stringify({ content }),
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || `HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body');
        }

        const decoder = new TextDecoder();
        let buffer = '';
        let responseContent = '';
        let reflectionContent = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events
          const events = buffer.split('\n\n');
          buffer = events.pop() || '';

          for (const raw of events) {
            const lines = raw.split('\n');
            let eventType = 'message';
            let dataPayload = '';

            for (const line of lines) {
              if (line.startsWith('event:')) {
                eventType = line.replace('event:', '').trim();
              } else if (line.startsWith('data:')) {
                dataPayload += line.replace('data:', '').trim();
              }
            }

            if (!dataPayload) continue;

            try {
              const data = JSON.parse(dataPayload);

              switch (eventType) {
                case 'response_chunk':
                  responseContent += data.delta || '';
                  setState((prev) => ({
                    ...prev,
                    response: responseContent,
                  }));
                  optionsRef.current.onResponseChunk?.(data.delta, responseContent);
                  break;

                case 'reflection_chunk':
                  reflectionContent += data.delta || '';
                  setState((prev) => ({
                    ...prev,
                    reflection: reflectionContent,
                  }));
                  optionsRef.current.onReflectionChunk?.(data.delta, reflectionContent);
                  break;

                case 'response_complete':
                  responseContent = data.content || responseContent;
                  setState((prev) => ({
                    ...prev,
                    response: responseContent,
                    isResponseComplete: true,
                  }));
                  optionsRef.current.onResponseComplete?.(responseContent);
                  break;

                case 'reflection_complete':
                  reflectionContent = data.content || reflectionContent;
                  setState((prev) => ({
                    ...prev,
                    reflection: reflectionContent,
                    isReflectionComplete: true,
                  }));
                  optionsRef.current.onReflectionComplete?.(reflectionContent);
                  break;

                case 'signals':
                  const signals = data.signals || [];
                  setState((prev) => ({
                    ...prev,
                    signals,
                  }));
                  optionsRef.current.onSignals?.(signals);
                  break;

                case 'done':
                  setState((prev) => ({
                    ...prev,
                    isStreaming: false,
                    messageId: data.message_id,
                    reflectionId: data.reflection_id,
                  }));
                  optionsRef.current.onDone?.({
                    messageId: data.message_id,
                    reflectionId: data.reflection_id,
                    signalsCount: data.signals_count || 0,
                  });
                  break;

                case 'error':
                  const errorMsg = data.error || 'Unknown error';
                  setState((prev) => ({
                    ...prev,
                    isStreaming: false,
                    error: errorMsg,
                  }));
                  optionsRef.current.onError?.(errorMsg);
                  break;
              }
            } catch (parseError) {
              console.warn('[UnifiedStream] Failed to parse event:', parseError);
            }
          }
        }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          console.log('[UnifiedStream] Stream aborted');
          setState((prev) => ({
            ...prev,
            isStreaming: false,
          }));
          return;
        }

        const errorMsg =
          error instanceof Error ? error.message : 'Stream failed';
        console.error('[UnifiedStream] Error:', errorMsg);
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: errorMsg,
        }));
        optionsRef.current.onError?.(errorMsg);
      } finally {
        abortControllerRef.current = null;
      }
    },
    [threadId]
  );

  /**
   * Stop the current stream
   */
  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setState((prev) => ({
        ...prev,
        isStreaming: false,
      }));
    }
  }, []);

  /**
   * Clear the current state
   */
  const clear = useCallback(() => {
    setState({
      response: '',
      reflection: '',
      signals: [],
      isStreaming: false,
      isResponseComplete: false,
      isReflectionComplete: false,
      error: null,
      messageId: null,
      reflectionId: null,
    });
  }, []);

  return {
    ...state,
    sendMessage,
    stopStream,
    clear,
  };
}
