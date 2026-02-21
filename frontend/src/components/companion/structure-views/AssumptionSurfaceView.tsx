/**
 * AssumptionSurfaceView — Renders assumptions extracted from the conversation.
 *
 * Each assumption shows its text with a risk-colored left border
 * and a subtle source tag (stated / inferred / implicit).
 * This is an annotation view — it extracts what was said, not new ideas.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';
import type { AssumptionRisk, AssumptionSurfaceContent, StructureViewProps } from './types';

const RISK_BORDER: Record<AssumptionRisk, string> = {
  high: 'border-amber-500/60',
  medium: 'border-amber-500/30',
  low: 'border-zinc-600/30',
};

const RISK_ICON: Record<AssumptionRisk, string> = {
  high: '⚠',
  medium: '△',
  low: '·',
};

export const AssumptionSurfaceView = memo(function AssumptionSurfaceView({
  content,
}: StructureViewProps<AssumptionSurfaceContent>) {
  const assumptions = content.assumptions ?? [];

  return (
    <div className="space-y-1.5">
      {content.context && (
        <p className={cn('text-xs', theme.thinking.textMuted)}>{content.context}</p>
      )}
      {assumptions.map((a, i) => {
        const risk = a.risk ?? 'medium';
        return (
          <div
            key={i}
            className={cn(
              'pl-2 border-l-2 py-0.5',
              RISK_BORDER[risk],
            )}
          >
            <div className="flex items-start gap-1.5">
              <span className="text-[10px] shrink-0 mt-px" aria-hidden="true">
                {RISK_ICON[risk]}
              </span>
              <span className={cn('text-xs', theme.thinking.text)}>{a.text}</span>
            </div>
            {a.source && (
              <span className={cn('text-[10px] pl-4', theme.thinking.textMuted)}>
                {a.source}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
});
