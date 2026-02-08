/**
 * CaseHome — Default main content view for the case workspace.
 *
 * Three vertically stacked zones:
 *   1. StageHeader: title, position statement, stage progression dots
 *   2. InvestigationTimeline: windowed inquiry list with fade edges
 *   3. ContextPanel: stage-adaptive sections (signals, assumptions, criteria)
 *
 * Fetches data via useCaseHome (aggregated getCaseHome endpoint).
 * Interactive: assumptions can be status-toggled, criteria toggled, items sent to chat.
 */

'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { plansAPI } from '@/lib/api/plans';
import { useCaseHome } from '@/hooks/useCaseHome';
import { useOptimisticPlanUpdate } from '@/hooks/useOptimisticPlanUpdate';
import type { CaseStage, CaseHomeInquiry, CaseHomeSignal, PlanAssumption, DecisionCriterion } from '@/lib/types/plan';
import { PremortemModal } from '@/components/cases/PremortemModal';
import { WhatChangedMindCard } from '@/components/cases/WhatChangedMindCard';
import { JudgmentSummaryCard } from '@/components/cases/JudgmentSummaryCard';
import { CheckCircleSmall, CircleSmall, SpinnerSmall, ChatBubbleIcon } from '@/components/ui/icons';

export interface ChatAboutPayload {
  text: string;
  source_type: 'assumption' | 'criterion' | 'signal' | 'inquiry';
  source_id: string;
}

interface CaseHomeProps {
  caseId: string;
  onViewInquiry: (inquiryId: string) => void;
  onViewAll: () => void;
  onChatAbout?: (payload: ChatAboutPayload) => void;
  onGeneratePlan?: () => void;
  className?: string;
}

export function CaseHome({ caseId, onViewInquiry, onViewAll, onChatAbout, onGeneratePlan, className }: CaseHomeProps) {
  const queryClient = useQueryClient();
  const {
    data,
    isLoading,
    stage,
    assumptionSummary,
    criteriaProgress,
  } = useCaseHome(caseId);

  const [showPremortem, setShowPremortem] = useState(false);

  // Auto-generate plan when CaseHome mounts with no plan
  const autoGenAttemptedRef = useRef(false);
  const [autoGenFailed, setAutoGenFailed] = useState(false);
  const [autoGenInProgress, setAutoGenInProgress] = useState(false);

  useEffect(() => {
    if (data && !data.plan && !isLoading && onGeneratePlan && !autoGenAttemptedRef.current) {
      autoGenAttemptedRef.current = true;
      setAutoGenInProgress(true);
      try {
        Promise.resolve(onGeneratePlan()).then(() => {
          setAutoGenInProgress(false);
        }).catch(() => {
          setAutoGenInProgress(false);
          setAutoGenFailed(true);
        });
      } catch {
        setAutoGenInProgress(false);
        setAutoGenFailed(true);
      }
    }
  }, [data, isLoading, onGeneratePlan]);

  const { optimisticUpdate, lastError: planError, clearError: clearPlanError } = useOptimisticPlanUpdate(caseId);

  // --- Mutation handlers (delegated to useOptimisticPlanUpdate) ---
  const handleUpdateAssumption = useCallback(async (assumptionId: string, newStatus: string) => {
    await optimisticUpdate(
      (old) => ({
        ...old,
        plan: old.plan ? {
          ...old.plan,
          current_content: old.plan.current_content ? {
            ...old.plan.current_content,
            assumptions: old.plan.current_content.assumptions.map((a) =>
              a.id === assumptionId ? { ...a, status: newStatus as PlanAssumption['status'] } : a
            ),
          } : old.plan.current_content,
        } : old.plan,
      }),
      () => plansAPI.updateAssumption(caseId, assumptionId, newStatus),
      'update assumption',
    );
  }, [caseId, optimisticUpdate]);

  const handleUpdateCriterion = useCallback(async (criterionId: string, isMet: boolean) => {
    await optimisticUpdate(
      (old) => ({
        ...old,
        plan: old.plan ? {
          ...old.plan,
          current_content: old.plan.current_content ? {
            ...old.plan.current_content,
            decision_criteria: old.plan.current_content.decision_criteria.map((c) =>
              c.id === criterionId ? { ...c, is_met: isMet } : c
            ),
          } : old.plan.current_content,
        } : old.plan,
      }),
      () => plansAPI.updateCriterion(caseId, criterionId, isMet),
      'update criterion',
    );
  }, [caseId, optimisticUpdate]);

  const handleStageChange = useCallback(async (newStage: CaseStage) => {
    await optimisticUpdate(
      (old) => ({
        ...old,
        plan: old.plan ? { ...old.plan, stage: newStage } : old.plan,
      }),
      () => plansAPI.updateStage(caseId, newStage),
      'update stage',
    );
    // Show premortem prompt when entering synthesizing stage
    if (newStage === 'synthesizing' && !data?.case.premortem_text) {
      setShowPremortem(true);
    }
  }, [caseId, optimisticUpdate, data]);

  if (isLoading || !data) {
    return (
      <div className={cn('max-w-3xl mx-auto py-8 px-6', className)}>
        <div className="space-y-6 animate-pulse">
          <div className="h-8 w-64 bg-neutral-200 dark:bg-neutral-800 rounded" />
          <div className="h-4 w-96 bg-neutral-200 dark:bg-neutral-800 rounded" />
          <div className="h-48 bg-neutral-200 dark:bg-neutral-800 rounded-lg" />
          <div className="h-32 bg-neutral-200 dark:bg-neutral-800 rounded-lg" />
        </div>
      </div>
    );
  }

  const plan = data.plan;
  const content = plan?.current_content;

  // Empty state when no plan exists — doubles as onboarding for new cases
  if (!plan) {
    const hasInquiries = data.inquiries.length > 0;
    const isFirstVisit = !hasInquiries && !(data.signals?.total_count);

    return (
      <div className={cn('max-w-3xl mx-auto py-8 px-6 space-y-8', className)}>
        {/* Case title */}
        <header>
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-100">
            {data.case.title ?? ''}
          </h1>
        </header>

        {/* First-time walkthrough guide */}
        {isFirstVisit && (
          <section className="rounded-lg border border-accent-200/80 dark:border-accent-800/50 bg-accent-50/50 dark:bg-accent-900/10 p-5 space-y-4">
            <h2 className="text-sm font-semibold text-accent-700 dark:text-accent-300">
              How to investigate a decision
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { step: '1', title: 'Chat about your decision', desc: 'Use the chat panel to explore your thinking. Episteme will extract assumptions and signals.' },
                { step: '2', title: 'Generate a plan', desc: 'Once you have context, generate an investigation plan to structure your inquiry.' },
                { step: '3', title: 'Test & resolve', desc: 'Open inquiries, gather evidence, and track your assumptions until you\'re ready to decide.' },
              ].map(item => (
                <div key={item.step} className="flex items-start gap-2.5">
                  <span className="w-6 h-6 rounded-full bg-accent-600 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                    {item.step}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{item.title}</p>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 leading-relaxed">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-accent-600 dark:text-accent-400">
              Start by chatting about your decision in the panel on the right →
            </p>
          </section>
        )}

        {/* Investigation Timeline (may already have inquiries) */}
        <InvestigationTimeline
          inquiries={data.inquiries}
          onViewInquiry={onViewInquiry}
          onViewAll={onViewAll}
        />

        {/* Plan generation — auto-generating or manual retry */}
        <section className="rounded-lg border border-dashed border-neutral-300 dark:border-neutral-700 p-6 text-center space-y-3">
          {autoGenFailed ? (
            <>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                Plan generation failed. You can try again.
              </p>
              {onGeneratePlan && (
                <button
                  onClick={() => {
                    setAutoGenFailed(false);
                    setAutoGenInProgress(true);
                    autoGenAttemptedRef.current = true;
                    try {
                      Promise.resolve(onGeneratePlan()).then(() => {
                        setAutoGenInProgress(false);
                      }).catch(() => {
                        setAutoGenInProgress(false);
                        setAutoGenFailed(true);
                      });
                    } catch {
                      setAutoGenInProgress(false);
                      setAutoGenFailed(true);
                    }
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-accent-600 text-white text-sm font-medium rounded-lg hover:bg-accent-700 transition-colors"
                >
                  Retry
                </button>
              )}
            </>
          ) : autoGenInProgress ? (
            <>
              <div className="w-10 h-10 mx-auto rounded-full bg-accent-100 dark:bg-accent-900/30 flex items-center justify-center">
                <svg className="w-5 h-5 text-accent-600 dark:text-accent-400 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              </div>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                Setting up investigation plan…
              </p>
            </>
          ) : (
            <>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                Preparing your investigation plan…
              </p>
            </>
          )}
        </section>
      </div>
    );
  }

  return (
    <div className={cn('max-w-3xl mx-auto py-8 px-6 space-y-8', className)}>
      {planError && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 flex items-center justify-between" role="alert">
          <p className="text-sm text-red-700 dark:text-red-300">{planError}</p>
          <button onClick={clearPlanError} className="text-xs text-red-500 hover:text-red-700">Dismiss</button>
        </div>
      )}

      {/* Zone 1: Stage Header */}
      <StageHeader
        caseTitle={data.case.title ?? ''}
        positionStatement={plan?.position_statement ?? ''}
        stage={stage}
        stageRationale={content?.stage_rationale ?? ''}
        onStageChange={handleStageChange}
      />

      {/* Zone 2: Investigation Timeline (windowed) */}
      <InvestigationTimeline
        inquiries={data.inquiries}
        onViewInquiry={onViewInquiry}
        onViewAll={onViewAll}
      />

      {/* Zone 3: Context Panel (stage-adaptive, interactive) */}
      <ContextPanel
        stage={stage}
        stageRationale={content?.stage_rationale ?? ''}
        assumptions={content?.assumptions ?? []}
        criteria={content?.decision_criteria ?? []}
        signals={data.signals?.recent ?? []}
        assumptionSummary={assumptionSummary}
        criteriaProgress={criteriaProgress}
        onUpdateAssumption={handleUpdateAssumption}
        onUpdateCriterion={handleUpdateCriterion}
        onChatAbout={onChatAbout}
        premortemText={data.case.premortem_text ?? ''}
        caseId={caseId}
        whatWouldChangeMind={data.case.what_would_change_mind ?? ''}
        whatChangedMindResponse={data.case.what_changed_mind_response ?? ''}
      />

      <PremortemModal
        caseId={caseId}
        isOpen={showPremortem}
        onClose={() => setShowPremortem(false)}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ['case-home', caseId] });
        }}
      />
    </div>
  );
}

// ─── Zone 1: Stage Header ────────────────────────────────

const STAGES: { key: CaseStage; label: string }[] = [
  { key: 'exploring', label: 'Exploring' },
  { key: 'investigating', label: 'Investigating' },
  { key: 'synthesizing', label: 'Synthesizing' },
  { key: 'ready', label: 'Ready' },
];

function StageHeader({
  caseTitle,
  positionStatement,
  stage,
  stageRationale,
  onStageChange,
}: {
  caseTitle: string;
  positionStatement: string;
  stage: CaseStage;
  stageRationale: string;
  onStageChange?: (stage: CaseStage) => void;
}) {
  const currentIndex = STAGES.findIndex(s => s.key === stage);

  return (
    <header>
      <h1 className="text-2xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-100">
        {caseTitle}
      </h1>

      {positionStatement && (
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1.5 leading-relaxed">
          {positionStatement}
        </p>
      )}

      {/* Stage progression — clickable for adjacent stages */}
      <div className="flex items-center gap-2 mt-4">
        {STAGES.map((s, idx) => {
          const isCompleted = idx < currentIndex;
          const isCurrent = idx === currentIndex;
          const canTransition = onStageChange && Math.abs(idx - currentIndex) === 1;

          return (
            <div key={s.key} className="flex items-center gap-2">
              {idx > 0 && (
                <div className={cn(
                  'w-8 h-px',
                  isCompleted ? 'bg-emerald-400' : 'bg-neutral-200 dark:bg-neutral-700'
                )} />
              )}
              <button
                onClick={() => canTransition && onStageChange?.(s.key)}
                disabled={!canTransition}
                className={cn(
                  'flex items-center gap-1.5 transition-opacity',
                  canTransition
                    ? 'cursor-pointer hover:opacity-70'
                    : 'cursor-default'
                )}
                title={canTransition ? `Move to ${s.label}` : undefined}
              >
                <div className={cn(
                  'w-2.5 h-2.5 rounded-full border-2 transition-colors',
                  isCompleted && 'border-emerald-500 bg-emerald-500',
                  isCurrent && 'border-accent-500 bg-accent-500',
                  !isCompleted && !isCurrent && 'border-neutral-300 dark:border-neutral-600 bg-transparent'
                )} />
                <span className={cn(
                  'text-xs',
                  isCurrent
                    ? 'text-accent-600 dark:text-accent-400 font-medium'
                    : isCompleted
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-neutral-400 dark:text-neutral-500'
                )}>
                  {s.label}
                </span>
              </button>
            </div>
          );
        })}
      </div>

      {stageRationale && (
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-2 italic">
          {stageRationale}
        </p>
      )}
    </header>
  );
}

// ─── Zone 2: Investigation Timeline ────────────────────────

function InvestigationTimeline({
  inquiries,
  onViewInquiry,
  onViewAll,
}: {
  inquiries: CaseHomeInquiry[];
  onViewInquiry: (id: string) => void;
  onViewAll: () => void;
}) {
  if (inquiries.length === 0) {
    return (
      <section>
        <SectionTitle>Investigation</SectionTitle>
        <div className="rounded-lg border border-neutral-200/80 dark:border-neutral-800/80 p-6 text-center">
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            No inquiries yet. Start a conversation to generate investigation questions.
          </p>
        </div>
      </section>
    );
  }

  const sorted = [...inquiries].sort((a, b) => a.sequence_index - b.sequence_index);

  return (
    <section>
      <SectionTitle>Investigation</SectionTitle>
      <div className="relative">
        {/* Windowed container with fade edges */}
        <div className="max-h-[320px] overflow-y-auto rounded-lg border border-neutral-200/80 dark:border-neutral-800/80 bg-white dark:bg-neutral-900/50 timeline-window">
          <div className="divide-y divide-neutral-100 dark:divide-neutral-800/50">
            {sorted.map(inquiry => (
              <InquiryTimelineItem
                key={inquiry.id}
                inquiry={inquiry}
                onClick={() => onViewInquiry(inquiry.id)}
              />
            ))}
          </div>
        </div>

        {/* Fade gradient at top */}
        {inquiries.length > 4 && (
          <>
            <div className="absolute top-0 left-0 right-0 h-6 bg-gradient-to-b from-white dark:from-neutral-900/50 to-transparent pointer-events-none rounded-t-lg z-10" />
            <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-white dark:from-neutral-900/50 to-transparent pointer-events-none rounded-b-lg z-10" />
          </>
        )}
      </div>

      <button
        onClick={onViewAll}
        className="text-xs text-accent-600 dark:text-accent-400 hover:underline mt-2 inline-block"
      >
        View all research →
      </button>
    </section>
  );
}

function InquiryTimelineItem({
  inquiry,
  onClick,
}: {
  inquiry: CaseHomeInquiry;
  onClick: () => void;
}) {
  const isResolved = inquiry.status === 'resolved';
  const isInvestigating = inquiry.status === 'investigating';

  return (
    <button
      onClick={onClick}
      className="flex items-start gap-3 w-full text-left p-3 hover:bg-neutral-50 dark:hover:bg-neutral-800/30 transition-colors"
    >
      {/* Status icon */}
      <span className="mt-0.5 shrink-0">
        {isResolved ? (
          <CheckCircleSmall className="w-4 h-4 text-emerald-500" />
        ) : isInvestigating ? (
          <SpinnerSmall className="w-4 h-4 text-accent-500" />
        ) : (
          <CircleSmall className="w-4 h-4 text-neutral-300 dark:text-neutral-600" />
        )}
      </span>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn(
            'text-sm font-medium truncate',
            isResolved
              ? 'text-neutral-500 dark:text-neutral-400'
              : 'text-neutral-800 dark:text-neutral-200'
          )}>
            {inquiry.title}
          </span>
          {inquiry.evidence_count > 0 && (
            <span className="text-[10px] bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 px-1.5 py-0.5 rounded-full shrink-0">
              {inquiry.evidence_count}
            </span>
          )}
        </div>

        {inquiry.latest_evidence_text && (
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 line-clamp-1">
            {inquiry.latest_evidence_text}
          </p>
        )}

        {inquiry.conclusion && isResolved && (
          <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5 line-clamp-1">
            {inquiry.conclusion}
          </p>
        )}
      </div>
    </button>
  );
}

// ─── Zone 3: Context Panel (stage-adaptive) ────────────────

const ASSUMPTION_STATUSES = ['untested', 'confirmed', 'challenged', 'refuted'] as const;

function ContextPanel({
  stage,
  stageRationale,
  assumptions,
  criteria,
  signals,
  assumptionSummary,
  criteriaProgress,
  onUpdateAssumption,
  onUpdateCriterion,
  onChatAbout,
  premortemText,
  caseId,
  whatWouldChangeMind,
  whatChangedMindResponse,
}: {
  stage: CaseStage;
  stageRationale: string;
  assumptions: PlanAssumption[];
  criteria: DecisionCriterion[];
  signals: CaseHomeSignal[];
  assumptionSummary: { untested: number; confirmed: number; challenged: number; refuted: number; total: number };
  criteriaProgress: { met: number; total: number };
  onUpdateAssumption?: (assumptionId: string, newStatus: string) => void;
  onUpdateCriterion?: (criterionId: string, isMet: boolean) => void;
  onChatAbout?: (payload: ChatAboutPayload) => void;
  premortemText?: string;
  caseId?: string;
  whatWouldChangeMind?: string;
  whatChangedMindResponse?: string;
}) {
  return (
    <section className="space-y-6">
      {/* Stage-adaptive content */}
      {stage === 'exploring' && (
        <ExploringContext signals={signals} onChatAbout={onChatAbout} />
      )}

      {stage === 'investigating' && (
        <InvestigatingContext
          assumptions={assumptions}
          assumptionSummary={assumptionSummary}
          onUpdateAssumption={onUpdateAssumption}
          onChatAbout={onChatAbout}
        />
      )}

      {(stage === 'synthesizing' || stage === 'ready') && (
        <SynthesizingContext
          criteria={criteria}
          criteriaProgress={criteriaProgress}
          assumptions={assumptions}
          assumptionSummary={assumptionSummary}
          onUpdateCriterion={onUpdateCriterion}
          onChatAbout={onChatAbout}
          premortemText={premortemText}
          caseId={caseId}
          whatWouldChangeMind={whatWouldChangeMind}
          whatChangedMindResponse={whatChangedMindResponse}
        />
      )}
    </section>
  );
}

function ExploringContext({
  signals,
  onChatAbout,
}: {
  signals: CaseHomeSignal[];
  onChatAbout?: (payload: ChatAboutPayload) => void;
}) {
  return (
    <>
      <div>
        <SectionTitle>Emerging Signals</SectionTitle>
        {signals.length === 0 ? (
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Chat with your case to surface signals and insights.
          </p>
        ) : (
          <div className="space-y-2">
            {signals.map(signal => (
              <div
                key={signal.id}
                className="group flex items-start gap-2 p-3 rounded-lg border border-neutral-200/80 dark:border-neutral-800/80 bg-white dark:bg-neutral-900/50"
              >
                <SignalTypeIcon type={signal.type} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-neutral-700 dark:text-neutral-300">
                    {signal.text}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-neutral-400 dark:text-neutral-500 uppercase">
                      {signal.type}
                    </span>
                    <span className={cn(
                      'text-[10px] px-1.5 py-0.5 rounded-full',
                      signal.temperature === 'hot'
                        ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                        : signal.temperature === 'warm'
                          ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'
                          : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400'
                    )}>
                      {signal.temperature}
                    </span>
                  </div>
                </div>
                {onChatAbout && (
                  <button
                    onClick={() => onChatAbout({ text: `Let's explore this signal further: "${signal.text}"`, source_type: 'signal', source_id: signal.id })}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 shrink-0"
                    title="Discuss in chat"
                  >
                    <ChatBubbleIcon className="w-4 h-4 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function InvestigatingContext({
  assumptions,
  assumptionSummary,
  onUpdateAssumption,
  onChatAbout,
}: {
  assumptions: PlanAssumption[];
  assumptionSummary: { untested: number; confirmed: number; challenged: number; refuted: number; total: number };
  onUpdateAssumption?: (assumptionId: string, newStatus: string) => void;
  onChatAbout?: (payload: ChatAboutPayload) => void;
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (assumptions.length === 0) {
    return (
      <div>
        <SectionTitle>Assumption Tracker</SectionTitle>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          No assumptions to track yet.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <SectionTitle noMargin>Assumption Tracker</SectionTitle>
        <div className="flex items-center gap-2 text-[10px]">
          {assumptionSummary.confirmed > 0 && (
            <span className="text-emerald-600 dark:text-emerald-400">
              {assumptionSummary.confirmed} confirmed
            </span>
          )}
          {assumptionSummary.challenged > 0 && (
            <span className="text-amber-600 dark:text-amber-400">
              {assumptionSummary.challenged} challenged
            </span>
          )}
          {assumptionSummary.untested > 0 && (
            <span className="text-neutral-500 dark:text-neutral-400">
              {assumptionSummary.untested} untested
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2">
        {assumptions.map(a => (
          <div
            key={a.id}
            className={cn(
              'rounded-lg border transition-colors',
              a.status === 'confirmed' && 'border-emerald-200 dark:border-emerald-800/50 bg-emerald-50/50 dark:bg-emerald-900/10',
              a.status === 'challenged' && 'border-amber-200 dark:border-amber-800/50 bg-amber-50/50 dark:bg-amber-900/10',
              a.status === 'refuted' && 'border-red-200 dark:border-red-800/50 bg-red-50/50 dark:bg-red-900/10',
              a.status === 'untested' && 'border-neutral-200/80 dark:border-neutral-800/80 bg-white dark:bg-neutral-900/50',
            )}
          >
            <div className="group flex items-start gap-2 p-3">
              {/* Clickable status badge */}
              <button
                onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
                className="shrink-0 mt-0.5 transition-transform hover:scale-110"
                title="Change status"
              >
                <AssumptionBadge status={a.status} />
              </button>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-neutral-700 dark:text-neutral-300">{a.text}</p>
                {a.evidence_summary && (
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                    {a.evidence_summary}
                  </p>
                )}
                {a.test_strategy && a.status === 'untested' && (
                  <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1 italic">
                    Test: {a.test_strategy}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {onChatAbout && (
                  <button
                    onClick={() => onChatAbout({ text: `Tell me more about the assumption: "${a.text}". What evidence do we have?`, source_type: 'assumption', source_id: a.id })}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800"
                    title="Discuss in chat"
                  >
                    <ChatBubbleIcon className="w-4 h-4 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300" />
                  </button>
                )}
                <span className={cn(
                  'text-[10px] px-1.5 py-0.5 rounded-full uppercase',
                  a.risk_level === 'high' && 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
                  a.risk_level === 'medium' && 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400',
                  a.risk_level === 'low' && 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400',
                )}>
                  {a.risk_level}
                </span>
              </div>
            </div>

            {/* Inline status selector */}
            <AnimatePresence>
              {expandedId === a.id && onUpdateAssumption && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className="overflow-hidden"
                >
                  <div className="flex items-center gap-1.5 px-3 pb-3 pt-1">
                    <span className="text-[10px] text-neutral-500 dark:text-neutral-400 mr-1">Set status:</span>
                    {ASSUMPTION_STATUSES.map(status => (
                      <button
                        key={status}
                        onClick={() => {
                          onUpdateAssumption(a.id, status);
                          setExpandedId(null);
                        }}
                        className={cn(
                          'text-[10px] px-2 py-1 rounded-full transition-colors capitalize',
                          a.status === status
                            ? 'ring-2 ring-accent-400 ring-offset-1 dark:ring-offset-neutral-900'
                            : '',
                          status === 'untested' && 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 hover:bg-neutral-200 dark:hover:bg-neutral-700',
                          status === 'confirmed' && 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-200 dark:hover:bg-emerald-900/50',
                          status === 'challenged' && 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 hover:bg-amber-200 dark:hover:bg-amber-900/50',
                          status === 'refuted' && 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50',
                        )}
                      >
                        {status}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </div>
  );
}

function SynthesizingContext({
  criteria,
  criteriaProgress,
  assumptions,
  assumptionSummary,
  onUpdateCriterion,
  onChatAbout,
  premortemText,
  caseId,
  whatWouldChangeMind,
  whatChangedMindResponse,
}: {
  criteria: DecisionCriterion[];
  criteriaProgress: { met: number; total: number };
  assumptions: PlanAssumption[];
  assumptionSummary: { untested: number; confirmed: number; challenged: number; refuted: number; total: number };
  onUpdateCriterion?: (criterionId: string, isMet: boolean) => void;
  onChatAbout?: (payload: ChatAboutPayload) => void;
  premortemText?: string;
  caseId?: string;
  whatWouldChangeMind?: string;
  whatChangedMindResponse?: string;
}) {
  return (
    <>
      {/* "What would change your mind" resurface card */}
      {caseId && whatWouldChangeMind && (
        <WhatChangedMindCard
          caseId={caseId}
          originalText={whatWouldChangeMind}
          existingResponse={whatChangedMindResponse}
        />
      )}

      {/* Decision Criteria */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <SectionTitle noMargin>Decision Criteria</SectionTitle>
          <span className="text-xs text-neutral-500 dark:text-neutral-400">
            {criteriaProgress.met}/{criteriaProgress.total} met
          </span>
        </div>

        {criteria.length === 0 ? (
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            No decision criteria defined yet.
          </p>
        ) : (
          <div className="space-y-1.5">
            {criteria.map(c => (
              <div
                key={c.id}
                className={cn(
                  'group flex items-start gap-2.5 p-2.5 rounded-lg transition-colors',
                  c.is_met
                    ? 'bg-emerald-50/50 dark:bg-emerald-900/10'
                    : 'bg-neutral-50/50 dark:bg-neutral-900/30'
                )}
              >
                {/* Clickable toggle */}
                <button
                  onClick={() => onUpdateCriterion?.(c.id, !c.is_met)}
                  className={cn(
                    'mt-0.5 shrink-0 transition-colors',
                    c.is_met
                      ? 'text-emerald-500 hover:text-emerald-600'
                      : 'text-neutral-300 dark:text-neutral-600 hover:text-neutral-400 dark:hover:text-neutral-500'
                  )}
                  title={c.is_met ? 'Mark as not met' : 'Mark as met'}
                >
                  {c.is_met ? (
                    <CheckCircleSmall className="w-4 h-4" />
                  ) : (
                    <CircleSmall className="w-4 h-4" />
                  )}
                </button>
                <span className={cn(
                  'text-sm flex-1',
                  c.is_met
                    ? 'text-emerald-700 dark:text-emerald-300'
                    : 'text-neutral-700 dark:text-neutral-300'
                )}>
                  {c.text}
                </span>
                {onChatAbout && (
                  <button
                    onClick={() => onChatAbout({ text: `How can we verify whether this criterion is met: "${c.text}"?`, source_type: 'criterion', source_id: c.id })}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 shrink-0"
                    title="Discuss in chat"
                  >
                    <ChatBubbleIcon className="w-4 h-4 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Progress bar */}
        {criteriaProgress.total > 0 && (
          <div className="mt-3">
            <div className="h-1.5 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                style={{ width: `${(criteriaProgress.met / criteriaProgress.total) * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Assumption summary (compact) */}
      {assumptions.length > 0 && (
        <div>
          <SectionTitle>Assumptions</SectionTitle>
          <div className="grid grid-cols-4 gap-2">
            <MetricCard
              label="Confirmed"
              value={assumptionSummary.confirmed}
              color="emerald"
            />
            <MetricCard
              label="Challenged"
              value={assumptionSummary.challenged}
              color="amber"
            />
            <MetricCard
              label="Refuted"
              value={assumptionSummary.refuted}
              color="red"
            />
            <MetricCard
              label="Untested"
              value={assumptionSummary.untested}
              color="neutral"
            />
          </div>
        </div>
      )}

      {/* Section Judgment Summary */}
      {caseId && (
        <div>
          <SectionTitle>Your Judgment vs Evidence</SectionTitle>
          <JudgmentSummaryCard caseId={caseId} />
        </div>
      )}

      {/* Premortem */}
      {premortemText && (
        <div>
          <SectionTitle>Premortem</SectionTitle>
          <div className="p-3 rounded-lg border border-amber-200/80 dark:border-amber-800/80 bg-amber-50/50 dark:bg-amber-900/20">
            <p className="text-sm text-amber-800 dark:text-amber-200 italic">
              &ldquo;{premortemText}&rdquo;
            </p>
            <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
              Your imagined reason for failure
            </p>
          </div>
        </div>
      )}
    </>
  );
}

// ─── Shared sub-components ────────────────────────────────

function SectionTitle({ children, noMargin }: { children: React.ReactNode; noMargin?: boolean }) {
  return (
    <h2 className={cn(
      'text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide',
      !noMargin && 'mb-3'
    )}>
      {children}
    </h2>
  );
}

function AssumptionBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; label: string }> = {
    untested: { color: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500', label: 'untested' },
    confirmed: { color: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400', label: 'confirmed' },
    challenged: { color: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400', label: 'challenged' },
    refuted: { color: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400', label: 'refuted' },
  };

  const c = config[status] ?? config.untested;
  return (
    <span className={cn('text-[10px] px-1.5 py-0.5 rounded-full uppercase shrink-0 mt-0.5', c.color)}>
      {c.label}
    </span>
  );
}

function MetricCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colorMap: Record<string, string> = {
    emerald: 'text-emerald-600 dark:text-emerald-400',
    amber: 'text-amber-600 dark:text-amber-400',
    red: 'text-red-600 dark:text-red-400',
    neutral: 'text-neutral-500 dark:text-neutral-400',
  };

  return (
    <div className="text-center p-2 rounded-lg bg-neutral-50/50 dark:bg-neutral-900/30">
      <div className={cn('text-lg font-semibold', colorMap[color] ?? colorMap.neutral)}>
        {value}
      </div>
      <div className="text-[10px] text-neutral-500 dark:text-neutral-400 uppercase">
        {label}
      </div>
    </div>
  );
}

function SignalTypeIcon({ type }: { type: string }) {
  return (
    <span className="w-5 h-5 rounded-full bg-accent-100 dark:bg-accent-900/30 flex items-center justify-center text-[10px] text-accent-600 dark:text-accent-400 shrink-0 mt-0.5">
      {type === 'tension' ? '⚡' : type === 'blind_spot' ? '🔍' : type === 'evidence' ? '📎' : '💡'}
    </span>
  );
}

