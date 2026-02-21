/**
 * OrientationView — lens-based editorial analysis layer.
 *
 * Renders below the thematic cluster map on the project page.
 * Shows findings, exploration angles, and exit ramps (discuss/research).
 *
 * Progressive rendering via SSE: findings fade in one by one as they
 * arrive from the orientation generation stream.
 */

'use client';

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { SectionTitle, LabelHeading } from '@/components/ui/headings';
import { Button } from '@/components/ui/button';
import { ChevronRightIcon } from '@/components/ui/icons';
import { Spinner } from '@/components/ui/spinner';
import type { ProjectOrientation, OrientationFinding, LensType } from '@/lib/types/orientation';
import { LENS_LABELS } from '@/lib/types/orientation';
import type { ClusterHierarchy, InsightType } from '@/lib/types/hierarchy';

// ── Type config for finding icons ─────────────────────────────────

const FINDING_TYPE_CONFIG: Partial<Record<InsightType, { icon: string; label: string }>> = {
  consensus: { icon: '\u2705', label: 'Consensus' },
  tension: { icon: '\u26a1', label: 'Tension' },
  gap: { icon: '\ud83d\udd0d', label: 'Gap' },
  weak_evidence: { icon: '\u26a0\ufe0f', label: 'Weak Evidence' },
  pattern: { icon: '\ud83d\udcca', label: 'Pattern' },
  connection: { icon: '\ud83d\udd17', label: 'Connection' },
  exploration_angle: { icon: '\u2192', label: 'Explore' },
};

// ── Props ─────────────────────────────────────────────────────────

interface OrientationViewProps {
  orientation: ProjectOrientation | null;
  isGenerating: boolean;
  hierarchy: ClusterHierarchy | null;
  onDiscuss: (insightId: string, title: string, body: string) => void;
  onResearch: (insightId: string) => void;
  onGenerateAngle: (insightId: string) => void;
  onRegenerateOrientation: () => void;
  onEditOrientation?: () => void;
  generatingAngleId?: string | null;
}

// ── Main component ────────────────────────────────────────────────

export function OrientationView({
  orientation,
  isGenerating,
  hierarchy,
  onDiscuss,
  onResearch,
  onGenerateAngle,
  onRegenerateOrientation,
  onEditOrientation,
  generatingAngleId = null,
}: OrientationViewProps) {
  // No orientation yet — don't render anything
  if (!orientation && !isGenerating) {
    return null;
  }

  // Generating skeleton
  if (isGenerating && (!orientation || orientation.status === 'generating')) {
    const hasPartialContent = orientation?.lead_text || (orientation?.findings?.length ?? 0) > 0;

    if (!hasPartialContent) {
      return <OrientationSkeleton />;
    }
    // Fall through to render partial content with skeleton at the bottom
  }

  // Failed state
  if (orientation?.status === 'failed') {
    return <OrientationFailed onRetry={onRegenerateOrientation} />;
  }

  // No findings or lead — empty state
  if (orientation && !orientation.lead_text && orientation.findings.length === 0) {
    return null;
  }

  // Memoize derived data to avoid recomputation on every render
  const { findings, angles } = useMemo(() => {
    const allFindings = orientation?.findings ?? [];
    return {
      findings: allFindings.filter(f => f.insight_type !== 'exploration_angle'),
      angles: allFindings.filter(f => f.insight_type === 'exploration_angle'),
    };
  }, [orientation?.findings]);

  // Build theme label lookup from hierarchy (stable unless hierarchy changes)
  const themeLabelMap = useMemo(() => buildThemeLabelMap(hierarchy), [hierarchy]);

  const lensLabel = orientation?.lens_type
    ? LENS_LABELS[orientation.lens_type as LensType] ?? orientation.lens_type.replace(/_/g, ' ')
    : '';

  return (
    <div className="space-y-5">
      {/* Header with lens label and lead text */}
      <OrientationHeader
        lensLabel={lensLabel}
        leadText={orientation?.lead_text ?? ''}
        onRegenerate={onRegenerateOrientation}
        onEdit={onEditOrientation}
        isGenerating={isGenerating}
      />

      {/* Findings */}
      {findings.length > 0 && (
        <div className="space-y-3">
          {findings.map((finding, idx) => (
            <motion.div
              key={finding.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: Math.min(idx * 0.1, 0.5) }}
            >
              <FindingCard
                finding={finding}
                themeLabelMap={themeLabelMap}
                onDiscuss={onDiscuss}
                onResearch={onResearch}
              />
            </motion.div>
          ))}
        </div>
      )}

      {/* Secondary lens invitation */}
      {orientation?.secondary_lens && orientation.secondary_lens_reason && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.3 }}
          className="text-sm text-neutral-500 dark:text-neutral-400 italic px-1"
        >
          {orientation.secondary_lens_reason}
        </motion.div>
      )}

      {/* Exploration angles */}
      {angles.length > 0 && (
        <ExplorationAngles
          angles={angles}
          onGenerate={onGenerateAngle}
          generatingAngleId={generatingAngleId}
        />
      )}

      {/* Generation in progress indicator (partial content) */}
      {isGenerating && (
        <div className="flex items-center gap-2 px-1">
          <div className="h-3 w-3 rounded-full border-2 border-accent-300 dark:border-accent-600 border-t-transparent animate-spin" />
          <span className="text-xs text-neutral-400 dark:text-neutral-500">
            Analyzing...
          </span>
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────

function OrientationHeader({
  lensLabel,
  leadText,
  onRegenerate,
  onEdit,
  isGenerating,
}: {
  lensLabel: string;
  leadText: string;
  onRegenerate: () => void;
  onEdit?: () => void;
  isGenerating: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center gap-3 mb-2">
        <span className="text-lg">{'\ud83e\udded'}</span>
        <SectionTitle className="text-primary-900 dark:text-primary-50 flex-1">
          Orientation
        </SectionTitle>
        {lensLabel && (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-accent-100 dark:bg-accent-900/40 text-accent-700 dark:text-accent-300 shrink-0">
            {lensLabel}
          </span>
        )}
        {onEdit && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onEdit}
            disabled={isGenerating}
            className="text-xs h-6 px-2 text-neutral-400 hover:text-accent-600 dark:hover:text-accent-400"
            title="Edit orientation via chat"
          >
            Edit
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={onRegenerate}
          disabled={isGenerating}
          className="text-xs h-6 px-2 text-neutral-400 hover:text-neutral-600"
          title="Regenerate orientation"
        >
          {isGenerating ? 'Analyzing...' : 'Refresh'}
        </Button>
      </div>
      {leadText && (
        <p className="text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed">
          {leadText}
        </p>
      )}
    </motion.div>
  );
}

function FindingCard({
  finding,
  themeLabelMap,
  onDiscuss,
  onResearch,
}: {
  finding: OrientationFinding;
  themeLabelMap: Map<string, string>;
  onDiscuss: (insightId: string, title: string, body: string) => void;
  onResearch: (insightId: string) => void;
}) {
  const [showSources, setShowSources] = useState(false);

  const config = FINDING_TYPE_CONFIG[finding.insight_type] ?? { icon: '\u2022', label: 'Finding' };
  const isResearching = finding.status === 'researching';
  const hasResearchResult = finding.research_result?.answer;
  const hasLinkedThread = !!finding.linked_thread;

  // Map source_cluster_ids to theme labels
  const sourceLabels = finding.source_cluster_ids
    .map(id => themeLabelMap.get(id))
    .filter(Boolean) as string[];

  return (
    <div
      className={cn(
        'rounded-lg border p-4',
        'border-neutral-200/80 dark:border-neutral-800/80',
        isResearching && 'animate-pulse',
      )}
    >
      <div className="flex items-start gap-2.5">
        <span className="text-sm shrink-0 mt-0.5">{config.icon}</span>
        <div className="flex-1 min-w-0">
          {/* Type label */}
          <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
            {config.label}
          </span>

          {/* Heading */}
          <h4 className="text-sm font-semibold text-primary-900 dark:text-primary-100 mt-0.5">
            {finding.title}
          </h4>

          {/* Body */}
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1 leading-relaxed">
            {finding.content}
          </p>

          {/* Source themes (expandable) */}
          {sourceLabels.length > 0 && (
            <button
              onClick={() => setShowSources(!showSources)}
              className="text-xs text-neutral-400 dark:text-neutral-500 mt-2 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors flex items-center gap-1"
              aria-expanded={showSources}
              aria-label={`${showSources ? 'Hide' : 'Show'} source themes`}
            >
              <ChevronRightIcon className={cn('w-3 h-3 transition-transform', showSources && 'rotate-90')} />
              {showSources ? 'Hide sources' : `From ${sourceLabels.length} theme${sourceLabels.length > 1 ? 's' : ''}`}
            </button>
          )}
          <AnimatePresence>
            {showSources && sourceLabels.length > 0 && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="overflow-hidden"
              >
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {sourceLabels.map((label, i) => (
                    <span
                      key={i}
                      className="text-xs px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400"
                    >
                      {label}
                    </span>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Research result (inline) */}
          {hasResearchResult && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-3 rounded-md bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200/60 dark:border-neutral-800/60 p-3"
            >
              <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1.5">
                Research findings
              </p>
              <p className="text-sm text-neutral-600 dark:text-neutral-300 leading-relaxed">
                {finding.research_result.answer}
              </p>
              {finding.research_result.sources && finding.research_result.sources.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {finding.research_result.sources.map((src, i) => (
                    <span
                      key={i}
                      className="text-xs px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400"
                    >
                      {src.title}
                    </span>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* Action buttons — only render when there's something to show */}
          {(finding.action_type === 'discuss' && !hasLinkedThread) ||
           (finding.action_type === 'research' && !hasResearchResult) ||
           hasLinkedThread ? (
            <div className="flex items-center gap-2 mt-2.5">
              {finding.action_type === 'discuss' && !hasLinkedThread && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onDiscuss(finding.id, finding.title, finding.content)}
                  className="text-xs h-6 px-2 text-accent-600 dark:text-accent-400 hover:text-accent-700"
                  aria-label={`Discuss: ${finding.title}`}
                >
                  Discuss this {'\u2192'}
                </Button>
              )}
              {finding.action_type === 'research' && !hasResearchResult && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onResearch(finding.id)}
                  disabled={isResearching}
                  className="text-xs h-6 px-2 text-accent-600 dark:text-accent-400 hover:text-accent-700"
                  aria-label={`Research: ${finding.title}`}
                >
                  {isResearching ? 'Researching...' : 'Research this \u2192'}
                </Button>
              )}
              {hasLinkedThread && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onDiscuss(finding.id, finding.title, finding.content)}
                  className="text-xs h-6 px-2 text-neutral-400 dark:text-neutral-500 hover:text-accent-600 dark:hover:text-accent-400"
                  aria-label={`Continue discussion: ${finding.title}`}
                >
                  Continue discussion {'\u2192'}
                </Button>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function ExplorationAngles({
  angles,
  onGenerate,
  generatingAngleId,
}: {
  angles: OrientationFinding[];
  onGenerate: (insightId: string) => void;
  generatingAngleId: string | null;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4, duration: 0.3 }}
      className="space-y-2"
    >
      <LabelHeading>Explore further</LabelHeading>

      <div className="space-y-1.5">
        {angles.map((angle) => (
          <AngleItem
            key={angle.id}
            angle={angle}
            onGenerate={() => onGenerate(angle.id)}
            isGenerating={generatingAngleId === angle.id}
          />
        ))}
      </div>
    </motion.div>
  );
}

function AngleItem({
  angle,
  onGenerate,
  isGenerating,
}: {
  angle: OrientationFinding;
  onGenerate: () => void;
  isGenerating: boolean;
}) {
  const hasContent = !!angle.content;

  return (
    <div
      className={cn(
        'rounded-lg border p-3 transition-colors',
        'border-neutral-200/60 dark:border-neutral-800/60',
        !hasContent && !isGenerating && 'cursor-pointer hover:border-accent-300 dark:hover:border-accent-700 hover:bg-accent-50/20 dark:hover:bg-accent-900/10',
      )}
      onClick={!hasContent && !isGenerating ? onGenerate : undefined}
      role={!hasContent && !isGenerating ? 'button' : undefined}
      tabIndex={!hasContent && !isGenerating ? 0 : undefined}
      onKeyDown={!hasContent && !isGenerating ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onGenerate(); } } : undefined}
      aria-label={!hasContent ? `Explore: ${angle.title}` : undefined}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm text-neutral-400 shrink-0">{'\u2192'}</span>
        <p className="text-sm font-medium text-primary-800 dark:text-primary-200 flex-1">
          {angle.title}
        </p>
        {isGenerating && (
          <Spinner size="sm" className="text-accent-500 shrink-0" />
        )}
        {!hasContent && !isGenerating && (
          <ChevronRightIcon className="w-4 h-4 text-neutral-300 dark:text-neutral-600 shrink-0" />
        )}
      </div>

      {/* Generated content (fade in) */}
      <AnimatePresence>
        {hasContent && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2 ml-6 leading-relaxed">
              {angle.content}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function OrientationSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="h-4 w-4 rounded-full border-2 border-accent-300 dark:border-accent-600 border-t-transparent animate-spin" />
        <span className="text-sm text-neutral-500 dark:text-neutral-400">
          Analyzing your documents...
        </span>
      </div>
      <div className="animate-pulse space-y-3">
        <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-48" />
        <div className="space-y-2">
          <div className="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-full" />
          <div className="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-5/6" />
        </div>
        <div className="h-20 rounded-lg bg-neutral-100 dark:bg-neutral-800/50" />
        <div className="h-20 rounded-lg bg-neutral-100 dark:bg-neutral-800/50" />
        <div className="h-16 rounded-lg bg-neutral-100 dark:bg-neutral-800/50" />
      </div>
    </div>
  );
}

function OrientationFailed({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-red-200/60 dark:border-red-800/40 bg-red-50/60 dark:bg-red-950/20 p-6">
      <p className="text-sm text-red-600 dark:text-red-400 mb-3">
        Failed to analyze your documents.
      </p>
      <Button
        variant="ghost"
        size="sm"
        onClick={onRetry}
        className="text-xs font-medium text-red-700 dark:text-red-300 hover:text-red-800 dark:hover:text-red-200"
      >
        Try again
      </Button>
    </div>
  );
}

// ── Utilities ──────────────────────────────────────────────────────

function buildThemeLabelMap(hierarchy: ClusterHierarchy | null): Map<string, string> {
  const map = new Map<string, string>();
  if (!hierarchy?.tree?.children) return map;

  for (const child of hierarchy.tree.children) {
    if (child.id && child.label) {
      map.set(child.id, child.label);
    }
    // Also map Level 1 children if they exist
    if (child.children) {
      for (const grandchild of child.children) {
        if (grandchild.id && grandchild.label) {
          map.set(grandchild.id, grandchild.label);
        }
      }
    }
  }
  return map;
}
