/**
 * CompanionPanel - Main container for the reasoning companion
 *
 * A vertical dashboard that shows:
 * - Reflection: Meta-cognitive commentary (always present)
 * - Activity: Current action progress/results (when applicable)
 * - Signals: Extracted signals list (expandable)
 * - Suggestions: Contextual actions (at bottom)
 *
 * Sections "breathe" - expand/contract based on relevance.
 */

'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { ReflectionSection } from './ReflectionSection';
import { ActivitySection } from './ActivitySection';
import { SignalsSection } from './SignalsSection';
import { SuggestionsSection } from './SuggestionsSection';
import type {
  CompanionSignal,
  ActiveAction,
  SuggestedAction,
  SignalValidationStatus,
} from '@/lib/types/companion';
import type { Signal } from '@/lib/types/signal';

interface CompanionPanelProps {
  threadId: string | null;
  caseId?: string | null;

  // Unified stream data
  reflection: string;
  isReflectionStreaming?: boolean;

  // Signals from unified stream or API
  signals: Signal[];

  // Active action state
  activeAction?: ActiveAction | null;
  onStopAction?: () => void;
  onDismissActionResult?: () => void;

  // Action handlers
  onValidateSignal?: (signal: CompanionSignal) => void;
  onValidateSignals?: (signals: CompanionSignal[]) => void;
  onDismissSignal?: (signal: CompanionSignal) => void;
  onSuggestionAction?: (action: SuggestedAction) => void;
  onDismissSuggestion?: (action: SuggestedAction) => void;
}

export function CompanionPanel({
  threadId,
  caseId,
  reflection,
  isReflectionStreaming = false,
  signals,
  activeAction,
  onStopAction,
  onDismissActionResult,
  onValidateSignal,
  onValidateSignals,
  onDismissSignal,
  onSuggestionAction,
  onDismissSuggestion,
}: CompanionPanelProps) {
  // Track dismissed suggestions locally
  const [dismissedSuggestions, setDismissedSuggestions] = useState<Set<string>>(
    new Set()
  );

  // Convert API signals to companion signals with validation status
  const companionSignals: CompanionSignal[] = useMemo(() => {
    return signals.map((signal) => ({
      id: signal.id,
      type: signal.type || signal.signal_type || 'Claim',
      text: signal.text || signal.content || '',
      confidence: signal.confidence,
      validationStatus: mapSignalStatus(signal),
      createdAt: signal.created_at,
    }));
  }, [signals]);

  // Generate suggestions based on signals and patterns
  const suggestions: SuggestedAction[] = useMemo(() => {
    const result: SuggestedAction[] = [];

    // Count pending assumptions
    const pendingAssumptions = companionSignals.filter(
      (s) => s.type === 'Assumption' && s.validationStatus === 'pending'
    );

    // Count questions
    const questions = companionSignals.filter((s) => s.type === 'Question');

    // Suggest validating assumptions
    if (pendingAssumptions.length >= 2) {
      result.push({
        id: 'validate-assumptions',
        type: 'validate_assumptions',
        label: `Validate ${pendingAssumptions.length} assumptions`,
        description: 'Research your assumptions to check if they hold',
        priority: 'high',
        targetIds: pendingAssumptions.map((s) => s.id),
        targetCount: pendingAssumptions.length,
      });
    }

    // Suggest organizing questions
    if (questions.length >= 3) {
      result.push({
        id: 'organize-questions',
        type: 'organize_questions',
        label: `Organize ${questions.length} questions`,
        description: 'Create an inquiry to track your investigation',
        priority: 'medium',
        targetIds: questions.map((s) => s.id),
        targetCount: questions.length,
      });
    }

    // Suggest creating a case if enough signals
    if (companionSignals.length >= 5) {
      const hasAssumptions = pendingAssumptions.length > 0;
      const hasQuestions = questions.length > 0;
      const claims = companionSignals.filter((s) => s.type === 'Claim');
      const goals = companionSignals.filter((s) => s.type === 'Goal');
      const hasClaims = claims.length > 0;

      if (hasAssumptions && hasQuestions && hasClaims) {
        // Derive suggested title from the most relevant signal
        // Priority: Goals > Claims > Assumptions
        const titleSource =
          goals[0]?.text ||
          claims[0]?.text ||
          pendingAssumptions[0]?.text ||
          '';

        // Extract a cleaner title (first sentence or phrase)
        let suggestedTitle = titleSource.split(/[.!?]/)[0].trim();
        if (suggestedTitle.length > 50) {
          suggestedTitle = suggestedTitle.slice(0, 47) + '...';
        }

        // Collect all signal IDs for potential LLM title generation
        const allTargetIds = companionSignals.map((s) => s.id);

        result.push({
          id: `create-case-${companionSignals.length}`, // Changes when signals change
          type: 'create_case',
          label: 'Structure this decision',
          description: `${companionSignals.length} signals to track`,
          priority: 'low',
          suggestedTitle: suggestedTitle || undefined,
          targetIds: allTargetIds,
          targetCount: companionSignals.length,
        });
      }
    }

    // Filter out dismissed suggestions (match by type for dynamic IDs like create-case)
    return result.filter((s) => {
      // For create-case, check if any create-case was dismissed
      if (s.type === 'create_case') {
        return !Array.from(dismissedSuggestions).some(id => id.startsWith('create-case'));
      }
      return !dismissedSuggestions.has(s.id);
    });
  }, [companionSignals, dismissedSuggestions]);

  // Handle dismissing suggestions
  const handleDismissSuggestion = useCallback(
    (action: SuggestedAction) => {
      setDismissedSuggestions((prev) => new Set([...prev, action.id]));
      onDismissSuggestion?.(action);
    },
    [onDismissSuggestion]
  );

  // Handle signal click - could show detail modal
  const handleSignalClick = useCallback((signal: CompanionSignal) => {
    // TODO: Show signal detail modal or highlight in chat
    console.log('[Companion] Signal clicked:', signal);
  }, []);

  if (!threadId) {
    return null;
  }

  const hasActiveAction = !!(activeAction && activeAction.status !== 'complete');
  const hasCompletedAction = !!(activeAction && activeAction.status === 'complete');

  return (
    <div className="w-96 border-l border-cyan-500/30 bg-[#0a0f14] flex flex-col h-full font-mono text-xs overflow-hidden">
      {/* Terminal Header */}
      <div className="px-3 py-2 border-b border-cyan-500/30 flex-shrink-0 bg-[#0a0f14]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-cyan-400">
            <span className={cn(
              'text-[10px]',
              isReflectionStreaming || hasActiveAction ? 'animate-pulse' : ''
            )}>
              {isReflectionStreaming || hasActiveAction ? '◉' : '○'}
            </span>
            <span className="text-[11px] tracking-wider">EPISTEME :: REASONING_CORE</span>
          </div>
          <span className="text-cyan-600 text-[10px]">v2.1.0</span>
        </div>
      </div>

      {/* Scrollable content area with terminal styling */}
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-cyan-900/50">
        {/* Reflection - always present */}
        <ReflectionSection
          content={reflection}
          isStreaming={isReflectionStreaming}
          collapsed={hasActiveAction}
        />

        {/* Activity - when action is running or just completed */}
        {activeAction && (
          <ActivitySection
            action={activeAction}
            onStop={onStopAction}
            onDismiss={onDismissActionResult}
          />
        )}

        {/* Signals - expandable list */}
        <SignalsSection
          signals={companionSignals}
          onSignalClick={handleSignalClick}
          onValidateSignal={onValidateSignal}
          onValidateAll={onValidateSignals}
          onDismissSignal={onDismissSignal}
        />
      </div>

      {/* Suggestions - sticks to bottom */}
      <SuggestionsSection
        suggestions={suggestions}
        onAction={(action) => onSuggestionAction?.(action)}
        onDismiss={handleDismissSuggestion}
      />
    </div>
  );
}

/**
 * Map API signal status to companion display status
 */
function mapSignalStatus(signal: Signal): SignalValidationStatus {
  if (signal.dismissed_at) {
    return 'dismissed';
  }

  // Check if signal has validation metadata (would need to add this to Signal type)
  // For now, all non-dismissed signals are pending
  return 'pending';
}
