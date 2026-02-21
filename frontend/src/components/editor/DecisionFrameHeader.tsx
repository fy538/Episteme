/**
 * DecisionFrameHeader — Collapsible decision frame above the brief editor.
 *
 * Collapsed: one-line summary of the decision question + stakes badge.
 * Expanded: full DecisionFrameEditor for editing the frame fields.
 */

'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DecisionFrameEditor,
  DecisionFrameSummary,
} from '@/components/cases';
import { casesAPI } from '@/lib/api/cases';
import type { Case } from '@/lib/types/case';

interface DecisionFrameHeaderProps {
  caseData: Case;
  onRefresh: () => void;
  className?: string;
}

export function DecisionFrameHeader({
  caseData,
  onRefresh,
  className,
}: DecisionFrameHeaderProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasDecisionQuestion = !!caseData.decision_question;

  return (
    <div
      className={cn(
        'border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900/30',
        className,
      )}
    >
      {/* Collapsed view — always visible */}
      <Button
        variant="ghost"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-2 h-auto flex items-center justify-between text-left rounded-none hover:bg-neutral-100/50 dark:hover:bg-neutral-800/30"
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          {/* Chevron */}
          <svg
            className={cn(
              'w-3.5 h-3.5 text-neutral-400 transition-transform duration-150 flex-shrink-0',
              isExpanded && 'rotate-90',
            )}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>

          {/* Label */}
          <span className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 flex-shrink-0">
            Decision Frame
          </span>

          {/* Summary */}
          {hasDecisionQuestion && !isExpanded && (
            <span className="text-xs text-neutral-600 dark:text-neutral-400 truncate">
              {caseData.decision_question}
            </span>
          )}
          {!hasDecisionQuestion && !isExpanded && (
            <span className="text-xs text-neutral-400 dark:text-neutral-500 italic">
              No decision question set
            </span>
          )}
        </div>

        {/* Stakes badge */}
        {caseData.stakes && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 flex-shrink-0 ml-2">
            {caseData.stakes} stakes
          </span>
        )}
      </Button>

      {/* Expanded view — shows full editor */}
      {isExpanded && (
        <div className="px-4 pb-3 pt-1 border-t border-neutral-100 dark:border-neutral-800/50">
          {hasDecisionQuestion && (
            <div className="mb-3">
              <DecisionFrameSummary caseData={caseData} />
            </div>
          )}
          <DecisionFrameEditor
            caseData={caseData}
            onSave={async (updates) => {
              await casesAPI.updateDecisionFrame(caseData.id, updates);
              onRefresh();
            }}
          />
        </div>
      )}
    </div>
  );
}
