/**
 * Hook for real-time reasoning companion updates via SSE
 */

import { useState, useEffect, useCallback } from 'react';
import { EventSourcePlus } from 'event-source-plus';
import type { Reflection, BackgroundActivity, CompanionEvent } from '@/lib/types/companion';

export function useReasoningCompanion(threadId: string | null) {
  const [reflection, setReflection] = useState<Reflection | null>(null);
  const [backgroundActivity, setBackgroundActivity] = useState<BackgroundActivity | null>(null);
  const [currentTopic, setCurrentTopic] = useState<string | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!threadId) {
      return;
    }

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const eventSourceUrl = `${backendUrl}/api/chat/threads/${threadId}/companion-stream/`;
    
    console.log('[Companion] Connecting to:', eventSourceUrl);
    
    // Use event-source-plus with proper authentication headers
    const eventSource = new EventSourcePlus(eventSourceUrl, {
      // LLM-optimized retry strategy: only retry on errors, not after stream ends
      retryStrategy: 'on-error',
      maxRetryCount: 5,
      maxRetryInterval: 8000, // Max 8s between retries
      
      // Headers function - gets fresh token on each request/retry
      headers: () => {
        const token = localStorage.getItem('auth_token');
        if (!token) {
          console.error('[Companion] No auth token found');
          return {};
        }
        return {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream',
        };
      },
    });

    const controller = eventSource.listen({
      onMessage: (message) => {
        console.log('[Companion] Raw message received:', message);
        try {
          // Skip heartbeat messages
          if (message.data && message.data.startsWith(':')) {
            return;
          }

          const data: CompanionEvent = JSON.parse(message.data);
          console.log('[Companion] Parsed event:', data.type, 'Delta length:', (data as any).delta?.length);

          if (data.type === 'status') {
            // Handle status messages (e.g., "Waiting for conversation to begin...")
            console.log('[Companion] Status:', (data as any).message);
            setIsActive(true);
          } else if (data.type === 'reflection_chunk') {
            const delta = (data as any).delta || '';
            setReflection(prev => {
              const currentText = prev?.text || '';
              const newText = currentText + delta;
              return {
                id: prev?.id || 'streaming',
                text: newText,
                trigger_type: prev?.trigger_type || 'periodic',
                patterns: prev?.patterns || {
                  ungrounded_assumptions: [],
                  contradictions: [],
                  strong_claims: [],
                  recurring_themes: [],
                  missing_considerations: []
                },
                created_at: prev?.created_at || new Date().toISOString()
              };
            });
          } else if (data.type === 'reflection_complete') {
            console.log('[Companion] Reflection complete');
            setReflection({
              id: (data as any).id || Date.now().toString(),
              text: data.text || '',
              trigger_type: (data as any).trigger_type || 'periodic',
              patterns: data.patterns || {
                ungrounded_assumptions: [],
                contradictions: [],
                strong_claims: [],
                recurring_themes: [],
                missing_considerations: []
              },
              created_at: new Date().toISOString()
            });
            
            if ((data as any).current_topic) {
              setCurrentTopic((data as any).current_topic);
            }
          } else if (data.type === 'background_update') {
            setBackgroundActivity(data.activity || null);
          }
        } catch (err) {
          console.error('[Companion] Failed to parse event:', err);
        }
      },

      onResponse: ({ response }) => {
        console.log('[Companion] Connection opened, status:', response.status);
        setIsActive(true);
        setError(null);
      },

      onResponseError: ({ response }) => {
        console.error('[Companion] Response error:', response.status);
        
        // Handle different error types
        if (response.status === 401 || response.status === 403) {
          setError('Authentication failed. Please log in again.');
          controller.abort(); // Don't retry auth errors
        } else {
          setError(`Connection error (${response.status}). Retrying...`);
        }
        setIsActive(false);
      },

      onRequestError: ({ error }) => {
        console.error('[Companion] Request error:', error);
        setError('Connection lost. Reconnecting...');
        setIsActive(false);
      },
    });

    // Cleanup on unmount or threadId change
    return () => {
      console.log('[Companion] Cleaning up connection');
      controller.abort();
      setIsActive(false);
    };
  }, [threadId]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    reflection,
    backgroundActivity,
    currentTopic,
    isActive,
    error,
    clearError
  };
}
