/**
 * useChatMode - Hook for managing chat mode state
 *
 * Handles transitions between:
 * - casual: General conversation
 * - case: Working within a specific case
 * - inquiry_focus: Focused on a specific inquiry within a case
 */

'use client';

import { useState, useCallback, useEffect } from 'react';
import type { ChatMode, ModeContext } from '@/lib/types/companion';

interface UseChatModeOptions {
  threadId: string | null;
  initialCaseId?: string | null;
  initialCaseName?: string;
  onModeChange?: (mode: ModeContext) => void;
}

interface UseChatModeReturn {
  mode: ModeContext;
  transitionToCase: (caseId: string, caseName: string) => void;
  focusOnInquiry: (inquiryId: string, inquiryTitle: string) => void;
  exitFocus: () => void;
  exitCase: () => void;
  setMode: (mode: ModeContext) => void;
}

export function useChatMode({
  threadId,
  initialCaseId,
  initialCaseName,
  onModeChange,
}: UseChatModeOptions): UseChatModeReturn {
  // Initialize mode based on whether we have a case
  const [mode, setModeState] = useState<ModeContext>(() => {
    if (initialCaseId && initialCaseName) {
      return {
        mode: 'case',
        caseId: initialCaseId,
        caseName: initialCaseName,
      };
    }
    return { mode: 'casual' };
  });

  // Update mode when initial case changes
  useEffect(() => {
    if (initialCaseId && initialCaseName) {
      setModeState({
        mode: 'case',
        caseId: initialCaseId,
        caseName: initialCaseName,
      });
    }
  }, [initialCaseId, initialCaseName]);

  // Wrapper for setMode that also calls callback
  const setMode = useCallback(
    (newMode: ModeContext) => {
      setModeState(newMode);
      onModeChange?.(newMode);
    },
    [onModeChange]
  );

  /**
   * Transition from casual to case mode
   */
  const transitionToCase = useCallback(
    (caseId: string, caseName: string) => {
      const newMode: ModeContext = {
        mode: 'case',
        caseId,
        caseName,
      };
      setMode(newMode);
    },
    [setMode]
  );

  /**
   * Focus on a specific inquiry within the current case
   */
  const focusOnInquiry = useCallback(
    (inquiryId: string, inquiryTitle: string) => {
      setModeState((prev) => {
        // Can only focus if we're in a case
        if (prev.mode === 'casual') {
          console.warn('[useChatMode] Cannot focus on inquiry without a case');
          return prev;
        }

        const newMode: ModeContext = {
          mode: 'inquiry_focus',
          caseId: prev.caseId,
          caseName: prev.caseName,
          inquiryId,
          inquiryTitle,
        };

        onModeChange?.(newMode);
        return newMode;
      });
    },
    [onModeChange]
  );

  /**
   * Exit inquiry focus, return to case mode
   */
  const exitFocus = useCallback(() => {
    setModeState((prev) => {
      if (prev.mode !== 'inquiry_focus') {
        return prev;
      }

      const newMode: ModeContext = {
        mode: 'case',
        caseId: prev.caseId,
        caseName: prev.caseName,
      };

      onModeChange?.(newMode);
      return newMode;
    });
  }, [onModeChange]);

  /**
   * Exit case mode entirely, return to casual
   */
  const exitCase = useCallback(() => {
    const newMode: ModeContext = { mode: 'casual' };
    setMode(newMode);
  }, [setMode]);

  return {
    mode,
    transitionToCase,
    focusOnInquiry,
    exitFocus,
    exitCase,
    setMode,
  };
}
