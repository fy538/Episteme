/**
 * ToolConfirmationCard — Inline card for tool actions requiring user approval
 *
 * Shown when the AI wants to execute an impactful tool action (e.g. record
 * decision, resolve inquiry, create case). Shows tool name, reason, and
 * params summary with Approve/Dismiss actions.
 *
 * On approve: calls chatAPI.confirmToolAction() with the confirmation ID.
 * On dismiss: calls the same endpoint with approved=false.
 *
 * Follows ActionCard pattern from PlanDiffProposalCard.tsx.
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import {
  ActionCard,
  ActionCardHeader,
  ActionCardTitle,
  ActionCardDescription,
  ActionCardFooter,
} from '@/components/ui/action-card';
import type { InlineActionCard, ToolConfirmationData } from '@/lib/types/chat';

interface ToolConfirmationCardProps {
  card: InlineActionCard;
  onConfirm: (confirmationId: string, approved: boolean) => Promise<void>;
  onDismiss: () => void;
}

/**
 * Format tool params into a human-readable summary.
 */
function formatParams(params: Record<string, unknown>): string[] {
  const summary: string[] = [];
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue;
    // Format the key nicely
    const label = key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());

    if (Array.isArray(value)) {
      summary.push(`${label}: ${value.length} item${value.length !== 1 ? 's' : ''}`);
    } else if (typeof value === 'object') {
      summary.push(`${label}: (complex)`);
    } else {
      const strVal = String(value);
      summary.push(`${label}: ${strVal.length > 80 ? strVal.slice(0, 80) + '...' : strVal}`);
    }
  }
  return summary;
}

export function ToolConfirmationCard({
  card,
  onConfirm,
  onDismiss,
}: ToolConfirmationCardProps) {
  const data = card.data as unknown as ToolConfirmationData;
  const { displayName, params, reason, confirmationId } = data;
  const [isConfirming, setIsConfirming] = useState(false);
  const [isDismissing, setIsDismissing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const paramsSummary = formatParams(params);

  async function handleApprove() {
    if (isConfirming || isDismissing) return;
    setError(null);
    setIsConfirming(true);
    try {
      await onConfirm(confirmationId, true);
      onDismiss(); // Auto-dismiss on success
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute action. Please try again.');
      setIsConfirming(false);
    }
  }

  async function handleDismissAction() {
    if (isConfirming || isDismissing) return;
    setIsDismissing(true);
    try {
      await onConfirm(confirmationId, false);
      onDismiss();
    } catch {
      // Dismiss failures are non-critical, just close the card
      onDismiss();
    }
  }

  const isBusy = isConfirming || isDismissing;

  return (
    <div className="my-3">
      <ActionCard variant="warning">
        <ActionCardHeader>
          <div className="flex items-center gap-2">
            <ActionCardTitle>{displayName}</ActionCardTitle>
            <span className="text-xs bg-warning-100 dark:bg-warning-900/30 text-warning-600 dark:text-warning-400 px-1.5 py-0.5 rounded-full">
              Requires approval
            </span>
          </div>

          {/* Reason */}
          <ActionCardDescription className="mt-2">
            {reason}
          </ActionCardDescription>

          {/* Parameters summary */}
          {paramsSummary.length > 0 && (
            <div className="mt-3 space-y-1">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Details
              </div>
              {paramsSummary.map((line, i) => (
                <div
                  key={`param-${i}`}
                  className="text-xs text-neutral-700 dark:text-neutral-300 pl-2 border-l-2 border-warning-300 dark:border-warning-700"
                >
                  {line}
                </div>
              ))}
            </div>
          )}

          {/* Error banner */}
          {error && (
            <div className="mt-2 px-3 py-2 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800/50 rounded text-xs text-error-700 dark:text-error-400 flex items-center gap-2">
              <span className="shrink-0">Error:</span>
              <span className="flex-1">{error}</span>
              <button
                type="button"
                aria-label="Dismiss error"
                onClick={() => setError(null)}
                className="text-error-500 hover:text-error-700 dark:hover:text-error-300 shrink-0"
              >
                &#x2715;
              </button>
            </div>
          )}
        </ActionCardHeader>

        <ActionCardFooter>
          <Button
            size="sm"
            onClick={handleApprove}
            disabled={isBusy}
          >
            {isConfirming ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="xs" />
                Executing...
              </span>
            ) : (
              'Approve'
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDismissAction}
            disabled={isBusy}
          >
            {isDismissing ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="xs" />
                Dismissing...
              </span>
            ) : (
              'Dismiss'
            )}
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}
