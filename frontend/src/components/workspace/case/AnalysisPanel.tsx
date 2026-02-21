/**
 * AnalysisPanel — Sidebar panel for case analysis results.
 *
 * Displays analysis overlays alongside the case graph:
 *   1. Decision Readiness gauge
 *   2. Blind Spots (with severity)
 *   3. Untested Load-bearing Assumptions
 *   4. Unsupported Claims
 *   5. Key Tensions
 *
 * Clicking/hovering items highlights the relevant nodes on the graph
 * via onHighlightNodes callback.
 */

'use client';

import { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { SearchIcon, AlertIcon, SparklesIcon, WarningIcon, CloseIcon } from '@/components/ui/icons';
import type { CaseAnalysis } from '@/lib/types/case-extraction';

const EMPTY_HIGHLIGHTS: string[] = [];

interface AnalysisPanelProps {
  analysis: CaseAnalysis;
  onHighlightNodes: (nodeIds: string[]) => void;
  onClose: () => void;
}

export function AnalysisPanel({
  analysis,
  onHighlightNodes,
  onClose,
}: AnalysisPanelProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  const {
    readiness,
    blind_spots,
    assumption_assessment,
    key_tensions,
    evidence_coverage,
  } = analysis;

  // Derive untested load-bearing assumptions
  const untestedAssumptions = useMemo(
    () => assumption_assessment.filter(a => a.load_bearing && a.supporting_evidence === 0),
    [assumption_assessment],
  );

  // Derive unsupported claims
  const unsupportedClaims = useMemo(
    () => evidence_coverage.unsupported_claims ?? [],
    [evidence_coverage],
  );

  // Clear highlights when mouse leaves panel (stable ref avoids re-allocation)
  const handleMouseLeave = useCallback(() => {
    onHighlightNodes(EMPTY_HIGHLIGHTS);
  }, [onHighlightNodes]);

  // Confidence color
  const confidenceColor =
    readiness.confidence >= 80
      ? 'text-success-600 dark:text-success-400'
      : readiness.confidence >= 50
      ? 'text-warning-600 dark:text-warning-400'
      : 'text-error-600 dark:text-error-400';

  const confidenceBg =
    readiness.confidence >= 80
      ? 'bg-success-500'
      : readiness.confidence >= 50
      ? 'bg-warning-500'
      : 'bg-error-500';

  return (
    <div
      className="w-72 border-l border-neutral-200/60 dark:border-neutral-800/60 bg-white dark:bg-neutral-950 flex flex-col h-full overflow-hidden"
      onMouseLeave={handleMouseLeave}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200/60 dark:border-neutral-800/60 shrink-0">
        <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">
          Analysis
        </h3>
        <button
          onClick={onClose}
          className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
          aria-label="Close analysis panel"
        >
          <CloseIcon className="w-4 h-4" />
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto divide-y divide-neutral-100 dark:divide-neutral-800/50">
        {/* 1. Decision Readiness */}
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
              Readiness
            </span>
            <span className={cn('text-lg font-bold', confidenceColor)}>
              {readiness.confidence}%
            </span>
          </div>

          {/* Confidence bar */}
          <div
            className="h-1.5 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden mb-3"
            role="progressbar"
            aria-valuenow={readiness.confidence}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Decision readiness: ${readiness.confidence}%`}
          >
            <div
              className={cn('h-full rounded-full transition-all duration-500', confidenceBg)}
              style={{ width: `${readiness.confidence}%` }}
            />
          </div>

          {readiness.issues.length > 0 && (
            <ul className="space-y-1">
              {readiness.issues.slice(0, 4).map((issue, i) => (
                <li key={i} className="text-xs text-neutral-500 dark:text-neutral-400 flex items-start gap-1.5">
                  <span className="text-warning-500 mt-0.5 shrink-0">-</span>
                  <span>{issue}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* 2. Blind Spots */}
        {blind_spots.length > 0 && (
          <ExpandableSection
            id="blindspots"
            icon={<SearchIcon className="w-3.5 h-3.5 text-warning-500" />}
            title="Blind Spots"
            count={blind_spots.length}
            isExpanded={expandedSection === 'blindspots'}
            onToggle={() => setExpandedSection(expandedSection === 'blindspots' ? null : 'blindspots')}
          >
            <ul className="space-y-2">
              {blind_spots.map((bs, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 cursor-pointer rounded p-1.5 -mx-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-900/50 transition-colors"
                  onMouseEnter={() => {
                    if (bs.relevant_theme_ids?.length) {
                      onHighlightNodes(bs.relevant_theme_ids);
                    }
                  }}
                >
                  <span className={cn(
                    'text-[10px] px-1 py-0.5 rounded uppercase mt-0.5 shrink-0 font-medium',
                    bs.severity === 'high' && 'bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400',
                    bs.severity === 'medium' && 'bg-warning-100 dark:bg-warning-900/30 text-warning-600 dark:text-warning-400',
                    bs.severity === 'low' && 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500',
                  )}>
                    {bs.severity}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-neutral-700 dark:text-neutral-300">{bs.description}</p>
                    <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-0.5">{bs.suggested_action}</p>
                  </div>
                </li>
              ))}
            </ul>
          </ExpandableSection>
        )}

        {/* 3. Untested Load-bearing Assumptions */}
        {untestedAssumptions.length > 0 && (
          <ExpandableSection
            id="assumptions"
            icon={<AlertIcon className="w-3.5 h-3.5 text-error-500" />}
            title="Untested Assumptions"
            count={untestedAssumptions.length}
            countClassName="text-error-500"
            isExpanded={expandedSection === 'assumptions'}
            onToggle={() => setExpandedSection(expandedSection === 'assumptions' ? null : 'assumptions')}
          >
            <ul className="space-y-2">
              {untestedAssumptions.map((a) => (
                <li
                  key={a.node_id}
                  className="flex items-start gap-2 cursor-pointer rounded p-1.5 -mx-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-900/50 transition-colors"
                  onMouseEnter={() => onHighlightNodes([a.node_id])}
                  onClick={() => onHighlightNodes([a.node_id])}
                >
                  <span className="text-[10px] px-1 py-0.5 rounded bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400 uppercase mt-0.5 shrink-0 font-medium">
                    critical
                  </span>
                  <p className="text-xs text-neutral-700 dark:text-neutral-300 flex-1">{a.content}</p>
                </li>
              ))}
            </ul>
          </ExpandableSection>
        )}

        {/* 4. Unsupported Claims */}
        {unsupportedClaims.length > 0 && (
          <ExpandableSection
            id="unsupported"
            icon={<WarningIcon className="w-3.5 h-3.5 text-amber-500" />}
            title="Unsupported Claims"
            count={unsupportedClaims.length}
            subtitle={`${evidence_coverage.supported_claims}/${evidence_coverage.total_claims} supported`}
            isExpanded={expandedSection === 'unsupported'}
            onToggle={() => setExpandedSection(expandedSection === 'unsupported' ? null : 'unsupported')}
          >
            <ul className="space-y-2">
              {unsupportedClaims.map((c) => (
                <li
                  key={c.node_id}
                  className="flex items-start gap-2 cursor-pointer rounded p-1.5 -mx-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-900/50 transition-colors"
                  onMouseEnter={() => onHighlightNodes([c.node_id])}
                  onClick={() => onHighlightNodes([c.node_id])}
                >
                  <span className="text-[10px] px-1 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 uppercase mt-0.5 shrink-0 font-medium">
                    no evidence
                  </span>
                  <p className="text-xs text-neutral-700 dark:text-neutral-300 flex-1">{c.content}</p>
                </li>
              ))}
            </ul>
          </ExpandableSection>
        )}

        {/* 5. Key Tensions */}
        {key_tensions.length > 0 && (
          <ExpandableSection
            id="tensions"
            icon={<SparklesIcon className="w-3.5 h-3.5 text-rose-500" />}
            title="Key Tensions"
            count={key_tensions.length}
            isExpanded={expandedSection === 'tensions'}
            onToggle={() => setExpandedSection(expandedSection === 'tensions' ? null : 'tensions')}
          >
            <ul className="space-y-2">
              {key_tensions.map((t) => (
                <li
                  key={t.node_id}
                  className="flex items-start gap-2 cursor-pointer rounded p-1.5 -mx-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-900/50 transition-colors"
                  onMouseEnter={() => onHighlightNodes([t.node_id, ...t.involved_nodes])}
                  onClick={() => onHighlightNodes([t.node_id, ...t.involved_nodes])}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-neutral-700 dark:text-neutral-300">{t.content}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={cn(
                        'text-[10px] px-1 py-0.5 rounded font-medium',
                        t.status === 'resolved'
                          ? 'bg-success-100 dark:bg-success-900/30 text-success-600 dark:text-success-400'
                          : t.status === 'acknowledged'
                          ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                          : 'bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400',
                      )}>
                        {t.status}
                      </span>
                      <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
                        {t.involved_nodes.length} nodes
                      </span>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </ExpandableSection>
        )}

        {/* Evidence Coverage bar */}
        <div className="p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
              Evidence Coverage
            </span>
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              {evidence_coverage.supported_claims}/{evidence_coverage.total_claims}
            </span>
          </div>
          {evidence_coverage.total_claims > 0 && (
            <div
              className="h-1.5 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden"
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
    </div>
  );
}

// ── Expandable Section ──

function ExpandableSection({
  id,
  icon,
  title,
  count,
  subtitle,
  countClassName,
  isExpanded,
  onToggle,
  children,
}: {
  id: string;
  icon: React.ReactNode;
  title: string;
  count: number;
  subtitle?: string;
  countClassName?: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  const contentId = `analysis-section-${id}`;
  return (
    <div className="p-4">
      <button
        onClick={onToggle}
        aria-expanded={isExpanded}
        aria-controls={contentId}
        className="flex items-center justify-between w-full text-left group"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-xs font-medium text-neutral-800 dark:text-neutral-200">
            {title}
          </span>
          <span className={cn('text-xs text-neutral-400 dark:text-neutral-500', countClassName)}>
            {count}
          </span>
          {subtitle && (
            <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
              ({subtitle})
            </span>
          )}
        </div>
        <span className="text-xs text-neutral-400 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors">
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
            className="overflow-hidden mt-2"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
