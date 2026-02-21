/**
 * OrientationDiffProposalCard — Inline card for accepting/rejecting orientation changes
 *
 * Shown when the AI proposes changes to the project orientation during chat.
 * Displays a summary of changes (lead text, findings, lens, angles)
 * with Accept/Dismiss actions.
 *
 * Follows PlanDiffProposalCard.tsx pattern.
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
import type { InlineActionCard, OrientationDiffProposalData } from '@/lib/types/chat';

interface OrientationDiffProposalCardProps {
  card: InlineActionCard;
  onAccept: (
    orientationId: string,
    proposedState: Record<string, unknown>,
    diffSummary: string,
    diffData: Record<string, unknown>,
  ) => Promise<void> | void;
  onDismiss: () => void;
}

export function OrientationDiffProposalCard({
  card,
  onAccept,
  onDismiss,
}: OrientationDiffProposalCardProps) {
  const data = card.data as unknown as OrientationDiffProposalData;
  const { orientationId, diffSummary, proposedState, diffData } = data;
  const [error, setError] = useState<string | null>(null);
  const [isAccepting, setIsAccepting] = useState(false);

  const hasLeadChange = !!diffData.update_lead;
  const hasLensChange = !!diffData.suggest_lens_change;
  const addedFindings = diffData.added_findings ?? [];
  const updatedFindings = diffData.updated_findings ?? [];
  const removedFindingIds = diffData.removed_finding_ids ?? [];
  const addedAngles = diffData.added_angles ?? [];
  const removedAngleIds = diffData.removed_angle_ids ?? [];

  const changeCount =
    (hasLeadChange ? 1 : 0) +
    (hasLensChange ? 1 : 0) +
    addedFindings.length +
    updatedFindings.length +
    removedFindingIds.length +
    addedAngles.length +
    removedAngleIds.length;

  async function handleAccept() {
    if (isAccepting) return;
    setError(null);
    setIsAccepting(true);
    try {
      await onAccept(
        orientationId,
        proposedState as unknown as Record<string, unknown>,
        diffSummary,
        diffData as unknown as Record<string, unknown>,
      );
      onDismiss();
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
            <ActionCardTitle>Orientation Update Proposed</ActionCardTitle>
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

          {/* Lead text change */}
          {hasLeadChange && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Updated lead
              </div>
              <div className="text-xs text-neutral-700 dark:text-neutral-300 pl-2 border-l-2 border-warning-400 italic">
                {diffData.update_lead}
              </div>
            </div>
          )}

          {/* Lens change */}
          {hasLensChange && (
            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Lens
              </span>
              <LensBadge lens={diffData.suggest_lens_change!} active />
            </div>
          )}

          {/* Added findings */}
          {addedFindings.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                New findings
              </div>
              <div className="space-y-1">
                {addedFindings.map((f, i) => (
                  <div
                    key={`added-f-${i}`}
                    className="text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5 pl-2 border-l-2 border-success-400"
                  >
                    <TypeBadge type={f.type} />
                    <span className="flex-1">{f.title}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Updated findings */}
          {updatedFindings.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Updated findings
              </div>
              <div className="space-y-1">
                {updatedFindings.map((f) => (
                  <div
                    key={`updated-f-${f.id}`}
                    className="text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5 pl-2 border-l-2 border-warning-400"
                  >
                    <span className="flex-1">
                      {f.title || `Finding ${f.id.slice(0, 8)}`}
                      {f.status && (
                        <span className={cn(
                          'ml-1 font-medium',
                          f.status === 'resolved' && 'text-success-600 dark:text-success-400',
                          f.status === 'dismissed' && 'text-neutral-400',
                        )}>
                          → {f.status}
                        </span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Removed findings */}
          {removedFindingIds.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Dismissed findings
              </div>
              <div className="space-y-1">
                {removedFindingIds.map((id) => (
                  <div
                    key={`removed-f-${id}`}
                    className="text-xs text-neutral-400 dark:text-neutral-500 pl-2 border-l-2 border-error-400 line-through"
                  >
                    Finding {id.slice(0, 8)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Added angles */}
          {addedAngles.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                New exploration angles
              </div>
              <div className="space-y-1">
                {addedAngles.map((a, i) => (
                  <div
                    key={`added-a-${i}`}
                    className="text-xs text-neutral-700 dark:text-neutral-300 pl-2 border-l-2 border-success-400"
                  >
                    {a.title}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Removed angles */}
          {removedAngleIds.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Removed angles
              </div>
              <div className="space-y-1">
                {removedAngleIds.map((id) => (
                  <div
                    key={`removed-a-${id}`}
                    className="text-xs text-neutral-400 dark:text-neutral-500 pl-2 border-l-2 border-error-400 line-through"
                  >
                    Angle {id.slice(0, 8)}
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

function TypeBadge({ type }: { type: string }) {
  return (
    <span className={cn(
      'text-xs px-1.5 py-0.5 rounded-full shrink-0 capitalize',
      type === 'tension' && 'bg-warning-100 dark:bg-warning-900/30 text-warning-600 dark:text-warning-400',
      type === 'gap' && 'bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400',
      type === 'consensus' && 'bg-success-100 dark:bg-success-900/30 text-success-600 dark:text-success-400',
      type === 'pattern' && 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400',
      type === 'weak_evidence' && 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400',
    )}>
      {type.replace('_', ' ')}
    </span>
  );
}

function LensBadge({ lens, active }: { lens: string; active?: boolean }) {
  const label = lens.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  return (
    <span className={cn(
      'text-xs px-2 py-0.5 rounded-full',
      active
        ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400 font-medium'
        : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400'
    )}>
      {label}
    </span>
  );
}
