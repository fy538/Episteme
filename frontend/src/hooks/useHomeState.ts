/**
 * useHomeState Hook
 *
 * Extracts state from Home.tsx into organized groups:
 * - Thread state: threadId, hasMessages, isInitializing, networkError
 * - Hero → Chat handoff: pendingMessage
 * - Rotating placeholder: placeholderIndex
 * - UI: sidebarCollapsed
 */

import { useState, useEffect, useCallback } from 'react';
import { chatAPI } from '@/lib/api/chat';
import { useTypewriter } from './useTypewriter';
import { useReducedMotion } from './useReducedMotion';
import { useCompanionState } from './useCompanionState';

const PLACEHOLDER_SUGGESTIONS = [
  'Help me think through a hiring decision...',
  'What are the blind spots in my analysis?',
  'Compare my options for the market entry...',
  'What evidence am I missing?',
  'Walk me through the key tensions...',
  'Summarize where things stand...',
];

export function useHomeState() {
  // --- UI state ---
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // --- Thread state ---
  const [threadId, setThreadId] = useState<string | null>(null);
  const [hasMessages, setHasMessages] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [networkError, setNetworkError] = useState(false);

  // --- Hero → Chat handoff ---
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // --- Typewriter placeholder ---
  const prefersReducedMotion = useReducedMotion();
  const typewriterText = useTypewriter({
    phrases: PLACEHOLDER_SUGGESTIONS,
    disabled: hasMessages || prefersReducedMotion,
  });

  // Initialize thread — always start fresh
  useEffect(() => {
    async function initThread() {
      try {
        setIsInitializing(true);
        const newThread = await chatAPI.createThread();
        setThreadId(newThread.id);
      } catch (err) {
        console.error('Failed to initialize thread:', err);
        setNetworkError(true);
      } finally {
        setIsInitializing(false);
      }
    }
    initThread();
  }, []);

  // Hero input send — fade out home, then swap to chat
  const handleHeroSend = useCallback((content: string) => {
    setPendingMessage(content);
    setIsTransitioning(true);
    // Wait for fade-out to complete before swapping views
    setTimeout(() => {
      setHasMessages(true);
      setIsTransitioning(false);
    }, 200);
  }, []);

  // Create new thread — fade out chat, then swap back to home
  const handleNewThread = useCallback(async () => {
    try {
      const newThread = await chatAPI.createThread();
      // Trigger fade-out on chat view, then swap to home
      setIsTransitioning(true);
      setTimeout(() => {
        setThreadId(newThread.id);
        setHasMessages(false);
        setPendingMessage(null);
        setIsTransitioning(false);
      }, 200);
    } catch (err) {
      console.error('Failed to create thread:', err);
    }
  }, []);

  // Companion state — reflection, action hints, stream callbacks
  const onMessageComplete = useCallback(() => {
    setHasMessages(true);
  }, []);

  const companion = useCompanionState({
    mode: 'casual',
    onMessageComplete,
  });

  return {
    // UI
    sidebarCollapsed,
    setSidebarCollapsed,

    // Thread
    threadId,
    hasMessages,
    isInitializing,
    networkError,
    setNetworkError,

    // Hero → Chat
    pendingMessage,
    setPendingMessage,
    handleHeroSend,
    handleNewThread,
    isTransitioning,

    // Placeholder
    currentPlaceholder: typewriterText || PLACEHOLDER_SUGGESTIONS[0],

    // Companion — stream callbacks + renderable state
    streamCallbacks: companion.streamCallbacks,
    companionThinking: companion.companionThinking,
    actionHints: companion.actionHints,
    signals: companion.signals,
    companionPosition: companion.companionPosition,
    setCompanionPosition: companion.setCompanionPosition,
    toggleCompanion: companion.toggleCompanion,
    rankedSections: companion.rankedSections,
    pinnedSection: companion.pinnedSection,
    setPinnedSection: companion.setPinnedSection,
  };
}

export { PLACEHOLDER_SUGGESTIONS };
