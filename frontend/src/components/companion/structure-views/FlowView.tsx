/**
 * FlowView — Renders a numbered flow/process with status indicators.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';
import type { FlowContent, StructureViewProps } from './types';

export const FlowView = memo(function FlowView({
  content,
}: StructureViewProps<FlowContent>) {
  const steps = content.steps ?? [];

  return (
    <div className="space-y-1">
      {content.title && (
        <p className={cn('text-xs font-medium', theme.thinking.text)}>{content.title}</p>
      )}
      {steps.map((step, i) => (
        <div key={i} className="flex items-start gap-1.5">
          <span className={cn(
            'text-xs mt-0.5 tabular-nums',
            step.status === 'understood' ? 'text-emerald-400' :
            step.status === 'blocked' ? 'text-red-400' : 'text-zinc-500',
          )}>
            {i + 1}.
          </span>
          <div>
            <span className={cn('text-xs font-medium', theme.thinking.text)}>{step.label}</span>
            {step.detail && (
              <p className={cn('text-[10px]', theme.thinking.textMuted)}>{step.detail}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
});
