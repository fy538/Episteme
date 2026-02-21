/**
 * Project Cases Page
 *
 * Route: /projects/[projectId]/cases
 *
 * Displays active decisions and decided cases for the project.
 * Active cases show decision question, stage, risk indicators.
 * Decided cases show resolution type, date, outcome status.
 *
 * "+ New Case" opens ScaffoldingChat in a modal overlay.
 */

'use client';

import { useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { Spinner } from '@/components/ui/spinner';
import { useProjectCasesList } from '@/hooks/useProjectCasesList';
import ScaffoldingChat from '@/components/workspace/case/ScaffoldingChat';
import type { Case } from '@/lib/types/case';
import { cn } from '@/lib/utils';

export default function ProjectCasesPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const queryClient = useQueryClient();

  const { activeCases, decidedCases, isLoading } = useProjectCasesList(projectId);
  const [showDecided, setShowDecided] = useState(false);
  const [showScaffold, setShowScaffold] = useState(false);

  const handleCaseCreated = useCallback(
    (caseId: string) => {
      setShowScaffold(false);
      queryClient.invalidateQueries({ queryKey: ['project-cases', projectId] });
      router.push(`/cases/${caseId}`);
    },
    [projectId, router, queryClient]
  );

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            Cases
          </h1>
          <button
            onClick={() => setShowScaffold(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-accent-600 hover:bg-accent-700 rounded-lg transition-colors"
          >
            <PlusIcon className="w-3.5 h-3.5" />
            New Case
          </button>
        </div>

        {/* Empty state */}
        {activeCases.length === 0 && decidedCases.length === 0 && (
          <div className="text-center py-16">
            <div className="w-12 h-12 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center mx-auto mb-4">
              <CaseIcon className="w-6 h-6 text-neutral-400" />
            </div>
            <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              No cases yet
            </h3>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-4 max-w-xs mx-auto">
              Cases help you investigate decisions with structured reasoning and evidence.
            </p>
            <button
              onClick={() => setShowScaffold(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-accent-600 hover:text-accent-700 border border-accent-200 dark:border-accent-800 rounded-lg hover:bg-accent-50 dark:hover:bg-accent-950/30 transition-colors"
            >
              <PlusIcon className="w-3.5 h-3.5" />
              Start a case
            </button>
          </div>
        )}

        {/* Active Decisions */}
        {activeCases.length > 0 && (
          <section className="mb-8">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-3">
              Active Decisions
            </h2>
            <div className="space-y-3">
              {activeCases.map((c) => (
                <ActiveCaseCard key={c.id} case_={c} projectId={projectId} />
              ))}
            </div>
          </section>
        )}

        {/* Decided */}
        {decidedCases.length > 0 && (
          <section>
            <button
              onClick={() => setShowDecided((v) => !v)}
              className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-3 hover:text-neutral-700 dark:hover:text-neutral-300 transition-colors"
            >
              <ChevronIcon
                className={cn(
                  'w-3 h-3 transition-transform',
                  showDecided && 'rotate-90'
                )}
              />
              Decided ({decidedCases.length})
            </button>
            {showDecided && (
              <div className="space-y-3">
                {decidedCases.map((c) => (
                  <DecidedCaseCard key={c.id} case_={c} projectId={projectId} />
                ))}
              </div>
            )}
          </section>
        )}
      </div>

      {/* Scaffolding modal */}
      {showScaffold && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/20 backdrop-blur-[2px]"
            onClick={() => setShowScaffold(false)}
          />
          <div className="relative z-10 w-full max-w-2xl mx-4 max-h-[80vh] bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-700 shadow-xl overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-5 py-3 border-b border-neutral-200 dark:border-neutral-700 shrink-0">
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                New Case
              </h3>
              <button
                onClick={() => setShowScaffold(false)}
                className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
              >
                <CloseIcon className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto">
              <ScaffoldingChat
                projectId={projectId}
                onCaseCreated={handleCaseCreated}
                onCancel={() => setShowScaffold(false)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Active Case Card ───────────────────────────────────────────

function ActiveCaseCard({ case_: c, projectId }: { case_: Case; projectId: string }) {
  const stage = c.plan_stage || 'exploring';
  const riskCount = c.risk_indicator || 0;

  return (
    <Link
      href={`/cases/${c.id}`}
      className="block p-4 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 line-clamp-2">
            {c.decision_question || c.title}
          </p>
          <div className="flex items-center gap-3 mt-2">
            <StageBadge stage={stage} />
            {riskCount > 0 && (
              <span className="inline-flex items-center gap-1 text-xs text-warning-600 dark:text-warning-400">
                <WarningIcon className="w-3 h-3" />
                {riskCount} high-risk assumption{riskCount > 1 ? 's' : ''}
              </span>
            )}
            {c.stakes === 'high' && (
              <span className="text-xs text-neutral-400 dark:text-neutral-500">
                High stakes
              </span>
            )}
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-neutral-300 dark:text-neutral-600 shrink-0 mt-1" />
      </div>
    </Link>
  );
}

// ─── Decided Case Card ──────────────────────────────────────────

function DecidedCaseCard({ case_: c, projectId }: { case_: Case; projectId: string }) {
  const summary = c.decision_summary;
  const decidedDate = summary?.decided_at
    ? new Date(summary.decided_at).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      })
    : null;

  return (
    <Link
      href={`/cases/${c.id}`}
      className="block p-4 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300 line-clamp-2">
            {c.decision_question || c.title}
          </p>
          <div className="flex items-center gap-3 mt-2">
            {summary && (
              <ResolutionBadge type={summary.resolution_type} />
            )}
            {decidedDate && (
              <span className="text-xs text-neutral-400 dark:text-neutral-500">
                {decidedDate}
              </span>
            )}
            {summary?.outcome_status && summary.outcome_status !== 'pending' && (
              <OutcomeStatusBadge status={summary.outcome_status} />
            )}
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-neutral-300 dark:text-neutral-600 shrink-0 mt-1" />
      </div>
    </Link>
  );
}

// ─── Badges ─────────────────────────────────────────────────────

const stageColors: Record<string, string> = {
  exploring: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  investigating: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  synthesizing: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  ready: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
};

const stageLabels: Record<string, string> = {
  exploring: 'Exploring',
  investigating: 'Investigating',
  synthesizing: 'Synthesizing',
  ready: 'Ready to decide',
};

function StageBadge({ stage }: { stage: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium',
        stageColors[stage] || stageColors.exploring
      )}
    >
      {stageLabels[stage] || stage}
    </span>
  );
}

const resolutionLabels: Record<string, string> = {
  resolved: 'Resolved',
  deferred: 'Deferred',
  abandoned: 'Abandoned',
  split: 'Split',
};

function ResolutionBadge({ type }: { type: string }) {
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400">
      {resolutionLabels[type] || type}
    </span>
  );
}

const outcomeStyles: Record<string, string> = {
  overdue: 'text-warning-600 dark:text-warning-400',
  positive: 'text-success-600 dark:text-success-400',
  negative: 'text-error-600 dark:text-error-400',
  neutral: 'text-neutral-500 dark:text-neutral-400',
};

const outcomeLabels: Record<string, string> = {
  overdue: 'Outcome check overdue',
  positive: 'Positive outcome',
  negative: 'Negative outcome',
  neutral: 'Outcome noted',
};

function OutcomeStatusBadge({ status }: { status: string }) {
  return (
    <span className={cn('text-xs', outcomeStyles[status] || outcomeStyles.neutral)}>
      {outcomeLabels[status] || status}
    </span>
  );
}

// ─── Icons ──────────────────────────────────────────────────────

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CaseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronRight({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.999L13.732 4.001c-.77-1.333-2.694-1.333-3.464 0L3.34 16.001C2.57 17.334 3.532 19 5.072 19z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
