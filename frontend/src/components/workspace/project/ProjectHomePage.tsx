/**
 * Project Home Page
 *
 * The main dashboard for a single project. This is the "scoped surface" —
 * chatting here means the AI immediately knows the project context.
 *
 * Sections:
 * 1. Header with project title, description, stats, and actions
 * 2. Scoped chat input (creates project-scoped thread)
 * 3. Action items (prioritized across all project cases)
 * 4. Cases with stage, inquiry progress, and assumption stats
 */

'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { NoCasesEmpty } from '@/components/ui/empty-state';
import { Button } from '@/components/ui/button';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { MessageInput } from '@/components/chat/MessageInput';
import { chatAPI } from '@/lib/api/chat';
import { cn } from '@/lib/utils';
import type { Project } from '@/lib/types/project';
import type { CaseStage } from '@/lib/types/plan';
import type {
  ProjectCaseSummary,
  ProjectStats,
  ProjectActionItem,
} from '@/hooks/useProjectDashboard';

interface ProjectHomePageProps {
  project: Project;
  cases: ProjectCaseSummary[];
  stats: ProjectStats;
  actionItems: ProjectActionItem[];
  isLoading: boolean;
  onCreateCase?: () => void;
  onOpenSettings?: () => void;
  onDelete?: () => void;
  className?: string;
}

export function ProjectHomePage({
  project,
  cases,
  stats,
  actionItems,
  isLoading,
  onCreateCase,
  onOpenSettings,
  onDelete,
  className,
}: ProjectHomePageProps) {
  const router = useRouter();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isSending, setIsSending] = useState(false);

  // Project-scoped chat: create a thread linked to this project
  const handleChatSend = useCallback(async (content: string) => {
    try {
      setIsSending(true);
      const thread = await chatAPI.createThread(project.id);
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('episteme_initial_message', JSON.stringify({ threadId: thread.id, content }));
      }
      router.push(`/chat/${thread.id}`);
    } catch (err) {
      console.error('Failed to start project chat:', err);
      setIsSending(false);
    }
  }, [project.id, router]);

  return (
    <div className={cn('max-w-3xl mx-auto py-8 px-4', className)}>
      {/* Header */}
      <header className="mb-6">
        <Link
          href="/"
          className="text-sm text-neutral-500 dark:text-neutral-400 hover:text-accent-600 dark:hover:text-accent-400 mb-2 inline-flex items-center gap-1"
        >
          <ChevronLeftIcon className="w-4 h-4" />
          Home
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-primary-900 dark:text-primary-50">
              {project.title}
            </h1>
            {project.description && (
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                {project.description}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Button variant="ghost" size="icon" onClick={onOpenSettings} title="Settings">
              <SettingsIcon className="w-5 h-5" />
            </Button>
            {onDelete && (
              <Button variant="ghost" size="icon" onClick={() => setShowDeleteConfirm(true)} title="Archive project">
                <TrashIcon className="w-5 h-5" />
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Stats bar */}
      {!isLoading && stats.totalCases > 0 && (
        <div className="flex items-center gap-4 mb-6 px-1">
          <StatPill
            label="Cases"
            value={`${stats.readyCases}/${stats.totalCases} ready`}
            variant={stats.readyCases === stats.totalCases ? 'success' : 'default'}
          />
          {stats.totalInquiries > 0 && (
            <StatPill
              label="Inquiries"
              value={`${stats.resolvedInquiries}/${stats.totalInquiries} resolved`}
              variant={stats.resolvedInquiries === stats.totalInquiries ? 'success' : 'default'}
            />
          )}
          {stats.highRiskUntested > 0 && (
            <StatPill
              label="Assumptions"
              value={`${stats.highRiskUntested} high-risk untested`}
              variant="warning"
            />
          )}
        </div>
      )}

      {/* Scoped chat input */}
      <div className="mb-8 rounded-lg border border-neutral-200/60 dark:border-neutral-700/50 overflow-hidden">
        <MessageInput
          variant="hero"
          onSend={handleChatSend}
          disabled={isSending}
          placeholder={`Ask about ${project.title}...`}
        />
      </div>

      {/* Action items */}
      {!isLoading && actionItems.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
            Action Items
          </h2>
          <div className="space-y-2">
            {actionItems.map((item) => (
              <ActionItemRow key={item.id} item={item} />
            ))}
          </div>
        </section>
      )}

      {/* Cases */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
            Cases
          </h2>
          {cases.length > 0 && (
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              {stats.readyCases}/{stats.totalCases} ready
            </span>
          )}
        </div>

        {cases.length === 0 && !isLoading ? (
          <NoCasesEmpty onCreate={onCreateCase || (() => {})} />
        ) : (
          <>
            <div className="space-y-3">
              {cases.map((caseItem) => (
                <ProjectCaseCard key={caseItem.id} caseItem={caseItem} />
              ))}
            </div>

            <Button variant="outline" className="w-full mt-4" onClick={onCreateCase}>
              <PlusIcon className="w-4 h-4 mr-2" />
              New Case
            </Button>
          </>
        )}
      </section>

      {/* Delete Confirm Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={() => {
          setShowDeleteConfirm(false);
          onDelete?.();
        }}
        title="Archive project"
        description={`"${project.title}" and all its cases will be archived. You can restore it later.`}
        confirmLabel="Archive"
        variant="danger"
      />
    </div>
  );
}

// ===== Stats Pill =====

function StatPill({
  label,
  value,
  variant = 'default',
}: {
  label: string;
  value: string;
  variant?: 'default' | 'success' | 'warning';
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-neutral-500 dark:text-neutral-400">{label}</span>
      <span
        className={cn(
          'text-xs font-medium tabular-nums',
          variant === 'success' && 'text-success-600 dark:text-success-400',
          variant === 'warning' && 'text-warning-600 dark:text-warning-400',
          variant === 'default' && 'text-primary-900 dark:text-primary-100'
        )}
      >
        {value}
      </span>
    </div>
  );
}

// ===== Action Item Row =====

const ACTION_TYPE_CONFIG: Record<ProjectActionItem['type'], { icon: string; color: string }> = {
  resolve_inquiry: { icon: '\u26a1', color: 'text-warning-600 dark:text-warning-400' },
  untested_assumptions: { icon: '\u26a0\ufe0f', color: 'text-warning-600 dark:text-warning-400' },
  resume_investigating: { icon: '\u2192', color: 'text-accent-600 dark:text-accent-400' },
  criteria_progress: { icon: '\u2713', color: 'text-success-600 dark:text-success-400' },
  start_investigation: { icon: '\u2022', color: 'text-neutral-500 dark:text-neutral-400' },
};

function ActionItemRow({ item }: { item: ProjectActionItem }) {
  const config = ACTION_TYPE_CONFIG[item.type] ?? ACTION_TYPE_CONFIG.start_investigation;

  return (
    <Link
      href={item.href}
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border',
        'border-neutral-200/80 dark:border-neutral-800/80',
        'hover:border-accent-300 dark:hover:border-accent-700',
        'hover:bg-accent-50/30 dark:hover:bg-accent-900/10',
        'transition-all duration-150'
      )}
    >
      <span className="text-sm shrink-0">{config.icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-primary-900 dark:text-primary-50 truncate">
          {item.title}
        </p>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate">
          {item.caseTitle}
        </p>
      </div>
      <ChevronIcon className="w-4 h-4 text-neutral-400 shrink-0" />
    </Link>
  );
}

// ===== Case Card =====

const STAGE_CONFIG: Record<CaseStage, { label: string; dotColor: string }> = {
  exploring: { label: 'Exploring', dotColor: 'bg-neutral-400' },
  investigating: { label: 'Investigating', dotColor: 'bg-info-500' },
  synthesizing: { label: 'Synthesizing', dotColor: 'bg-warning-500' },
  ready: { label: 'Ready', dotColor: 'bg-success-500' },
};

function ProjectCaseCard({ caseItem }: { caseItem: ProjectCaseSummary }) {
  const stage = STAGE_CONFIG[caseItem.stage];

  return (
    <Link
      href={`/cases/${caseItem.id}`}
      className={cn(
        'block rounded-lg border p-4',
        'border-neutral-200/80 dark:border-neutral-800/80',
        'hover:border-accent-300 dark:hover:border-accent-700',
        'hover:bg-accent-50/30 dark:hover:bg-accent-900/10',
        'transition-all duration-150 group'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            {caseItem.isReady ? (
              <CheckCircleIcon className="w-4 h-4 text-success-500 shrink-0" />
            ) : (
              <div className={cn('w-2 h-2 rounded-full shrink-0', stage.dotColor)} />
            )}
            <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
              {stage.label}
            </span>
          </div>

          <h3 className="text-sm font-medium text-primary-900 dark:text-primary-100 truncate">
            {caseItem.title}
          </h3>

          <div className="flex items-center gap-3 mt-1.5 text-xs text-neutral-500 dark:text-neutral-400">
            {caseItem.inquiries.total > 0 && (
              <span className="tabular-nums">
                {caseItem.inquiries.resolved}/{caseItem.inquiries.total} inquiries
              </span>
            )}
            {caseItem.assumptions.highRiskUntested > 0 && (
              <span className="text-warning-600 dark:text-warning-400">
                {caseItem.assumptions.highRiskUntested} untested
              </span>
            )}
            <span>{formatRelativeTime(caseItem.updatedAt)}</span>
          </div>
        </div>

        <span
          className={cn(
            'text-xs font-medium px-2.5 py-1 rounded-md shrink-0',
            'text-accent-700 dark:text-accent-300',
            'bg-accent-100 dark:bg-accent-900/40',
            'opacity-0 group-hover:opacity-100 transition-opacity duration-150'
          )}
        >
          Open
        </span>
      </div>
    </Link>
  );
}

// ===== Utils =====

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);

  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ===== Icons =====

function ChevronLeftIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  );
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="3 6 5 6 21 6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default ProjectHomePage;
