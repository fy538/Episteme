/**
 * useHomeState Hook
 *
 * Simplified home state — the home page is now dashboard-only.
 * When the user sends a message via the hero input, we:
 * 1. Create a thread
 * 2. Store the initial message in sessionStorage
 * 3. Navigate to /chat/[threadId]
 *
 * No longer manages chat thread state, companion state, or view toggling.
 */

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { chatAPI } from '@/lib/api/chat';
import { useTypewriter } from './useTypewriter';
import { useReducedMotion } from './useReducedMotion';

const PLACEHOLDER_SUGGESTIONS = [
  'Help me think through a hiring decision...',
  'What are the blind spots in my analysis?',
  'Compare my options for the market entry...',
  'What evidence am I missing?',
  'Walk me through the key tensions...',
  'Summarize where things stand...',
];

export function useHomeState() {
  const router = useRouter();

  // --- UI state ---
  const [networkError, setNetworkError] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // --- Typewriter placeholder ---
  const prefersReducedMotion = useReducedMotion();
  const typewriterText = useTypewriter({
    phrases: PLACEHOLDER_SUGGESTIONS,
    disabled: prefersReducedMotion,
  });

  // Hero input send — create thread, store message, navigate to /chat/[threadId]
  const handleHeroSend = useCallback(async (content: string) => {
    try {
      // Start fade-out animation
      setIsTransitioning(true);

      // Create a new thread
      const thread = await chatAPI.createThread();

      // Store the initial message in sessionStorage for the chat page to pick up
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('episteme_initial_message', content);
      }

      // Navigate to the conversation page
      router.push(`/chat/${thread.id}`);
    } catch (err) {
      console.error('Failed to start conversation:', err);
      setIsTransitioning(false);
      setNetworkError(true);
    }
  }, [router]);

  return {
    // UI state
    networkError,
    setNetworkError,
    isTransitioning,

    // Hero send
    handleHeroSend,

    // Placeholder
    currentPlaceholder: typewriterText || PLACEHOLDER_SUGGESTIONS[0],
  };
}

export { PLACEHOLDER_SUGGESTIONS };
