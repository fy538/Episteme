/**
 * CaseStructurePanelContent
 *
 * Sidebar content for CASE mode (zoomed into a decision).
 * Shows "← [Project Name]" back button and the case's structure nav
 * (plan phases, inquiries, assumptions, criteria).
 *
 * The back button navigates to the project page, triggering the
 * sidebar slide-back animation to PROJECT mode.
 */

'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { CaseStructureNav } from '@/components/workspace/CaseStructureNav';
import { useCaseWorkspaceContext } from '@/components/workspace/CaseWorkspaceProvider';
import { useProjectWorkspaceContext } from '@/components/workspace/ProjectWorkspaceProvider';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ArrowLeftIcon } from '@/components/ui/icons';
import { cn } from '@/lib/utils';

export function CaseStructurePanelContent() {
  const router = useRouter();
  const workspace = useCaseWorkspaceContext();

  // Resolve project name for the back button
  const projectInfo = useMemo(() => {
    if (!workspace?.caseData?.project || !workspace.projects) {
      return { name: 'Back', id: null };
    }
    const project = workspace.projects.find((p) => p.id === workspace.caseData!.project);
    return {
      name: project?.title ?? 'Back',
      id: workspace.caseData.project,
    };
  }, [workspace?.caseData?.project, workspace?.projects]);

  const handleBack = () => {
    if (projectInfo.id) {
      router.push(`/projects/${projectInfo.id}`);
    } else {
      router.push('/');
    }
  };

  const backButton = (
    <Button
      variant="ghost"
      onClick={handleBack}
      className={cn(
        'flex items-center gap-1.5 px-3 py-2.5 w-full text-left justify-start h-auto rounded-none',
        'text-xs text-neutral-500 dark:text-neutral-400',
        'hover:text-neutral-700 dark:hover:text-neutral-300',
        'hover:bg-neutral-50 dark:hover:bg-neutral-800/50',
        'border-b border-neutral-200 dark:border-neutral-800'
      )}
    >
      <ArrowLeftIcon className="w-3.5 h-3.5" />
      <span className="truncate">{projectInfo.name}</span>
    </Button>
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
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-6 w-full rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {backButton}

      {/* Sibling cases (other cases in the same project) */}
      <SiblingCases currentCaseId={workspace.caseData.id} />

      {/* Case structure nav — uses workspace context */}
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

// ─── Sibling Cases ──────────────────────────────────────

function SiblingCases({ currentCaseId }: { currentCaseId: string }) {
  const [expanded, setExpanded] = useState(false);
  const projectWorkspace = useProjectWorkspaceContext();

  // Get sibling cases from project workspace, excluding the current case
  const siblings = useMemo(() => {
    if (!projectWorkspace?.cases) return [];
    return projectWorkspace.cases.filter((c) => c.id !== currentCaseId);
  }, [projectWorkspace?.cases, currentCaseId]);

  if (siblings.length === 0) return null;

  return (
    <div className="border-b border-neutral-200 dark:border-neutral-800">
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          'flex items-center gap-1.5 w-full px-3 py-1.5 text-left',
          'text-xs text-neutral-500 dark:text-neutral-400',
          'hover:bg-neutral-50 dark:hover:bg-neutral-800/50',
          'transition-colors duration-150'
        )}
      >
        <svg
          className={cn(
            'w-3 h-3 text-neutral-400 dark:text-neutral-500 shrink-0 transition-transform duration-150',
            expanded && 'rotate-90'
          )}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
        >
          <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span>Other Cases ({siblings.length})</span>
      </button>
      {expanded && (
        <div className="px-2 pb-1.5 space-y-0.5">
          {siblings.map((caseItem) => (
            <Link
              key={caseItem.id}
              href={`/cases/${caseItem.id}`}
              className={cn(
                'flex items-center gap-1.5 px-2 py-1 rounded-md',
                'text-neutral-700 dark:text-neutral-300',
                'hover:bg-neutral-100 dark:hover:bg-neutral-800',
                'transition-colors duration-150'
              )}
            >
              <SiblingCaseDot status={caseItem.status} />
              <span className="text-xs truncate flex-1">{caseItem.title}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function SiblingCaseDot({ status }: { status: string }) {
  const color =
    status === 'decided'
      ? 'bg-success-500'
      : status === 'active'
        ? 'bg-accent-400'
        : 'bg-neutral-300 dark:bg-neutral-600';
  return <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', color)} />;
}
