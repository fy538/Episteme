/**
 * CaseHome — Default main content view for the case workspace.
 *
 * Three vertically stacked zones:
 *   1. StageHeader: title, position statement, stage progression dots
 *   2. InvestigationTimeline: windowed inquiry list with fade edges
 *   3. ContextPanel: stage-adaptive sections (assumptions, criteria)
 *
 * Fetches data via useCaseHome (aggregated getCaseHome endpoint).
 * Interactive: assumptions can be status-toggled, criteria toggled, items sent to chat.
 */

'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { plansAPI } from '@/lib/api/plans';
import { useCaseHome } from '@/hooks/useCaseHome';
import { useOptimisticPlanUpdate } from '@/hooks/useOptimisticPlanUpdate';
import type { CaseStage, CaseHomeInquiry, PlanAssumption, DecisionCriterion } from '@/lib/types/plan';
import { PremortemModal } from '@/components/cases/PremortemModal';
import { ResolutionTypePicker } from '@/components/cases/ResolutionTypePicker';
import { DecisionSummaryView } from '@/components/cases/DecisionSummaryView';
import { OutcomeCheckBanner, useOutcomeCheckDismiss } from '@/components/cases/OutcomeCheckBanner';
import { WhatChangedMindCard } from '@/components/cases/WhatChangedMindCard';
import { JudgmentSummaryCard } from '@/components/cases/JudgmentSummaryCard';
import { CheckCircleSmall, CircleSmall, SpinnerSmall, ChatBubbleIcon } from '@/components/ui/icons';
import { CaseExtractionProgress } from './CaseExtractionProgress';
import { casesAPI } from '@/lib/api/cases';
import type { DecisionRecord } from '@/lib/types/case';
import { ReadinessChecklist } from '@/components/readiness';
import type { ReadinessChecklistItemData, ChecklistProgress } from '@/components/readiness';
import type { ExtractionPhase } from '@/lib/types/case-extraction';

export interface ChatAboutPayload {
  text: string;
  source_type: 'assumption' | 'criterion' | 'inquiry';
  source_id: string;
}

interface CaseHomeProps {
  caseId: string;
  projectId?: string;
  onViewInquiry: (inquiryId: string) => void;
  onViewAll: () => void;
  onChatAbout?: (payload: ChatAboutPayload) => void;
  onGeneratePlan?: () => void;
  onViewGraph?: () => void;
  className?: string;
}

export function CaseHome({ caseId, projectId, onViewInquiry, onViewAll, onChatAbout, onGeneratePlan, onViewGraph, className }: CaseHomeProps) {
  const queryClient = useQueryClient();
  const {
    data,
    isLoading,
    stage,
    assumptionSummary,
    criteriaProgress,
  } = useCaseHome(caseId);

  const [showPremortem, setShowPremortem] = useState(false);
  const [decision, setDecision] = useState<DecisionRecord | null>(null);
  const { isDismissed: bannerDismissed, dismiss: dismissBanner } = useOutcomeCheckDismiss(caseId);

  // Fetch decision record when case is decided
  useEffect(() => {
    if (data?.case.status === 'decided') {
      casesAPI.getDecision(caseId)
        .then(setDecision)
        .catch(() => {}); // Silently fail — decision might not exist yet
    }
  }, [data?.case.status, caseId]);

  // Handle auto-resolution from ResolutionTypePicker
  const handleResolved = useCallback((record: DecisionRecord) => {
    setDecision(record);
    queryClient.invalidateQueries({ queryKey: ['case-home', caseId] });
  }, [queryClient, caseId]);

  const handleAddOutcomeNote = useCallback(async (note: string, sentiment: string) => {
    const updated = await casesAPI.addOutcomeNote(caseId, {
      note,
      sentiment: sentiment as 'positive' | 'neutral' | 'negative',
    });
    setDecision(updated);
  }, [caseId]);

  // Stable callback for extraction completion — invalidates case + graph queries
  const handleExtractionComplete = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['case-home', caseId] });
    if (projectId) {
      queryClient.invalidateQueries({ queryKey: ['project-graph', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project-summary', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project-deltas', projectId] });
    }
  }, [queryClient, caseId, projectId]);

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
    const isFirstVisit = !hasInquiries;

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
                { step: '1', title: 'Chat about your decision', desc: 'Use the chat panel to explore your thinking. Episteme will help surface assumptions and questions.' },
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

        {/* Extraction Progress — may run before plan exists */}
        {data.case.metadata?.extraction_status &&
          data.case.metadata.extraction_status !== 'none' && (
          <CaseExtractionProgress
            caseId={caseId}
            initialStatus={{
              extraction_status: data.case.metadata.extraction_status as ExtractionPhase,
              extraction_started_at: data.case.metadata.extraction_started_at,
              extraction_completed_at: data.case.metadata.extraction_completed_at,
              extraction_error: data.case.metadata.extraction_error,
              extraction_result: data.case.metadata.extraction_result,
            }}
            onComplete={handleExtractionComplete}
            onChatAbout={onChatAbout}
            onViewGraph={onViewGraph}
          />
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
                <Button
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
                >
                  Retry
                </Button>
              )}
            </>
          ) : autoGenInProgress ? (
            <>
              <div className="w-10 h-10 mx-auto rounded-full bg-accent-100 dark:bg-accent-900/30 flex items-center justify-center">
                <Spinner size="md" className="text-accent-600 dark:text-accent-400" />
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
        <div className="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-3 flex items-center justify-between" role="alert">
          <p className="text-sm text-error-700 dark:text-error-300">{planError}</p>
          <Button variant="ghost" size="sm" onClick={clearPlanError} className="text-xs text-error-500 hover:text-error-700">Dismiss</Button>
        </div>
      )}

      {/* Extraction Progress — shown when case has active or completed extraction */}
      {data.case.metadata?.extraction_status &&
        data.case.metadata.extraction_status !== 'none' && (
        <CaseExtractionProgress
          caseId={caseId}
          initialStatus={{
            extraction_status: data.case.metadata.extraction_status as ExtractionPhase,
            extraction_started_at: data.case.metadata.extraction_started_at,
            extraction_completed_at: data.case.metadata.extraction_completed_at,
            extraction_error: data.case.metadata.extraction_error,
            extraction_result: data.case.metadata.extraction_result,
          }}
          onComplete={handleExtractionComplete}
          onChatAbout={onChatAbout}
          onViewGraph={onViewGraph}
        />
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

      {/* Zone 3: Context Panel or Decision Summary */}
      {data.case.status === 'decided' && decision ? (
        <>
          {/* Outcome check reminder banner */}
          {decision.outcome_check_date && !bannerDismissed && (
            <OutcomeCheckBanner
              caseTitle={data.case.title}
              outcomeCheckDate={decision.outcome_check_date}
              onAddNote={() => {
                // Scroll to the outcome timeline (it's in DecisionSummaryView)
                const el = document.querySelector('[data-outcome-timeline]');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }}
              onDismiss={dismissBanner}
            />
          )}
          <DecisionSummaryView
            decision={decision}
            assumptions={content?.assumptions ?? []}
            onAddOutcomeNote={handleAddOutcomeNote}
          />
        </>
      ) : (
        <ContextPanel
          stage={stage}
          stageRationale={content?.stage_rationale ?? ''}
          assumptions={content?.assumptions ?? []}
          criteria={content?.decision_criteria ?? []}
          assumptionSummary={assumptionSummary}
          criteriaProgress={criteriaProgress}
          onUpdateAssumption={handleUpdateAssumption}
          onUpdateCriterion={handleUpdateCriterion}
          onChatAbout={onChatAbout}
          premortemText={data.case.premortem_text ?? ''}
          caseId={caseId}
          whatWouldChangeMind={data.case.what_would_change_mind ?? ''}
          whatChangedMindResponse={data.case.what_changed_mind_response ?? ''}
          isReady={stage === 'ready'}
          onResolved={handleResolved}
        />
      )}

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
                  isCompleted ? 'bg-success-400' : 'bg-neutral-200 dark:bg-neutral-700'
                )} />
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => canTransition && onStageChange?.(s.key)}
                disabled={!canTransition}
                className={cn(
                  'flex items-center gap-1.5 h-auto px-1 py-0',
                  canTransition
                    ? 'cursor-pointer hover:opacity-70'
                    : 'cursor-default'
                )}
                title={canTransition ? `Move to ${s.label}` : undefined}
              >
                <div className={cn(
                  'w-2.5 h-2.5 rounded-full border-2 transition-colors',
                  isCompleted && 'border-success-500 bg-success-500',
                  isCurrent && 'border-accent-500 bg-accent-500',
                  !isCompleted && !isCurrent && 'border-neutral-300 dark:border-neutral-600 bg-transparent'
                )} />
                <span className={cn(
                  'text-xs',
                  isCurrent
                    ? 'text-accent-600 dark:text-accent-400 font-medium'
                    : isCompleted
                      ? 'text-success-600 dark:text-success-400'
                      : 'text-neutral-400 dark:text-neutral-500'
                )}>
                  {s.label}
                </span>
              </Button>
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

      <Button
        variant="ghost"
        size="sm"
        onClick={onViewAll}
        className="text-xs text-accent-600 dark:text-accent-400 hover:underline mt-2 px-0 h-auto"
      >
        View all research →
      </Button>
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
    <Button
      variant="ghost"
      onClick={onClick}
      className="flex items-start gap-3 w-full justify-start text-left p-3 h-auto rounded-none hover:bg-neutral-50 dark:hover:bg-neutral-800/30"
    >
      {/* Status icon */}
      <span className="mt-0.5 shrink-0">
        {isResolved ? (
          <CheckCircleSmall className="w-4 h-4 text-success-500" />
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
            <span className="text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 px-1.5 py-0.5 rounded-full shrink-0">
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
          <p className="text-xs text-success-600 dark:text-success-400 mt-0.5 line-clamp-1">
            {inquiry.conclusion}
          </p>
        )}
      </div>
    </Button>
  );
}

// ─── Zone 3: Context Panel (stage-adaptive) ────────────────

const ASSUMPTION_STATUSES = ['untested', 'confirmed', 'challenged', 'refuted'] as const;

function ContextPanel({
  stage,
  stageRationale,
  assumptions,
  criteria,
  assumptionSummary,
  criteriaProgress,
  onUpdateAssumption,
  onUpdateCriterion,
  onChatAbout,
  premortemText,
  caseId,
  whatWouldChangeMind,
  whatChangedMindResponse,
  isReady,
  onResolved,
}: {
  stage: CaseStage;
  stageRationale: string;
  assumptions: PlanAssumption[];
  criteria: DecisionCriterion[];
  assumptionSummary: { untested: number; confirmed: number; challenged: number; refuted: number; total: number };
  criteriaProgress: { met: number; total: number };
  onUpdateAssumption?: (assumptionId: string, newStatus: string) => void;
  onUpdateCriterion?: (criterionId: string, isMet: boolean) => void;
  onChatAbout?: (payload: ChatAboutPayload) => void;
  premortemText?: string;
  caseId?: string;
  whatWouldChangeMind?: string;
  whatChangedMindResponse?: string;
  isReady?: boolean;
  onResolved?: (record: DecisionRecord) => void;
}) {
  return (
    <section className="space-y-6">
      {/* Stage-adaptive content */}
      {stage === 'exploring' && (
        <ExploringContext onChatAbout={onChatAbout} />
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
          isReady={isReady}
          onResolved={onResolved}
        />
      )}

      {/* Subtle resolve picker — only at exploring stage for shelve/reframe.
          At investigating, users should focus on testing assumptions.
          At synthesizing/ready, the prominent picker is shown inside SynthesizingContext. */}
      {caseId && stage === 'exploring' && (
        <div className="pt-2 border-t border-neutral-100 dark:border-neutral-800">
          <ResolutionTypePicker caseId={caseId} onResolved={onResolved} isProminent={false} />
        </div>
      )}
    </section>
  );
}

function ExploringContext({
  onChatAbout,
}: {
  onChatAbout?: (payload: ChatAboutPayload) => void;
}) {
  return (
    <>
      <div>
        <SectionTitle>Exploring</SectionTitle>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Chat with your case to explore your thinking and surface assumptions.
        </p>
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
        <div className="flex items-center gap-2 text-xs">
          {assumptionSummary.confirmed > 0 && (
            <span className="text-success-600 dark:text-success-400">
              {assumptionSummary.confirmed} confirmed
            </span>
          )}
          {assumptionSummary.challenged > 0 && (
            <span className="text-warning-600 dark:text-warning-400">
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
              a.status === 'confirmed' && 'border-success-200 dark:border-success-800/50 bg-success-50/50 dark:bg-success-900/10',
              a.status === 'challenged' && 'border-warning-200 dark:border-warning-800/50 bg-warning-50/50 dark:bg-warning-900/10',
              a.status === 'refuted' && 'border-error-200 dark:border-error-800/50 bg-error-50/50 dark:bg-error-900/10',
              a.status === 'untested' && 'border-neutral-200/80 dark:border-neutral-800/80 bg-white dark:bg-neutral-900/50',
            )}
          >
            <div className="group flex items-start gap-2 p-3">
              {/* Clickable status badge */}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
                className="shrink-0 mt-0.5 h-auto w-auto hover:scale-110"
                title="Change status"
              >
                <AssumptionBadge status={a.status} />
              </Button>
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
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onChatAbout({ text: `Tell me more about the assumption: "${a.text}". What evidence do we have?`, source_type: 'assumption', source_id: a.id })}
                    className="opacity-0 group-hover:opacity-100 transition-opacity h-7 w-7"
                    title="Discuss in chat"
                  >
                    <ChatBubbleIcon className="w-4 h-4 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300" />
                  </Button>
                )}
                <span className={cn(
                  'text-xs px-1.5 py-0.5 rounded-full uppercase',
                  a.risk_level === 'high' && 'bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400',
                  a.risk_level === 'medium' && 'bg-warning-100 dark:bg-warning-900/30 text-warning-600 dark:text-warning-400',
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
                    <span className="text-xs text-neutral-500 dark:text-neutral-400 mr-1">Set status:</span>
                    {ASSUMPTION_STATUSES.map(status => (
                      <Button
                        key={status}
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          onUpdateAssumption(a.id, status);
                          setExpandedId(null);
                        }}
                        className={cn(
                          'text-xs px-2 py-1 h-auto rounded-full capitalize',
                          a.status === status
                            ? 'ring-2 ring-accent-400 ring-offset-1 dark:ring-offset-neutral-900'
                            : '',
                          status === 'untested' && 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 hover:bg-neutral-200 dark:hover:bg-neutral-700',
                          status === 'confirmed' && 'bg-success-100 dark:bg-success-900/30 text-success-600 dark:text-success-400 hover:bg-success-200 dark:hover:bg-success-900/50',
                          status === 'challenged' && 'bg-warning-100 dark:bg-warning-900/30 text-warning-600 dark:text-warning-400 hover:bg-warning-200 dark:hover:bg-warning-900/50',
                          status === 'refuted' && 'bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400 hover:bg-error-200 dark:hover:bg-error-900/50',
                        )}
                      >
                        {status}
                      </Button>
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
  isReady,
  onResolved,
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
  isReady?: boolean;
  onResolved?: (record: DecisionRecord) => void;
}) {
  // Inline readiness checklist data loading
  const [checklistItems, setChecklistItems] = useState<ReadinessChecklistItemData[]>([]);
  const [checklistProgress, setChecklistProgress] = useState<ChecklistProgress>({
    completed: 0, required: 0, required_completed: 0, total: 0,
  });
  const loadChecklist = useCallback(async () => {
    if (!caseId) return;
    try {
      const res = await fetch(`/api/cases/${caseId}/readiness-checklist/`);
      if (!res.ok) return;
      const data = await res.json();
      setChecklistItems(data.items || []);
      setChecklistProgress(data.progress || { completed: 0, required: 0, required_completed: 0, total: 0 });
    } catch { /* graceful — no checklist items generated yet */ }
  }, [caseId]);
  useEffect(() => { loadChecklist(); }, [loadChecklist]);

  return (
    <>
      {/* Readiness checklist — soft gate for decision recording */}
      {caseId && checklistItems.length > 0 && (
        <div className="mb-4">
          <ReadinessChecklist
            caseId={caseId}
            items={checklistItems}
            progress={checklistProgress}
            onRefresh={loadChecklist}
          />
        </div>
      )}

      {/* Resolve Case — prominent picker at synthesizing/ready stage */}
      {caseId && (
        <div className="p-4 rounded-lg border-2 border-accent-200 dark:border-accent-800 bg-accent-50/50 dark:bg-accent-900/10">
          {checklistProgress.required > 0 &&
           checklistProgress.required_completed < checklistProgress.required && (
            <p className="text-xs text-amber-600 dark:text-amber-400 mb-3">
              {checklistProgress.required_completed}/{checklistProgress.required} required checklist items completed
            </p>
          )}
          <ResolutionTypePicker caseId={caseId} onResolved={onResolved} isProminent />
        </div>
      )}

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
                    ? 'bg-success-50/50 dark:bg-success-900/10'
                    : 'bg-neutral-50/50 dark:bg-neutral-900/30'
                )}
              >
                {/* Clickable toggle */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onUpdateCriterion?.(c.id, !c.is_met)}
                  className={cn(
                    'mt-0.5 shrink-0 h-auto w-auto',
                    c.is_met
                      ? 'text-success-500 hover:text-success-600'
                      : 'text-neutral-300 dark:text-neutral-600 hover:text-neutral-400 dark:hover:text-neutral-500'
                  )}
                  title={c.is_met ? 'Mark as not met' : 'Mark as met'}
                >
                  {c.is_met ? (
                    <CheckCircleSmall className="w-4 h-4" />
                  ) : (
                    <CircleSmall className="w-4 h-4" />
                  )}
                </Button>
                <span className={cn(
                  'text-sm flex-1',
                  c.is_met
                    ? 'text-success-700 dark:text-success-300'
                    : 'text-neutral-700 dark:text-neutral-300'
                )}>
                  {c.text}
                </span>
                {onChatAbout && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onChatAbout({ text: `How can we verify whether this criterion is met: "${c.text}"?`, source_type: 'criterion', source_id: c.id })}
                    className="opacity-0 group-hover:opacity-100 transition-opacity h-7 w-7 shrink-0"
                    title="Discuss in chat"
                  >
                    <ChatBubbleIcon className="w-4 h-4 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300" />
                  </Button>
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
                className="h-full bg-success-500 rounded-full transition-all duration-500"
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
          <div className="p-3 rounded-lg border border-warning-200/80 dark:border-warning-800/80 bg-warning-50/50 dark:bg-warning-900/20">
            <p className="text-sm text-warning-800 dark:text-warning-200 italic">
              &ldquo;{premortemText}&rdquo;
            </p>
            <p className="text-xs text-warning-600 dark:text-warning-400 mt-1">
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
    confirmed: { color: 'bg-success-100 dark:bg-success-900/30 text-success-600 dark:text-success-400', label: 'confirmed' },
    challenged: { color: 'bg-warning-100 dark:bg-warning-900/30 text-warning-600 dark:text-warning-400', label: 'challenged' },
    refuted: { color: 'bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400', label: 'refuted' },
  };

  const c = config[status] ?? config.untested;
  return (
    <span className={cn('text-xs px-1.5 py-0.5 rounded-full uppercase shrink-0 mt-0.5', c.color)}>
      {c.label}
    </span>
  );
}

function MetricCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colorMap: Record<string, string> = {
    emerald: 'text-success-600 dark:text-success-400',
    amber: 'text-warning-600 dark:text-warning-400',
    red: 'text-error-600 dark:text-error-400',
    neutral: 'text-neutral-500 dark:text-neutral-400',
  };

  return (
    <div className="text-center p-2 rounded-lg bg-neutral-50/50 dark:bg-neutral-900/30">
      <div className={cn('text-lg font-semibold', colorMap[color] ?? colorMap.neutral)}>
        {value}
      </div>
      <div className="text-xs text-neutral-500 dark:text-neutral-400 uppercase">
        {label}
      </div>
    </div>
  );
}


