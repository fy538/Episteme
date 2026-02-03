/**
 * Attention Needed Card
 * Alerts user to issues that need action
 */

import { IntelligenceCard } from './IntelligenceCard';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function AttentionNeededCard() {
  return (
    <IntelligenceCard
      icon={
        <svg className="w-5 h-5 text-warning-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      }
      title="Weak Evidence Detected"
      description="Your standing argument's redressability element needs strengthening. Currently only 1 case supports this - precedent requires 2-3 minimum."
      variant="warning"
      actions={
        <>
          <Button size="sm" variant="default">
            Research Now
          </Button>
          <Button size="sm" variant="outline">
            Create Inquiry
          </Button>
          <Button size="sm" variant="outline">
            Discuss
          </Button>
        </>
      }
    >
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Badge variant="warning" className="text-xs">
            High Priority
          </Badge>
          <span className="text-xs text-neutral-600 dark:text-neutral-400">
            Detected 2 hours ago
          </span>
        </div>
        <div className="text-sm text-neutral-700 dark:text-neutral-300">
          <p className="font-medium mb-1">Impact:</p>
          <p className="text-xs">
            Without additional support, this element may be challenged and could undermine your entire standing argument.
          </p>
        </div>
      </div>
    </IntelligenceCard>
  );
}
