/**
 * Hook for real-time reasoning companion updates via SSE
 */

import { useState, useEffect, useCallback } from 'react';
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
    
    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource(eventSourceUrl, {
        withCredentials: true
      });

      eventSource.onopen = () => {
        setIsActive(true);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        try {
          // Skip heartbeat messages
          if (event.data.startsWith(':')) {
            return;
          }

          const data: CompanionEvent = JSON.parse(event.data);

          if (data.type === 'reflection_chunk') {
            // Stream token-by-token - append to existing reflection
            setReflection(prev => {
              const currentText = prev?.text || '';
              return {
                id: prev?.id || 'streaming',
                text: currentText + ((data as any).delta || ''),
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
            // Finalize reflection with ID and patterns
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
            
            // Update current topic for semantic highlighting
            if ((data as any).current_topic) {
              setCurrentTopic((data as any).current_topic);
            }
          } else if (data.type === 'background_update') {
            setBackgroundActivity(data.activity || null);
          }
        } catch (err) {
          console.error('Failed to parse companion event:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('Companion SSE error:', err);
        setError('Connection lost. Reconnecting...');
        setIsActive(false);
        
        // EventSource automatically reconnects, but we can close and recreate
        // if we want custom reconnect logic
      };

    } catch (err) {
      console.error('Failed to create EventSource:', err);
      setError('Failed to connect to reasoning companion');
    }

    // Cleanup on unmount or threadId change
    return () => {
      if (eventSource) {
        eventSource.close();
        setIsActive(false);
      }
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
