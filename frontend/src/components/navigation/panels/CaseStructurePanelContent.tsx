/**
 * CaseStructurePanelContent
 *
 * Sidebar panel content that replaces the case list when a case is active.
 * Shows a "← Decisions" back button and the case's structure nav (plan,
 * inquiries, assumptions, criteria).
 *
 * Part of the drill-down sidebar pattern: case list → case structure → back.
 * The back button slides back to the case list without page navigation.
 */

'use client';

import { CaseStructureNav } from '@/components/workspace/CaseStructureNav';
import { useCaseWorkspaceContext } from '@/components/workspace/CaseWorkspaceProvider';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface CaseStructurePanelContentProps {
  onBack: () => void;
}

export function CaseStructurePanelContent({ onBack }: CaseStructurePanelContentProps) {
  const workspace = useCaseWorkspaceContext();

  const backButton = (
    <button
      onClick={onBack}
      className={cn(
        'flex items-center gap-1.5 px-3 py-2.5 w-full text-left',
        'text-xs text-neutral-500 dark:text-neutral-400',
        'hover:text-neutral-700 dark:hover:text-neutral-300',
        'hover:bg-neutral-50 dark:hover:bg-neutral-800/50',
        'transition-colors border-b border-neutral-200 dark:border-neutral-800'
      )}
    >
      <ArrowLeftIcon className="w-3.5 h-3.5" />
      <span>Decisions</span>
    </button>
  );

  // Loading state — workspace exists but data is still fetching
  if (!workspace || workspace.loading || !workspace.caseData) {
    return (
      <div className="flex flex-col h-full">
        {backButton}
        <div className="p-3 space-y-3">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-3 w-16" />
          <div className="mt-4 space-y-2">
            {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-6 w-full rounded" />)}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {backButton}

      {/* Case structure nav */}
      <div className="flex-1 overflow-hidden">
        <CaseStructureNav
          caseId={workspace.caseData.id}
          caseTitle={workspace.caseData.title}
          plan={workspace.plan}
          inquiries={workspace.inquiries}
          documentCount={workspace.documents?.length ?? 0}
          viewMode={workspace.viewMode}
          activeInquiryId={workspace.activeInquiryId}
          onNavigate={(mode, inquiryId) => {
            if (inquiryId) {
              workspace.handleOpenInquiry(inquiryId);
            } else {
              workspace.setViewMode(mode);
            }
          }}
          isCollapsed={false}
          onToggleCollapse={() => {}}
          activeSkills={workspace.caseData.active_skills_summary}
          hideCollapseToggle
        />
      </div>
    </div>
  );
}

function ArrowLeftIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="19" y1="12" x2="5" y2="12" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="12 19 5 12 12 5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
