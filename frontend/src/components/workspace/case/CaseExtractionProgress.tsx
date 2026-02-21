/**
 * CaseExtractionProgress — Progressive loading indicator for case extraction pipeline.
 *
 * Shows a phase-by-phase progress view as the extraction pipeline runs:
 *   retrieving → extracting → integrating → analyzing → complete
 *
 * Uses SSE streaming for real-time updates, with polling fallback only when
 * SSE connection has not been established or has failed.
 * After completion, shows a compact analysis summary panel.
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { casesAPI } from '@/lib/api/cases';
import { Spinner } from '@/components/ui/spinner';
import { CheckCircleSmall, AlertIcon, SearchIcon, SparklesIcon, ChatBubbleIcon } from '@/components/ui/icons';
import type { ExtractionPhase, ExtractionStatus, CaseAnalysis } from '@/lib/types/case-extraction';
import type { ChatAboutPayload } from './CaseHome';

// ── Phase definitions ──

interface PhaseInfo {
  key: ExtractionPhase;
  label: string;
  description: string;
}

const EXTRACTION_PHASES: PhaseInfo[] = [
  { key: 'retrieving', label: 'Retrieving', description: 'Finding relevant document chunks...' },
  { key: 'extracting', label: 'Extracting', description: 'Extracting claims, evidence, and assumptions...' },
  { key: 'integrating', label: 'Integrating', description: 'Connecting nodes into your knowledge graph...' },
  { key: 'analyzing', label: 'Analyzing', description: 'Detecting blind spots and assessing readiness...' },
];

const PHASE_ORDER: ExtractionPhase[] = ['pending', 'retrieving', 'extracting', 'integrating', 'analyzing', 'complete'];

function phaseIndex(phase: ExtractionPhase): number {
  const idx = PHASE_ORDER.indexOf(phase);
  return idx >= 0 ? idx : -1;
}

// ── Props ──

interface CaseExtractionProgressProps {
  caseId: string;
  initialStatus?: ExtractionStatus;
  onComplete?: () => void;
  onChatAbout?: (payload: ChatAboutPayload) => void;
  onViewGraph?: () => void;
  className?: string;
}

export function CaseExtractionProgress({
  caseId,
  initialStatus,
  onComplete,
  onChatAbout,
  onViewGraph,
  className,
}: CaseExtractionProgressProps) {
  const [status, setStatus] = useState<ExtractionStatus | null>(initialStatus ?? null);
  const [analysis, setAnalysis] = useState<CaseAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const completeFired = useRef(false);
  const sseConnected = useRef(false);
  const mountedRef = useRef(true);

  // Stabilize onComplete to avoid re-triggering effects on identity change
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const currentPhase = status?.extraction_status ?? 'none';
  const isRunning = ['pending', 'retrieving', 'extracting', 'integrating', 'analyzing'].includes(currentPhase);
  const isComplete = currentPhase === 'complete';
  const isFailed = currentPhase === 'failed';

  // Track mount state for safe async state updates
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // SSE streaming for real-time progress
  useEffect(() => {
    if (!isRunning) return;

    sseConnected.current = false;
    const abortController = new AbortController();

    casesAPI.streamExtraction(
      caseId,
      (event) => {
        sseConnected.current = true;
        if (!mountedRef.current) return;

        if (event.event === 'status' || event.event === 'progress') {
          const patch = event.data as Partial<ExtractionStatus>;
          setStatus(prev => ({
            ...(prev ?? { extraction_status: 'pending' as ExtractionPhase }),
            ...patch,
          }));
        } else if (event.event === 'completed') {
          const patch = event.data as Partial<ExtractionStatus>;
          setStatus(prev => ({
            ...(prev ?? { extraction_status: 'complete' as ExtractionPhase }),
            extraction_status: 'complete' as ExtractionPhase,
            ...patch,
          }));
        } else if (event.event === 'failed') {
          setStatus(prev => ({
            ...(prev ?? { extraction_status: 'failed' as ExtractionPhase }),
            extraction_status: 'failed' as ExtractionPhase,
            extraction_error: (event.data?.error as string) ?? undefined,
          }));
          setError(event.data?.error ?? 'Extraction failed');
        }
      },
      abortController.signal,
    ).catch(() => {
      // Stream ended or failed — polling fallback will handle it
      sseConnected.current = false;
    });

    return () => abortController.abort();
  }, [caseId, isRunning]);

  // Polling fallback — only polls when SSE is not connected
  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(async () => {
      // Skip polling if SSE is actively connected
      if (sseConnected.current) return;

      try {
        const fresh = await casesAPI.getExtractionStatus(caseId);
        if (mountedRef.current) {
          setStatus(fresh);
        }
      } catch {
        // Ignore polling errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [caseId, isRunning]);

  // Fetch analysis when complete
  useEffect(() => {
    if (!isComplete) return;

    casesAPI.getAnalysis(caseId)
      .then((result) => {
        if (mountedRef.current) setAnalysis(result);
      })
      .catch(() => {
        // Analysis may not be ready yet
      });

    if (!completeFired.current) {
      completeFired.current = true;
      onCompleteRef.current?.();
    }
  }, [caseId, isComplete]);

  // Re-extract handler
  const handleReExtract = useCallback(async () => {
    setError(null);
    setAnalysis(null);
    completeFired.current = false;
    setStatus({
      extraction_status: 'pending',
      extraction_started_at: undefined,
      extraction_completed_at: undefined,
      extraction_error: undefined,
      extraction_result: undefined,
    });
    try {
      await casesAPI.reExtract(caseId);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to start re-extraction';
      setError(message);
    }
  }, [caseId]);

  // Nothing to show
  if (currentPhase === 'none' && !analysis) return null;

  return (
    <div className={cn('space-y-4', className)} role="region" aria-label="Extraction progress">
      {/* Progress phases — shown while running or just completed */}
      {(isRunning || isComplete) && (
        <div className="rounded-lg border border-accent-200/60 dark:border-accent-800/40 bg-accent-50/30 dark:bg-accent-900/10 p-4">
          <div className="flex items-center gap-2 mb-3">
            {isRunning ? (
              <Spinner size="sm" className="text-accent-600 dark:text-accent-400" />
            ) : (
              <CheckCircleSmall className="w-4 h-4 text-success-500" />
            )}
            <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
              {isRunning ? 'Analyzing your decision...' : 'Analysis complete'}
            </span>
          </div>

          <div className="space-y-2" role="list" aria-label="Extraction phases">
            {EXTRACTION_PHASES.map((phase) => {
              const idx = phaseIndex(phase.key);
              const currentIdx = phaseIndex(currentPhase);
              const isDone = currentIdx > idx;
              const isActive = phase.key === currentPhase;

              return (
                <div key={phase.key} className="flex items-center gap-2.5" role="listitem">
                  <span className="shrink-0 w-4 h-4 flex items-center justify-center">
                    {isDone ? (
                      <CheckCircleSmall className="w-4 h-4 text-success-500" />
                    ) : isActive ? (
                      <Spinner size="xs" className="text-accent-600 dark:text-accent-400" />
                    ) : (
                      <div className="w-2 h-2 rounded-full bg-neutral-200 dark:bg-neutral-700" />
                    )}
                  </span>
                  <span className={cn(
                    'text-sm',
                    isDone && 'text-neutral-500 dark:text-neutral-400',
                    isActive && 'text-accent-700 dark:text-accent-300 font-medium',
                    !isDone && !isActive && 'text-neutral-400 dark:text-neutral-500',
                  )}>
                    {isActive ? phase.description : phase.label}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Result summary after completion */}
          {isComplete && status?.extraction_result && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-3 pt-3 border-t border-accent-200/50 dark:border-accent-800/30"
            >
              <div className="flex items-center gap-4 text-xs text-neutral-500 dark:text-neutral-400">
                <span>{status.extraction_result.node_count} nodes extracted</span>
                <span>{status.extraction_result.edge_count} relationships found</span>
                <span>from {status.extraction_result.chunk_count} chunks</span>
              </div>
              {onViewGraph && status.extraction_result.node_count > 0 && (
                <button
                  onClick={onViewGraph}
                  className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-accent-600 dark:text-accent-400 hover:text-accent-700 dark:hover:text-accent-300 transition-colors"
                >
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="18" cy="5" r="3" />
                    <circle cx="6" cy="12" r="3" />
                    <circle cx="18" cy="19" r="3" />
                    <path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" />
                  </svg>
                  View Investigation Graph ({status.extraction_result.node_count} nodes)
                </button>
              )}
            </motion.div>
          )}
        </div>
      )}

      {/* Error state */}
      {isFailed && (
        <div className="rounded-lg border border-error-200 dark:border-error-800 bg-error-50/50 dark:bg-error-900/20 p-4" role="alert">
          <div className="flex items-start gap-2">
            <AlertIcon className="w-4 h-4 text-error-500 mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="text-sm text-error-700 dark:text-error-300">
                Extraction failed{error ? `: ${error}` : ''}
              </p>
              <button
                onClick={handleReExtract}
                className="text-xs text-error-600 dark:text-error-400 hover:underline mt-1"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Analysis summary — shown after completion */}
      <AnimatePresence>
        {analysis && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
          >
            <AnalysisSummary
              analysis={analysis}
              onChatAbout={onChatAbout}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Analysis Summary Panel ──

function AnalysisSummary({
  analysis,
  onChatAbout,
}: {
  analysis: CaseAnalysis;
  onChatAbout?: (payload: ChatAboutPayload) => void;
}) {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const { readiness, blind_spots, assumption_assessment, key_tensions, evidence_coverage } = analysis;

  const loadBearingUntested = assumption_assessment.filter(a => a.load_bearing && a.supporting_evidence === 0);

  return (
    <div className="rounded-lg border border-neutral-200/80 dark:border-neutral-800/80 bg-white dark:bg-neutral-900/50 divide-y divide-neutral-100 dark:divide-neutral-800/50">
      {/* Decision Readiness */}
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={cn(
              'w-2.5 h-2.5 rounded-full',
              readiness.ready ? 'bg-success-500' : readiness.confidence >= 50 ? 'bg-warning-500' : 'bg-error-500'
            )} />
            <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
              Decision Readiness
            </span>
          </div>
          <span className={cn(
            'text-xs px-2 py-0.5 rounded-full',
            readiness.ready
              ? 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300'
              : 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300'
          )}>
            {readiness.confidence}% confidence
          </span>
        </div>
        {readiness.issues.length > 0 && (
          <ul className="mt-2 space-y-1">
            {readiness.issues.slice(0, 3).map((issue, i) => (
              <li key={i} className="text-xs text-neutral-500 dark:text-neutral-400 flex items-start gap-1.5">
                <span className="text-warning-500 mt-0.5 shrink-0">-</span>
                {issue}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Blind Spots */}
      {blind_spots.length > 0 && (
        <ExpandableSection
          id="blindspots"
          icon={<SearchIcon className="w-4 h-4 text-warning-500" />}
          title="Blind Spots"
          count={blind_spots.length}
          isExpanded={expandedSection === 'blindspots'}
          onToggle={() => setExpandedSection(expandedSection === 'blindspots' ? null : 'blindspots')}
        >
          <ul className="mt-2 space-y-2">
            {blind_spots.map((bs, i) => (
              <li key={i} className="flex items-start gap-2 group">
                <span className={cn(
                  'text-xs px-1 py-0.5 rounded uppercase mt-0.5 shrink-0',
                  bs.severity === 'high' && 'bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400',
                  bs.severity === 'medium' && 'bg-warning-100 dark:bg-warning-900/30 text-warning-600 dark:text-warning-400',
                  bs.severity === 'low' && 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500',
                )}>
                  {bs.severity}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-neutral-700 dark:text-neutral-300">{bs.description}</p>
                  <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">{bs.suggested_action}</p>
                </div>
                {onChatAbout && (
                  <ChatButton
                    onClick={() => onChatAbout({
                      text: `I'd like to explore this blind spot: "${bs.description}". ${bs.suggested_action}`,
                      source_type: 'assumption',
                      source_id: `blindspot-${i}`,
                    })}
                  />
                )}
              </li>
            ))}
          </ul>
        </ExpandableSection>
      )}

      {/* Load-bearing Untested Assumptions */}
      {loadBearingUntested.length > 0 && (
        <ExpandableSection
          id="assumptions"
          icon={<AlertIcon className="w-4 h-4 text-error-500" />}
          title="Untested Load-bearing Assumptions"
          count={loadBearingUntested.length}
          countClassName="text-error-500"
          isExpanded={expandedSection === 'assumptions'}
          onToggle={() => setExpandedSection(expandedSection === 'assumptions' ? null : 'assumptions')}
        >
          <ul className="mt-2 space-y-2">
            {loadBearingUntested.map((a) => (
              <li key={a.node_id} className="flex items-start gap-2 group">
                <span className="text-xs px-1 py-0.5 rounded bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400 uppercase mt-0.5 shrink-0">
                  critical
                </span>
                <p className="text-sm text-neutral-700 dark:text-neutral-300 flex-1">{a.content}</p>
                {onChatAbout && (
                  <ChatButton
                    onClick={() => onChatAbout({
                      text: `This assumption seems load-bearing but untested: "${a.content}". How can we test it?`,
                      source_type: 'assumption',
                      source_id: a.node_id,
                    })}
                  />
                )}
              </li>
            ))}
          </ul>
        </ExpandableSection>
      )}

      {/* Key Tensions */}
      {key_tensions.length > 0 && (
        <ExpandableSection
          id="tensions"
          icon={<SparklesIcon className="w-4 h-4 text-rose-500" />}
          title="Key Tensions"
          count={key_tensions.length}
          isExpanded={expandedSection === 'tensions'}
          onToggle={() => setExpandedSection(expandedSection === 'tensions' ? null : 'tensions')}
        >
          <ul className="mt-2 space-y-2">
            {key_tensions.map((t) => (
              <li key={t.node_id} className="flex items-start gap-2 group">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-neutral-700 dark:text-neutral-300">{t.content}</p>
                  <span className="text-xs text-neutral-400 dark:text-neutral-500">
                    {t.status} - involves {t.involved_nodes.length} nodes
                  </span>
                </div>
                {onChatAbout && (
                  <ChatButton
                    onClick={() => onChatAbout({
                      text: `Help me think through this tension: "${t.content}"`,
                      source_type: 'assumption',
                      source_id: t.node_id,
                    })}
                  />
                )}
              </li>
            ))}
          </ul>
        </ExpandableSection>
      )}

      {/* Evidence Coverage */}
      <div className="p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
            Evidence Coverage
          </span>
          <span className="text-xs text-neutral-500 dark:text-neutral-400">
            {evidence_coverage.supported_claims}/{evidence_coverage.total_claims} claims supported
          </span>
        </div>
        {evidence_coverage.total_claims > 0 && (
          <div
            className="mt-2 h-1.5 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={evidence_coverage.supported_claims}
            aria-valuemin={0}
            aria-valuemax={evidence_coverage.total_claims}
            aria-label={`${evidence_coverage.supported_claims} of ${evidence_coverage.total_claims} claims supported by evidence`}
          >
            <div
              className="h-full bg-success-500 rounded-full transition-all duration-500"
              style={{
                width: `${Math.round((evidence_coverage.supported_claims / evidence_coverage.total_claims) * 100)}%`,
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Shared sub-components ──

/** Expandable section with accessible toggle button */
function ExpandableSection({
  id,
  icon,
  title,
  count,
  countClassName,
  isExpanded,
  onToggle,
  children,
}: {
  id: string;
  icon: React.ReactNode;
  title: string;
  count: number;
  countClassName?: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  const contentId = `extraction-section-${id}`;
  return (
    <div className="p-4">
      <button
        onClick={onToggle}
        aria-expanded={isExpanded}
        aria-controls={contentId}
        className="flex items-center justify-between w-full text-left"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
            {title}
          </span>
          <span className={cn('text-xs text-neutral-400 dark:text-neutral-500', countClassName)}>
            {count}
          </span>
        </div>
        <span className="text-xs text-neutral-400">
          {isExpanded ? '-' : '+'}
        </span>
      </button>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            id={contentId}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/** Chat-about button with keyboard visibility */
function ChatButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity shrink-0"
      title="Discuss in chat"
    >
      <ChatBubbleIcon className="w-4 h-4 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300" />
    </button>
  );
}
