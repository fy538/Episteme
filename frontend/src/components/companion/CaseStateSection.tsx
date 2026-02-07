/**
 * CaseStateSection - Summary of case state when in case mode
 *
 * Shows:
 * - Open/resolved inquiries count
 * - Validated/unvalidated assumptions count
 * - Evidence gaps
 * - Link to view case
 */

'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { theme, isTerminalTheme } from '@/lib/theme/companionTheme';
import type { CaseState } from '@/lib/types/companion';

interface CaseStateSectionProps {
  caseState: CaseState;
  onViewCase?: () => void;
  onViewInquiries?: () => void;
}

export function CaseStateSection({
  caseState,
  onViewCase,
  onViewInquiries,
}: CaseStateSectionProps) {
  const [collapsed, setCollapsed] = useState(false);

  const { inquiries, assumptions, evidenceGaps, caseName } = caseState;
  const totalInquiries = inquiries.open + inquiries.resolved;
  const totalAssumptions = assumptions.validated + assumptions.unvalidated;

  return (
    <section className={cn('border-b', theme.case.border)}>
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        aria-expanded={!collapsed}
        className={cn(
          'w-full px-3 py-2 flex items-center justify-between transition-colors',
          theme.case.bgHover,
          isTerminalTheme && 'font-mono'
        )}
      >
        <div className="flex items-center gap-2">
          <span className={cn('text-xs', theme.case.text)} aria-hidden="true">{'>'}</span>
          <span className={cn('text-xs tracking-wider font-medium uppercase', theme.case.text)}>
            CASE
          </span>
          <span className={cn('text-xs truncate max-w-48', theme.case.icon)}>
            {caseName}
          </span>
        </div>
        <span className={cn('text-xs', theme.case.textMuted)} aria-hidden="true">
          {collapsed ? '[+]' : '[-]'}
        </span>
      </button>

      {/* Content */}
      {!collapsed && (
        <div className={cn('px-3 pb-3', isTerminalTheme && 'font-mono')}>
          <div className={cn(
            'border p-2 text-xs space-y-2',
            theme.case.border,
            theme.case.bg
          )}>
            {/* Inquiries */}
            <div className="flex items-center justify-between">
              <span className={theme.case.textMuted}>Inquiries:</span>
              <div className="flex items-center gap-2">
                {inquiries.open > 0 && (
                  <span className={theme.metrics.neutral}>
                    {inquiries.open} open
                  </span>
                )}
                {inquiries.resolved > 0 && (
                  <span className={theme.metrics.positive}>
                    {inquiries.resolved} resolved
                  </span>
                )}
                {totalInquiries === 0 && (
                  <span className={theme.case.textSubtle}>none</span>
                )}
              </div>
            </div>

            {/* Assumptions */}
            <div className="flex items-center justify-between">
              <span className={theme.case.textMuted}>Assumptions:</span>
              <div className="flex items-center gap-2">
                {assumptions.unvalidated > 0 && (
                  <span className={theme.metrics.negative}>
                    {assumptions.unvalidated} unvalidated
                  </span>
                )}
                {assumptions.validated > 0 && (
                  <span className={theme.metrics.positive}>
                    {assumptions.validated} validated
                  </span>
                )}
                {totalAssumptions === 0 && (
                  <span className={theme.case.textSubtle}>none</span>
                )}
              </div>
            </div>

            {/* Evidence Gaps */}
            {evidenceGaps > 0 && (
              <div className="flex items-center justify-between">
                <span className={theme.case.textMuted}>Evidence gaps:</span>
                <span className={theme.metrics.negative}>
                  {evidenceGaps}
                </span>
              </div>
            )}

            {/* Actions */}
            <div className={cn(
              'flex items-center gap-2 pt-1 border-t mt-2',
              theme.case.border
            )}>
              {onViewCase && (
                <button
                  onClick={onViewCase}
                  className={cn(
                    'transition-opacity hover:opacity-80',
                    theme.case.text
                  )}
                >
                  [View case]
                </button>
              )}
              {onViewInquiries && inquiries.open > 0 && (
                <button
                  onClick={onViewInquiries}
                  className={cn(
                    'transition-opacity hover:opacity-80',
                    theme.case.text
                  )}
                >
                  [Inquiries]
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
