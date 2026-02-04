/**
 * SuggestionsSection - Context-aware action suggestions
 *
 * Shows relevant actions based on current signals and patterns.
 * Sticks to bottom of companion panel.
 */

'use client';

import { cn } from '@/lib/utils';
import type { SuggestedAction } from '@/lib/types/companion';

interface SuggestionsSectionProps {
  suggestions: SuggestedAction[];
  onAction: (action: SuggestedAction) => void;
  onDismiss: (action: SuggestedAction) => void;
}

const priorityStyles: Record<string, { bg: string; border: string; text: string; label: string }> = {
  high: {
    bg: 'bg-amber-950/20',
    border: 'border-amber-800/50',
    text: 'text-amber-400',
    label: '[!]',
  },
  medium: {
    bg: 'bg-cyan-950/20',
    border: 'border-cyan-800/50',
    text: 'text-cyan-400',
    label: '[>]',
  },
  low: {
    bg: 'bg-cyan-950/10',
    border: 'border-cyan-900/30',
    text: 'text-cyan-500',
    label: '[~]',
  },
};

const actionLabels: Record<string, string> = {
  research_assumption: 'RESEARCH',
  validate_assumptions: 'VALIDATE',
  organize_questions: 'ORGANIZE',
  create_case: 'NEW_CASE',
  create_inquiry: 'NEW_INQUIRY',
};

export function SuggestionsSection({
  suggestions,
  onAction,
  onDismiss,
}: SuggestionsSectionProps) {
  if (suggestions.length === 0) {
    return null;
  }

  // Show only top 2 suggestions
  const visibleSuggestions = suggestions.slice(0, 2);

  return (
    <section className="px-3 py-2 border-t border-cyan-500/30 bg-[#0a0f14] flex-shrink-0">
      {/* Terminal header */}
      <div className="flex items-center gap-2 mb-2 font-mono">
        <span className="text-cyan-400 text-[10px]">{'>'}</span>
        <span className="text-[10px] tracking-wider font-medium text-cyan-400 uppercase">
          SUGGESTED_ACTIONS
        </span>
      </div>

      <div className="space-y-1.5">
        {visibleSuggestions.map((suggestion) => {
          const styles = priorityStyles[suggestion.priority];

          return (
            <div
              key={suggestion.id}
              className={cn(
                'group relative border transition-all duration-200 font-mono',
                styles.bg,
                styles.border,
                'hover:bg-opacity-40'
              )}
            >
              {/* Dismiss button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDismiss(suggestion);
                }}
                className="absolute top-1.5 right-1.5 p-0.5 opacity-0 group-hover:opacity-100 text-cyan-700 hover:text-cyan-500 transition-opacity text-[9px]"
              >
                [X]
              </button>

              {/* Action button */}
              <button
                onClick={() => onAction(suggestion)}
                className="w-full p-2 text-left"
              >
                <div className="flex items-start gap-2">
                  <span className={cn('text-[10px] font-medium tracking-wider', styles.text)}>
                    {styles.label}
                  </span>
                  <div className="flex-1 min-w-0 pr-6">
                    <p className={cn('text-[10px] font-medium tracking-wider uppercase', styles.text)}>
                      {actionLabels[suggestion.type] || suggestion.type}
                    </p>
                    <p className="text-[9px] text-cyan-600 mt-0.5 leading-relaxed">
                      {suggestion.description}
                    </p>
                  </div>
                  <span
                    className={cn(
                      'text-[10px] mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity',
                      styles.text
                    )}
                  >
                    →
                  </span>
                </div>
              </button>
            </div>
          );
        })}
      </div>

      {/* More suggestions indicator */}
      {suggestions.length > 2 && (
        <p className="text-[9px] text-cyan-700 text-center mt-1.5 font-mono">
          +{suggestions.length - 2} more
        </p>
      )}
    </section>
  );
}
