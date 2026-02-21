/**
 * PositionUpdateProposalCard — Inline card for accepting/rejecting position updates
 *
 * Shown when fact promotion detects that conversation has produced a position
 * shift. Displays the current position, the proposed update from conversation
 * facts, and Accept/Dismiss actions.
 *
 * Follows PlanDiffProposalCard.tsx pattern (ActionCard + ActionCardHeader + ActionCardFooter).
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
import type { InlineActionCard, PositionUpdateProposalData } from '@/lib/types/chat';

interface PositionUpdateProposalCardProps {
  card: InlineActionCard;
  onAccept: (caseId: string, newPosition: string, reason: string, messageId?: string) => Promise<void> | void;
  onDismiss: (caseId: string, messageId?: string) => Promise<void> | void;
}

export function PositionUpdateProposalCard({
  card,
  onAccept,
  onDismiss,
}: PositionUpdateProposalCardProps) {
  const data = card.data as unknown as PositionUpdateProposalData;
  const { proposals, caseId, currentPosition, messageId } = data;
  const [error, setError] = useState<string | null>(null);
  const [isAccepting, setIsAccepting] = useState(false);
  const [isDismissing, setIsDismissing] = useState(false);

  // Guard: nothing to show if proposals are empty
  if (!proposals || proposals.length === 0) return null;

  // Build the proposed new position from facts
  const proposedPosition = proposals.map(p => p.fact).join('. ');

  async function handleAccept() {
    if (isAccepting || isDismissing) return;
    setError(null);
    setIsAccepting(true);
    try {
      const reasons = proposals.map(p => p.reason).filter(Boolean).join('; ');
      await onAccept(caseId, proposedPosition, reasons, messageId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update position.');
      setIsAccepting(false);
    }
  }

  async function handleDismiss() {
    if (isAccepting || isDismissing) return;
    setIsDismissing(true);
    try {
      await onDismiss(caseId, messageId);
    } catch {
      // Dismiss failures are non-critical — just close the card
      setIsDismissing(false);
    }
  }

  return (
    <div className="my-3">
      <ActionCard variant="accent">
        <ActionCardHeader>
          <ActionCardTitle>Position Update Suggested</ActionCardTitle>

          {currentPosition && (
            <div className="mt-2">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1">
                Current position
              </div>
              <p className="text-xs text-neutral-600 dark:text-neutral-400 italic pl-2 border-l-2 border-neutral-300 dark:border-neutral-600 line-clamp-4">
                {currentPosition}
              </p>
            </div>
          )}

          <div className="mt-3">
            <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
              Suggested update
            </div>
            <div className="space-y-1.5">
              {proposals.map((p, i) => (
                <div
                  key={`pos-${i}`}
                  className="text-sm text-neutral-700 dark:text-neutral-300 pl-2 border-l-2 border-accent-400"
                >
                  <span>{p.fact}</span>
                  {p.reason && (
                    <span className="text-xs text-neutral-400 dark:text-neutral-500 ml-2">
                      — {p.reason}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

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
        </ActionCardHeader>

        <ActionCardFooter>
          <Button
            size="sm"
            onClick={handleAccept}
            disabled={isAccepting || isDismissing}
            aria-label="Accept position update"
          >
            {isAccepting ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="xs" />
                Updating...
              </span>
            ) : (
              'Accept Update'
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDismiss}
            disabled={isAccepting || isDismissing}
            aria-label="Dismiss position update"
          >
            Dismiss
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}
