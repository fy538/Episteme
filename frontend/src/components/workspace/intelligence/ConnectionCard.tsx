/**
 * Connection Card
 * Shows discovered connections between cases/projects
 */

import { IntelligenceCard } from './IntelligenceCard';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function ConnectionCard() {
  return (
    <IntelligenceCard
      icon={
        <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
      }
      title="Connection Discovered"
      description="Your preemption argument shares 3 key assumptions with your Patent Case from last month. The reasoning patterns are nearly identical."
      variant="neutral"
      actions={
        <>
          <Button size="sm" variant="default">
            Explore Connections
          </Button>
          <Button size="sm" variant="outline">
            Reuse Analysis
          </Button>
          <Button size="sm" variant="outline">
            Dismiss
          </Button>
        </>
      }
    >
      <div className="space-y-2">
        <div className="text-sm text-neutral-700 dark:text-neutral-300">
          <p className="font-medium mb-1">Shared elements:</p>
          <ul className="text-xs space-y-1">
            <li className="flex items-start gap-2">
              <Badge variant="neutral" className="text-xs shrink-0">Assumption</Badge>
              <span>"Federal law preempts state regulation"</span>
            </li>
            <li className="flex items-start gap-2">
              <Badge variant="neutral" className="text-xs shrink-0">Evidence</Badge>
              <span>Supreme Court precedent on field preemption</span>
            </li>
            <li className="flex items-start gap-2">
              <Badge variant="neutral" className="text-xs shrink-0">Method</Badge>
              <span>Obstacle preemption analysis framework</span>
            </li>
          </ul>
        </div>
        <p className="text-xs text-accent-600 dark:text-accent-400">
          You could save time by adapting your previous analysis.
        </p>
      </div>
    </IntelligenceCard>
  );
}
