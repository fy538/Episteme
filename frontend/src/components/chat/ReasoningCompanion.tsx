/**
 * ReasoningCompanion - Mode-aware sidebar with meta-reflection and session tracking
 *
 * Four sections:
 * 1. Thinking: Mode-aware meta-cognitive reflection
 * 2. Status: Background work progress and just-completed items
 * 3. Session Receipts: Timeline of session accomplishments
 * 4. Case State: Summary when in case mode
 */

'use client';

import { useState } from 'react';
import { KnowledgeGraphView } from '@/components/graph/KnowledgeGraphView';
import { cn } from '@/lib/utils';
import type {
  CompanionState,
  SessionReceipt,
} from '@/lib/types/companion';
import { ThinkingSection } from '@/components/companion/ThinkingSection';
import { StatusSection } from '@/components/companion/StatusSection';
import { SessionReceiptsSection } from '@/components/companion/SessionReceiptsSection';
import { CaseStateSection } from '@/components/companion/CaseStateSection';

interface ReasoningCompanionProps {
  threadId: string | null;
  caseId?: string | null;
  /** Full companion state for mode-aware experience */
  companionState: CompanionState;
  /** Handler for viewing the case */
  onViewCase?: () => void;
  /** Handler for viewing inquiries */
  onViewInquiries?: () => void;
  /** Handler for clicking a receipt */
  onReceiptClick?: (receipt: SessionReceipt) => void;
  /** Handler for dismissing completed work */
  onDismissCompleted?: (id: string) => void;
}

export function ReasoningCompanion({
  threadId,
  caseId,
  companionState,
  onViewCase,
  onViewInquiries,
  onReceiptClick,
  onDismissCompleted,
}: ReasoningCompanionProps) {
  const [showGraph, setShowGraph] = useState(false);

  if (!threadId) {
    return null;
  }

  const mode = companionState.mode;

  return (
    <>
      {/* Knowledge Graph Modal */}
      {showGraph && caseId && (
        <KnowledgeGraphView
          caseId={caseId}
          onClose={() => setShowGraph(false)}
        />
      )}

      <div className="w-80 border-l border-neutral-900/10 dark:border-neutral-100/10 bg-gradient-to-b from-neutral-50/80 to-white/80 dark:from-neutral-950/80 dark:to-neutral-900/80 backdrop-blur-xl flex-shrink-0">
        {/* Header */}
        <div className="border-b border-neutral-900/5 dark:border-neutral-100/5 p-6 pb-5">
          <div className="flex items-center gap-2">
            <div className={cn(
              "w-2 h-2 rounded-full transition-colors",
              companionState.thinking.isStreaming ? "bg-accent-500 animate-pulse" : "bg-neutral-300"
            )} />
            <h2 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
              {mode.mode === 'case' ? 'Case Companion' :
               mode.mode === 'inquiry_focus' ? 'Inquiry Focus' : 'Reasoning'}
            </h2>
          </div>
        </div>

        <div className="overflow-y-auto max-h-[calc(100vh-200px)]">
          {/* Section 1: Thinking (mode-aware) */}
          <ThinkingSection
            content={companionState.thinking.content}
            isStreaming={companionState.thinking.isStreaming}
            mode={companionState.mode.mode}
          />

          {/* Section 2: Status (background work) */}
          <StatusSection
            inProgress={companionState.status.inProgress}
            justCompleted={companionState.status.justCompleted}
            onDismissCompleted={onDismissCompleted}
          />

          {/* Section 3: Session Receipts */}
          <SessionReceiptsSection
            receipts={companionState.sessionReceipts}
            onReceiptClick={onReceiptClick}
          />

          {/* Section 4: Case State (when in case mode) */}
          {companionState.caseState && (
            <CaseStateSection
              caseState={companionState.caseState}
              onViewCase={onViewCase}
              onViewInquiries={onViewInquiries}
            />
          )}
        </div>
      </div>
    </>
  );
}
