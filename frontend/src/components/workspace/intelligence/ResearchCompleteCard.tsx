/**
 * Research Complete Card
 * Shows when background research finishes
 */

import { IntelligenceCard } from './IntelligenceCard';
import { Button } from '@/components/ui/button';

export function ResearchCompleteCard() {
  return (
    <IntelligenceCard
      icon={
        <svg className="w-5 h-5 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      }
      title="Research Complete: Standing Doctrine"
      description="I finished researching your standing question. Found 12 relevant cases, 3 directly on point. The circuit is split on this issue, with 2nd Circuit favoring your position."
      variant="success"
      actions={
        <>
          <Button size="sm" variant="default">
            View Findings
          </Button>
          <Button size="sm" variant="outline">
            Add to Brief
          </Button>
          <Button size="sm" variant="outline">
            Start Discussion
          </Button>
        </>
      }
    >
      <div className="text-sm space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-success-600">✓</span>
          <span>12 cases analyzed</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-success-600">✓</span>
          <span>3 directly on point</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-warning-600">⚠</span>
          <span>Circuit split detected</span>
        </div>
      </div>
    </IntelligenceCard>
  );
}
