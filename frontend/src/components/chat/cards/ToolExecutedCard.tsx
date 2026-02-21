/**
 * ToolExecutedCard — Inline card for auto-executed tool results
 *
 * Shown when the AI auto-executes a safe tool action (e.g. create inquiry,
 * update stage). Compact card with success/error state.
 *
 * Follows ActionCard pattern from PlanDiffProposalCard.tsx.
 */

'use client';

import { useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import {
  ActionCard,
  ActionCardHeader,
  ActionCardTitle,
  ActionCardDescription,
  ActionCardFooter,
} from '@/components/ui/action-card';
import type { InlineActionCard, ToolExecutedData } from '@/lib/types/chat';

interface ToolExecutedCardProps {
  card: InlineActionCard;
  onDismiss: () => void;
}

/**
 * Format tool output into a human-readable summary.
 */
function formatOutput(tool: string, output: Record<string, unknown>): string {
  // Try common output fields
  if (output.title) return String(output.title);
  if (output.decision_text) return String(output.decision_text);
  if (output.content) return String(output.content);
  if (output.note) return String(output.note);
  if (output.new_stage) return `Stage: ${output.new_stage}`;
  if (output.new_status) return `Status: ${output.new_status}`;
  if (output.id) return `ID: ${String(output.id).slice(0, 8)}...`;
  return '';
}

export function ToolExecutedCard({
  card,
  onDismiss,
}: ToolExecutedCardProps) {
  const data = card.data as unknown as ToolExecutedData;
  const { displayName, success, output, error } = data;

  // Auto-dismiss after 8 seconds on success
  // M5: mounted ref prevents calling onDismiss after unmount (stale closure guard)
  const mountedRef = useRef(true);
  const dismissTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => {
    if (success && !card.dismissed) {
      dismissTimerRef.current = setTimeout(() => {
        if (mountedRef.current) {
          onDismiss();
        }
      }, 8000);
    }
    return () => {
      if (dismissTimerRef.current) {
        clearTimeout(dismissTimerRef.current);
      }
    };
  }, [success, card.dismissed, onDismiss]);

  const outputSummary = success ? formatOutput(data.tool, output) : '';
  const variant = success ? 'success' : 'error';

  return (
    <div className="my-2">
      <ActionCard variant={variant}>
        <ActionCardHeader>
          <div className="flex items-center gap-2">
            <span className="text-sm">
              {success ? (
                <span className="text-success-500">&#x2713;</span>
              ) : (
                <span className="text-error-500">&#x2717;</span>
              )}
            </span>
            <ActionCardTitle>
              {displayName}
            </ActionCardTitle>
          </div>

          {success && outputSummary && (
            <ActionCardDescription className="mt-1">
              {outputSummary}
            </ActionCardDescription>
          )}

          {!success && error && (
            <ActionCardDescription className="mt-1 text-error-600 dark:text-error-400">
              {error}
            </ActionCardDescription>
          )}
        </ActionCardHeader>

        <ActionCardFooter>
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            Dismiss
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}
