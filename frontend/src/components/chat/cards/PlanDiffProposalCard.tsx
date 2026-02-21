/**
 * PlanDiffProposalCard — Inline card for accepting/rejecting plan changes
 *
 * Shown when the AI proposes changes to the investigation plan during chat.
 * Displays a summary of changes (new assumptions, stage transitions, etc.)
 * with Accept/Dismiss actions.
 *
 * Follows CasePreviewCard.tsx pattern (ActionCard + ActionCardHeader + ActionCardFooter).
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import {
  ActionCard,
  ActionCardHeader,
  ActionCardTitle,
  ActionCardFooter,
} from '@/components/ui/action-card';
import { cn } from '@/lib/utils';
import { ArrowRightIcon } from '@/components/ui/icons';
import type { InlineActionCard, PlanDiffProposalData } from '@/lib/types/chat';

interface PlanDiffProposalCardProps {
  card: InlineActionCard;
  onAccept: (proposedContent: Record<string, unknown>, diffSummary: string, diffData: Record<string, unknown>) => Promise<void> | void;
  onDismiss: () => void;
}

export function PlanDiffProposalCard({
  card,
  onAccept,
  onDismiss,
}: PlanDiffProposalCardProps) {
  const data = card.data as unknown as PlanDiffProposalData;
  const { diffSummary, proposedContent, diffData } = data;
  const [error, setError] = useState<string | null>(null);
  const [isAccepting, setIsAccepting] = useState(false);

  const hasStageChange = !!diffData.stage_change;
  const addedAssumptions = diffData.added_assumptions ?? [];
  const updatedAssumptions = diffData.updated_assumptions ?? [];
  const addedCriteria = diffData.added_criteria ?? [];
  const updatedCriteria = diffData.updated_criteria ?? [];

  // Change count for quick summary
  const changeCount =
    addedAssumptions.length +
    updatedAssumptions.length +
    addedCriteria.length +
    updatedCriteria.length +
    (hasStageChange ? 1 : 0);

  async function handleAccept() {
    if (isAccepting) return; // Prevent double-clicks
    setError(null);
    setIsAccepting(true);
    try {
      await onAccept(proposedContent, diffSummary, diffData as unknown as Record<string, unknown>);
      onDismiss(); // Auto-dismiss on success
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply changes. Please try again.');
      setIsAccepting(false);
    }
  }

  return (
    <div className="my-3">
      <ActionCard variant="accent">
        <ActionCardHeader>
          <div className="flex items-center gap-2">
            <ActionCardTitle>Plan Update Proposed</ActionCardTitle>
            <span className="text-xs bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400 px-1.5 py-0.5 rounded-full">
              {changeCount} {changeCount === 1 ? 'change' : 'changes'}
            </span>
          </div>

          {/* Summary */}
          <p className="mt-2 text-sm text-neutral-700 dark:text-neutral-300">
            {diffSummary}
          </p>

          {/* Error banner */}
          {error && (
            <div className="mt-2 px-3 py-2 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800/50 rounded text-xs text-error-700 dark:text-error-400 flex items-center gap-2">
              <span className="shrink-0">Failed to apply:</span>
              <span className="flex-1">{error}</span>
              <button
                onClick={() => setError(null)}
                className="text-error-500 hover:text-error-700 dark:hover:text-error-300 shrink-0"
              >
                ✕
              </button>
            </div>
          )}

          {/* Stage change */}
          {hasStageChange && diffData.stage_change && (
            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Stage
              </span>
              <div className="flex items-center gap-1.5 text-xs">
                <StageBadge stage={diffData.stage_change.from} />
                <ArrowRightIcon className="w-3 h-3 text-neutral-400" />
                <StageBadge stage={diffData.stage_change.to} active />
              </div>
              {diffData.stage_change.rationale && (
                <span className="text-xs text-neutral-500 dark:text-neutral-400 italic ml-1">
                  — {diffData.stage_change.rationale}
                </span>
              )}
            </div>
          )}

          {/* Added assumptions */}
          {addedAssumptions.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                New assumptions
              </div>
              <div className="space-y-1">
                {addedAssumptions.map((a, i) => (
                  <div
                    key={`added-a-${a.text.slice(0, 20)}-${i}`}
                    className="text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5 pl-2 border-l-2 border-success-400"
                  >
                    <span className="flex-1">{a.text}</span>
                    {a.risk_level && (
                      <span className={cn(
                        'text-xs px-1.5 py-0.5 rounded-full uppercase shrink-0',
                        a.risk_level === 'high' && 'bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400',
                        a.risk_level === 'medium' && 'bg-warning-100 dark:bg-warning-900/30 text-warning-600 dark:text-warning-400',
                        a.risk_level === 'low' && 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400',
                      )}>
                        {a.risk_level}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Updated assumptions */}
          {updatedAssumptions.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Updated assumptions
              </div>
              <div className="space-y-1">
                {updatedAssumptions.map((a) => (
                  <div
                    key={`updated-a-${a.id}`}
                    className="text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5 pl-2 border-l-2 border-warning-400"
                  >
                    <span className="flex-1">
                      {a.evidence_summary || `Assumption ${a.id.slice(0, 8)}`}
                      {' → '}
                      <span className={cn(
                        'font-medium',
                        a.status === 'confirmed' && 'text-success-600 dark:text-success-400',
                        a.status === 'challenged' && 'text-warning-600 dark:text-warning-400',
                        a.status === 'refuted' && 'text-error-600 dark:text-error-400',
                      )}>
                        {a.status}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Added criteria */}
          {addedCriteria.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                New decision criteria
              </div>
              <div className="space-y-1">
                {addedCriteria.map((c, i) => (
                  <div
                    key={`added-c-${c.text.slice(0, 20)}-${i}`}
                    className="text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5 pl-2 border-l-2 border-success-400"
                  >
                    <span className="text-success-500 shrink-0">&#x2713;</span>
                    <span>{c.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Updated criteria */}
          {updatedCriteria.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Updated criteria
              </div>
              <div className="space-y-1">
                {updatedCriteria.map((c) => (
                  <div
                    key={`updated-c-${c.id}`}
                    className="text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5 pl-2 border-l-2 border-warning-400"
                  >
                    <span>{`Criterion ${c.id.slice(0, 8)} → ${c.is_met ? 'met' : 'not met'}`}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </ActionCardHeader>

        <ActionCardFooter>
          <Button
            size="sm"
            onClick={handleAccept}
            disabled={isAccepting}
          >
            {isAccepting ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="xs" />
                Applying...
              </span>
            ) : (
              'Accept Changes'
            )}
          </Button>
          <Button variant="ghost" size="sm" onClick={onDismiss} disabled={isAccepting}>
            Dismiss
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}

// ─── Sub-components ────────────────────────────────

function StageBadge({ stage, active }: { stage: string; active?: boolean }) {
  return (
    <span className={cn(
      'text-xs px-2 py-0.5 rounded-full capitalize',
      active
        ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400 font-medium'
        : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400'
    )}>
      {stage}
    </span>
  );
}

