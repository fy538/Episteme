/**
 * CompanionPanel - Adaptive right sidebar with priority-ranked sections
 *
 * The panel uses a slot system — sections compete for visibility based on
 * recency, content density, mode relevance, and user interaction.
 *
 * Sidebar mode: 3 slots (vertical, each scrollable)
 * Bottom mode: 2 slots (horizontal strip, compact)
 *
 * Slot 1 renders expanded, slots 2+ render as compact previews.
 * Overflow sections shown as "+N more" with expand-on-click.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme, isTerminalTheme } from '@/lib/theme/companionTheme';
import { ThinkingSection } from './ThinkingSection';
import { StatusSection } from './StatusSection';
import { SessionReceiptsSection } from './SessionReceiptsSection';
import { CaseStateSection } from './CaseStateSection';
import { getActionHintIcon, getActionHintLabel } from '@/lib/utils/action-hints';
import type { CompanionSectionId } from '@/lib/utils/companion-ranking';
import type { ChatMode, BackgroundWorkItem, SessionReceipt, CaseState } from '@/lib/types/companion';
import type { ActionHint } from '@/lib/types/chat';
import type { Signal } from '@/lib/types/signal';

// Human-readable labels for signal types
const SIGNAL_TYPE_LABELS: Record<string, string> = {
  DecisionIntent: 'Decision',
  Claim: 'Claim',
  Goal: 'Goal',
  Constraint: 'Constraint',
  Assumption: 'Assumption',
  Question: 'Question',
  EvidenceMention: 'Evidence',
};

function getSignalLabel(signal: Signal): string {
  // Prefer signal_type (backend label) if set, otherwise map the enum type
  if (signal.signal_type) return signal.signal_type;
  return SIGNAL_TYPE_LABELS[signal.type] || signal.type;
}

function getSignalContent(signal: Signal): string {
  return signal.content || signal.text;
}

interface CompanionPanelProps {
  // Core state
  thinking: { content: string; isStreaming: boolean };
  mode: ChatMode;
  position: 'sidebar' | 'bottom' | 'hidden';

  // Section data
  actionHints?: ActionHint[];
  signals?: Signal[];
  status?: { inProgress: BackgroundWorkItem[]; justCompleted: BackgroundWorkItem[] };
  sessionReceipts?: SessionReceipt[];
  caseState?: CaseState;

  // Ranking
  rankedSections: CompanionSectionId[];
  pinnedSection?: CompanionSectionId | null;
  onPinSection?: (id: CompanionSectionId | null) => void;

  // Actions
  onActionHint?: (hint: ActionHint) => void;
  onDismissCompleted?: (id: string) => void;
  onViewCase?: () => void;
  onViewInquiries?: () => void;
  onReceiptClick?: (receipt: SessionReceipt) => void;
  onTogglePosition?: () => void;
  onClose?: () => void;
}

const MODE_DOTS: Record<ChatMode, string> = {
  casual: 'bg-cyan-400',
  case: 'bg-amber-400',
  inquiry_focus: 'bg-purple-400',
};

export function CompanionPanel({
  thinking,
  mode,
  position,
  actionHints = [],
  signals = [],
  status = { inProgress: [], justCompleted: [] },
  sessionReceipts = [],
  caseState,
  rankedSections,
  pinnedSection,
  onPinSection,
  onActionHint,
  onDismissCompleted,
  onViewCase,
  onViewInquiries,
  onReceiptClick,
  onTogglePosition,
  onClose,
}: CompanionPanelProps) {
  if (position === 'hidden') return null;

  const slotCount = position === 'sidebar' ? 3 : 2;
  const visibleSections = rankedSections.slice(0, slotCount);
  const overflowCount = rankedSections.length - visibleSections.length;

  return (
    <div
      role="complementary"
      aria-label="AI Companion"
      className={cn(
        'flex flex-col overflow-hidden',
        position === 'sidebar' ? 'h-full' : 'max-h-48',
        theme.panel.bg,
        isTerminalTheme && 'font-mono'
      )}
    >
      {/* Header */}
      <div
        className={cn(
          'flex items-center justify-between px-3 py-2 border-b shrink-0',
          theme.panel.border,
          theme.panel.headerBg
        )}
      >
        <div className="flex items-center gap-2">
          <span className={cn('w-2 h-2 rounded-full', MODE_DOTS[mode])} aria-hidden="true" />
          <span className={cn('text-xs font-medium tracking-wide uppercase', theme.panel.header)}>
            Companion
          </span>
        </div>
        <div className="flex items-center gap-1">
          {onTogglePosition && (
            <button
              onClick={onTogglePosition}
              className={cn('p-1 rounded transition-colors text-xs', theme.panel.header, 'opacity-60 hover:opacity-100')}
              aria-label={position === 'sidebar' ? 'Move to bottom' : 'Move to sidebar'}
            >
              {position === 'sidebar' ? '⊥' : '⊢'}
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className={cn('p-1 rounded transition-colors text-xs', theme.panel.header, 'opacity-60 hover:opacity-100')}
              aria-label="Hide companion"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* Slots */}
      <div
        className={cn(
          'flex-1 overflow-y-auto min-h-0',
          position === 'bottom' && 'flex flex-row divide-x',
          position === 'bottom' && theme.panel.border
        )}
      >
        {visibleSections.length === 0 && (
          <div className={cn('px-3 py-4 text-xs text-center', theme.thinking.textSubtle)}>
            {mode === 'case' ? (
              caseState
                ? `${caseState.caseName} · ${caseState.inquiries.open} open inquiries, ${caseState.assumptions.unvalidated} untested assumptions`
                : 'Chat about your decision to surface signals'
            ) : mode === 'inquiry_focus'
              ? 'Chat about this inquiry to surface insights'
              : 'Send a message to see your reasoning structure'}
          </div>
        )}

        {visibleSections.map((sectionId, index) => (
          <div
            key={sectionId}
            className={cn(
              'transition-all duration-300 ease-in-out',
              position === 'bottom' && 'flex-1 overflow-y-auto',
              position === 'sidebar' && index === 0 && 'flex-shrink-0',
            )}
          >
            <SectionRenderer
              sectionId={sectionId}
              expanded={index === 0}
              thinking={sectionId === 'thinking' ? thinking : undefined}
              mode={sectionId === 'thinking' ? mode : undefined}
              actionHints={sectionId === 'action_hints' ? actionHints : undefined}
              signals={sectionId === 'signals' ? signals : undefined}
              status={sectionId === 'status' ? status : undefined}
              sessionReceipts={sectionId === 'receipts' ? sessionReceipts : undefined}
              caseState={sectionId === 'case_state' ? caseState : undefined}
              onActionHint={sectionId === 'action_hints' ? onActionHint : undefined}
              onDismissCompleted={sectionId === 'status' ? onDismissCompleted : undefined}
              onViewCase={sectionId === 'case_state' ? onViewCase : undefined}
              onViewInquiries={sectionId === 'case_state' ? onViewInquiries : undefined}
              onReceiptClick={sectionId === 'receipts' ? onReceiptClick : undefined}
            />
          </div>
        ))}
      </div>

      {/* Overflow indicator */}
      {overflowCount > 0 && (
        <div
          className={cn(
            'px-3 py-1.5 border-t text-xs shrink-0',
            theme.panel.border,
            theme.thinking.textMuted
          )}
        >
          <span>+{overflowCount} more section{overflowCount > 1 ? 's' : ''}</span>
        </div>
      )}
    </div>
  );
}

// --- Section Renderer (memoized — only re-renders when its specific data changes) ---

interface SectionRendererProps {
  sectionId: CompanionSectionId;
  expanded: boolean;
  thinking?: { content: string; isStreaming: boolean };
  mode?: ChatMode;
  actionHints?: ActionHint[];
  signals?: Signal[];
  status?: { inProgress: BackgroundWorkItem[]; justCompleted: BackgroundWorkItem[] };
  sessionReceipts?: SessionReceipt[];
  caseState?: CaseState;
  onActionHint?: (hint: ActionHint) => void;
  onDismissCompleted?: (id: string) => void;
  onViewCase?: () => void;
  onViewInquiries?: () => void;
  onReceiptClick?: (receipt: SessionReceipt) => void;
}

const SectionRenderer = memo(function SectionRenderer({
  sectionId,
  expanded,
  thinking,
  mode,
  actionHints,
  signals,
  status,
  sessionReceipts,
  caseState,
  onActionHint,
  onDismissCompleted,
  onViewCase,
  onViewInquiries,
  onReceiptClick,
}: SectionRendererProps) {
  switch (sectionId) {
    case 'thinking':
      return thinking ? (
        <ThinkingSection
          content={thinking.content}
          isStreaming={thinking.isStreaming}
          mode={mode || 'casual'}
          collapsed={!expanded}
        />
      ) : null;

    case 'action_hints':
      return actionHints && actionHints.length > 0 ? (
        <section className={cn('border-b', theme.thinking.border)} role="region" aria-label="Suggested actions">
          <div className={cn(
            'px-3 py-2 flex items-center gap-2',
            isTerminalTheme && 'font-mono'
          )}>
            <span className={cn('text-xs', theme.thinking.text)} aria-hidden="true">{'>'}</span>
            <span className={cn('text-xs tracking-wider font-medium uppercase', theme.thinking.text)}>
              ACTIONS
            </span>
          </div>
          <div className="px-3 pb-3 flex flex-wrap gap-1.5">
            {actionHints.map((hint) => (
              <button
                key={`${hint.type}-${hint.reason}`}
                onClick={() => onActionHint?.(hint)}
                className={cn(
                  'inline-flex items-center gap-1 px-2 py-1 text-xs rounded',
                  'border transition-colors',
                  theme.thinking.border,
                  theme.thinking.bg,
                  theme.thinking.text,
                  'hover:brightness-110'
                )}
                title={hint.reason}
              >
                <span aria-hidden="true">{getActionHintIcon(hint.type)}</span>
                <span>{getActionHintLabel(hint.type, hint.data)}</span>
              </button>
            ))}
          </div>
        </section>
      ) : null;

    case 'signals':
      return signals && signals.length > 0 ? (
        <section className={cn('border-b', theme.thinking.border)} role="region" aria-label={`${signals.length} signals extracted`}>
          <div className={cn(
            'px-3 py-2 flex items-center gap-2',
            isTerminalTheme && 'font-mono'
          )}>
            <span className={cn('text-xs', theme.thinking.text)} aria-hidden="true">{'>'}</span>
            <span className={cn('text-xs tracking-wider font-medium uppercase', theme.thinking.text)}>
              SIGNALS
            </span>
            <span className={cn('text-xs', theme.thinking.textMuted)}>
              ({signals.length})
            </span>
          </div>
          <div className={cn(
            'px-3 pb-3 space-y-1.5',
            !expanded && 'max-h-20 overflow-hidden'
          )}>
            {signals.slice(0, expanded ? undefined : 3).map(signal => (
              <div
                key={signal.id}
                className={cn(
                  'text-xs p-1.5 border',
                  theme.thinking.border,
                  theme.thinking.bg,
                  isTerminalTheme && 'font-mono'
                )}
              >
                <span className={cn('font-medium', theme.thinking.text)}>
                  {getSignalLabel(signal)}:
                </span>
                <span className={cn('ml-1', theme.thinking.textMuted)}>
                  {getSignalContent(signal)}
                </span>
              </div>
            ))}
            {!expanded && signals.length > 3 && (
              <div className={cn('text-xs', theme.thinking.textSubtle)}>
                +{signals.length - 3} more
              </div>
            )}
          </div>
        </section>
      ) : null;

    case 'status':
      return status ? (
        <StatusSection
          inProgress={status.inProgress}
          justCompleted={status.justCompleted}
          onDismissCompleted={onDismissCompleted}
        />
      ) : null;

    case 'receipts':
      return sessionReceipts ? (
        <SessionReceiptsSection receipts={sessionReceipts} onReceiptClick={onReceiptClick} />
      ) : null;

    case 'case_state':
      return caseState ? (
        <CaseStateSection caseState={caseState} onViewCase={onViewCase} onViewInquiries={onViewInquiries} />
      ) : null;

    default:
      return null;
  }
});
