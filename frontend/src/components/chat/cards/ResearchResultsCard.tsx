/**
 * ResearchResultsCard - Shows results from completed background research
 *
 * Appears when research completes, allowing user to view or add to case.
 */

'use client';

import { Button } from '@/components/ui/button';
import {
  ActionCard,
  ActionCardHeader,
  ActionCardTitle,
  ActionCardDescription,
  ActionCardFooter,
} from '@/components/ui/action-card';
import type { InlineActionCard, ResearchResultsData } from '@/lib/types/chat';

interface ResearchResultsCardProps {
  card: InlineActionCard;
  onViewResults: (researchId: string) => void;
  onAddToCase: (researchId: string) => void;
  onDismiss: () => void;
}

export function ResearchResultsCard({
  card,
  onViewResults,
  onAddToCase,
  onDismiss,
}: ResearchResultsCardProps) {
  const data = card.data as unknown as ResearchResultsData;
  const { researchId, title, summary, sourceCount } = data;

  return (
    <div className="my-3 mx-4">
      <ActionCard variant="info">
        <ActionCardHeader icon="?">
          <ActionCardTitle>Research complete</ActionCardTitle>
          <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mt-1">
            {title}
          </p>

          {/* Summary */}
          <ActionCardDescription className="mt-2 line-clamp-3">
            {summary}
          </ActionCardDescription>

          {/* Source count */}
          {sourceCount > 0 && (
            <div className="mt-2 text-xs text-info-600 dark:text-info-400">
              {sourceCount} source{sourceCount !== 1 ? 's' : ''} found
            </div>
          )}
        </ActionCardHeader>

        <ActionCardFooter className="ml-7">
          <Button size="sm" onClick={() => onViewResults(researchId)}>
            View Results
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onAddToCase(researchId)}
          >
            Add to Case
          </Button>
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            Dismiss
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}
