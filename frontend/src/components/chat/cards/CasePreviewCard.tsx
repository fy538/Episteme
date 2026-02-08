/**
 * CasePreviewCard - Rich preview of a structured case ready for creation
 *
 * Shown after the analyze_for_case API returns results. Displays the
 * suggested title, key questions, and assumptions. User can create the
 * case, adjust the framing (continues conversation), or dismiss.
 */

'use client';

import { Button } from '@/components/ui/button';
import {
  ActionCard,
  ActionCardHeader,
  ActionCardTitle,
  ActionCardFooter,
} from '@/components/ui/action-card';
import type { InlineActionCard, CasePreviewData } from '@/lib/types/chat';

interface CasePreviewCardProps {
  card: InlineActionCard;
  onCreateCase: (analysis: Record<string, unknown>, title: string) => void;
  onAdjust: () => void;
  onDismiss: () => void;
  isCreating?: boolean;
}

export function CasePreviewCard({
  card,
  onCreateCase,
  onAdjust,
  onDismiss,
  isCreating = false,
}: CasePreviewCardProps) {
  const data = card.data as unknown as CasePreviewData;
  const { suggestedTitle, keyQuestions, assumptions, decisionCriteria, analysis } = data;

  return (
    <div className="my-3">
      <ActionCard variant="accent">
        <ActionCardHeader>
          <ActionCardTitle>Case Preview</ActionCardTitle>

          {/* Title */}
          <div className="mt-3 text-sm font-medium text-neutral-900 dark:text-neutral-100">
            {suggestedTitle}
          </div>

          {/* Key questions */}
          {keyQuestions && keyQuestions.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Questions to investigate
              </div>
              <div className="space-y-1">
                {keyQuestions.map((q, i) => (
                  <div
                    key={i}
                    className="text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5"
                  >
                    <span className="text-accent-500 mt-px shrink-0">?</span>
                    <span>{q}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Assumptions */}
          {assumptions && assumptions.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Assumptions to test
              </div>
              <div className="space-y-1">
                {assumptions.map((a, i) => (
                  <div
                    key={i}
                    className="text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5"
                  >
                    <span className="text-neutral-400 mt-px shrink-0">&middot;</span>
                    <span>{a}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Decision criteria */}
          {decisionCriteria && decisionCriteria.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Decision criteria
              </div>
              <div className="space-y-1">
                {decisionCriteria.map((c, i) => (
                  <div
                    key={i}
                    className="text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5"
                  >
                    <span className="text-emerald-500 mt-px shrink-0">&#x2713;</span>
                    <span>
                      {c.criterion}
                      {c.measurable && (
                        <span className="text-neutral-400 dark:text-neutral-500 ml-1">
                          ({c.measurable})
                        </span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </ActionCardHeader>

        <ActionCardFooter>
          <Button
            size="sm"
            onClick={() => onCreateCase(analysis, suggestedTitle)}
            disabled={isCreating}
          >
            {isCreating ? (
              <span className="inline-flex items-center gap-2">
                <span className="w-3 h-3 border-2 border-white/60 border-t-white rounded-full animate-spin" />
                Creating...
              </span>
            ) : (
              'Create This Case'
            )}
          </Button>
          <Button variant="ghost" size="sm" onClick={onAdjust} disabled={isCreating}>
            Adjust
          </Button>
          <Button variant="ghost" size="sm" onClick={onDismiss} disabled={isCreating}>
            Dismiss
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}
