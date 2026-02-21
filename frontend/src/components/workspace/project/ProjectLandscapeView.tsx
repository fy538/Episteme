/**
 * ProjectLandscapeView — zoomable hierarchical view of a project's
 * document clusters.
 *
 * Replaces the graph visualization at the project level. Displays
 * themes → topics → source chunks as nested expandable cards.
 */

'use client';

import { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { SectionTitle, LabelHeading } from '@/components/ui/headings';
import { Button } from '@/components/ui/button';
import { ChevronRightIcon } from '@/components/ui/icons';
import type {
  ClusterHierarchy,
  ClusterTreeNode,
  ProjectInsight,
  InsightType,
  HierarchyDiff,
} from '@/lib/types/hierarchy';
import { HierarchyChangeCard } from './HierarchyChangeCard';

// ── Helpers ──────────────────────────────────────────────────────

function pluralize(count: number, singular: string, plural?: string): string {
  return `${count} ${count === 1 ? singular : (plural ?? singular + 's')}`;
}

function getThemeColor(idx: number) {
  return THEME_COLORS[idx % THEME_COLORS.length];
}

// ── Props ────────────────────────────────────────────────────────

interface ProjectLandscapeViewProps {
  hierarchy: ClusterHierarchy;
  insights: ProjectInsight[];
  isBuilding?: boolean;
  isFailed?: boolean;
  onOpenCase?: (context?: { insightId?: string }) => void;
  onAcknowledgeInsight?: (insightId: string) => void;
  onDismissInsight?: (insightId: string) => void;
  onRebuild?: () => void;
  isRebuilding?: boolean;
  updatingInsightId?: string | null;
}

// ── Theme colors (cycling for coverage bar and cards) ────────────

const THEME_COLORS = [
  { bg: 'bg-accent-50 dark:bg-accent-950/30', border: 'border-accent-200 dark:border-accent-800', text: 'text-accent-700 dark:text-accent-300', bar: 'bg-accent-500', leftBorder: 'border-l-accent-300 dark:border-l-accent-700' },
  { bg: 'bg-info-50 dark:bg-info-950/30', border: 'border-info-200 dark:border-info-800', text: 'text-info-700 dark:text-info-300', bar: 'bg-info-500', leftBorder: 'border-l-info-300 dark:border-l-info-700' },
  { bg: 'bg-success-50 dark:bg-success-950/30', border: 'border-success-200 dark:border-success-800', text: 'text-success-700 dark:text-success-300', bar: 'bg-success-500', leftBorder: 'border-l-success-300 dark:border-l-success-700' },
  { bg: 'bg-warning-50 dark:bg-warning-950/30', border: 'border-warning-200 dark:border-warning-800', text: 'text-warning-700 dark:text-warning-300', bar: 'bg-warning-500', leftBorder: 'border-l-warning-300 dark:border-l-warning-700' },
  { bg: 'bg-rose-50 dark:bg-rose-950/30', border: 'border-rose-200 dark:border-rose-800', text: 'text-rose-700 dark:text-rose-300', bar: 'bg-rose-500', leftBorder: 'border-l-rose-300 dark:border-l-rose-700' },
];

const INSIGHT_TYPE_CONFIG: Partial<Record<InsightType, { icon: string; label: string }>> = {
  tension: { icon: '\u26a1', label: 'Tension' },
  blind_spot: { icon: '\ud83d\udd0d', label: 'Blind Spot' },
  pattern: { icon: '\ud83d\udcca', label: 'Pattern' },
  stale_finding: { icon: '\u231b', label: 'Stale Finding' },
  connection: { icon: '\ud83d\udd17', label: 'Connection' },
  consensus: { icon: '\u2705', label: 'Consensus' },
  gap: { icon: '\ud83d\udd0d', label: 'Gap' },
  weak_evidence: { icon: '\u26a0\ufe0f', label: 'Weak Evidence' },
  exploration_angle: { icon: '\u2192', label: 'Explore' },
};

// ── Main component ───────────────────────────────────────────────

export function ProjectLandscapeView({
  hierarchy,
  insights,
  isBuilding = false,
  isFailed = false,
  onOpenCase,
  onAcknowledgeInsight,
  onDismissInsight,
  onRebuild,
  isRebuilding = false,
  updatingInsightId = null,
}: ProjectLandscapeViewProps) {
  const [expandedThemeId, setExpandedThemeId] = useState<string | null>(null);
  const [expandedTopicId, setExpandedTopicId] = useState<string | null>(null);
  const [diffDismissed, setDiffDismissed] = useState(false);

  const tree = hierarchy?.tree;
  const themes = useMemo(() => tree?.children ?? [], [tree]);
  const diff = hierarchy?.metadata?.diff ?? null;

  const handleToggleTheme = useCallback((themeId: string) => {
    setExpandedThemeId(prev => prev === themeId ? null : themeId);
    setExpandedTopicId(null);
  }, []);

  const handleToggleTopic = useCallback((topicId: string) => {
    setExpandedTopicId(prev => prev === topicId ? null : topicId);
  }, []);

  // Failed state
  if (isFailed) {
    return <LandscapeFailedState onRebuild={onRebuild} isRebuilding={isRebuilding} />;
  }

  // Building state
  if (isBuilding || !tree) {
    return <LandscapeBuildingState />;
  }

  // Empty state (ready but no themes)
  if (themes.length === 0) {
    return <LandscapeEmptyState />;
  }

  return (
    <div className="space-y-6">
      {/* Root overview */}
      <LandscapeOverview
        label={tree.label}
        summary={tree.summary}
        themeCount={themes.length}
        totalChunks={tree.chunk_count}
        documentCount={tree.document_ids.length}
        onRebuild={onRebuild}
        isRebuilding={isRebuilding}
      />

      {/* Change detection card (Plan 6) */}
      {diff && !diffDismissed && (
        <HierarchyChangeCard
          diff={diff}
          summary={hierarchy.metadata?.diff_summary ?? ''}
          version={hierarchy.version}
          projectId={hierarchy.project}
          onDismiss={() => setDiffDismissed(true)}
        />
      )}

      {/* Coverage bar */}
      {themes.length > 0 && (
        <CoverageBar themes={themes} />
      )}

      {/* Theme cards */}
      <div className="space-y-3" role="tree" aria-label="Knowledge landscape themes">
        {themes.map((theme, idx) => (
          <ThemeCard
            key={theme.id}
            theme={theme}
            colorIdx={idx}
            isExpanded={expandedThemeId === theme.id}
            expandedTopicId={expandedThemeId === theme.id ? expandedTopicId : null}
            onToggle={() => handleToggleTheme(theme.id)}
            onToggleTopic={handleToggleTopic}
            delay={Math.min(idx * 0.05, 0.3)}
            diff={diff}
          />
        ))}
      </div>

      {/* Agent-discovered insights (non-orientation) — kept inline for backwards compat */}
      {/* Orientation findings are rendered in the OrientationView below */}
      {insights.filter(i => i.source_type !== 'orientation').length > 0 && (
        <InsightsPanel
          insights={insights.filter(i => i.source_type !== 'orientation')}
          onAcknowledge={onAcknowledgeInsight}
          onDismiss={onDismissInsight}
          onOpenCase={onOpenCase}
          updatingInsightId={updatingInsightId}
        />
      )}
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────

function LandscapeOverview({
  label,
  summary,
  themeCount,
  totalChunks,
  documentCount,
  onRebuild,
  isRebuilding,
}: {
  label: string;
  summary: string;
  themeCount: number;
  totalChunks: number;
  documentCount: number;
  onRebuild?: () => void;
  isRebuilding?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center gap-3 mb-2">
        <span className="text-lg">&#x1f30d;</span>
        <SectionTitle className="text-primary-900 dark:text-primary-50 flex-1">
          {label}
        </SectionTitle>
        {onRebuild && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRebuild}
            disabled={isRebuilding}
            className="text-xs h-6 px-2 text-neutral-400 hover:text-neutral-600"
            title="Rebuild landscape"
          >
            {isRebuilding ? 'Rebuilding...' : 'Refresh'}
          </Button>
        )}
      </div>
      <p className="text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed">
        {summary}
      </p>
      <div className="flex items-center gap-4 mt-3">
        <span className="text-xs text-neutral-500 dark:text-neutral-400">
          {pluralize(themeCount, 'theme')}
        </span>
        <span className="text-xs text-neutral-500 dark:text-neutral-400">
          {pluralize(totalChunks, 'passage')}
        </span>
        <span className="text-xs text-neutral-500 dark:text-neutral-400">
          {pluralize(documentCount, 'document')}
        </span>
      </div>
    </motion.div>
  );
}

function CoverageBar({ themes }: { themes: ClusterTreeNode[] }) {
  return (
    <div className="space-y-1.5">
      <LabelHeading>Coverage</LabelHeading>
      <div
        className="flex h-2 rounded-full overflow-hidden bg-neutral-100 dark:bg-neutral-800"
        role="img"
        aria-label={`Coverage distribution across ${themes.length} themes`}
      >
        {themes.map((theme, idx) => {
          const color = getThemeColor(idx);
          return (
            <div
              key={theme.id}
              className={cn('h-full transition-all duration-300', color.bar)}
              style={{ width: `${theme.coverage_pct}%` }}
              aria-label={`${theme.label}: ${theme.coverage_pct}%`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {themes.map((theme, idx) => {
          const color = getThemeColor(idx);
          return (
            <div key={theme.id} className="flex items-center gap-1.5">
              <div className={cn('w-2 h-2 rounded-full', color.bar)} />
              <span className="text-xs text-neutral-500 dark:text-neutral-400">
                {theme.label} ({theme.coverage_pct}%)
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ThemeCard({
  theme,
  colorIdx,
  isExpanded,
  expandedTopicId,
  onToggle,
  onToggleTopic,
  delay,
  diff,
}: {
  theme: ClusterTreeNode;
  colorIdx: number;
  isExpanded: boolean;
  expandedTopicId: string | null;
  onToggle: () => void;
  onToggleTopic: (topicId: string) => void;
  delay: number;
  diff?: HierarchyDiff | null;
}) {
  const color = getThemeColor(colorIdx);
  const topics = theme.children;
  const contentId = `theme-content-${theme.id}`;

  // Check if this theme is new or expanded (Plan 6 badges)
  const isNewTheme = diff?.new_themes?.some(t => t.label === theme.label) ?? false;
  const expandedInfo = diff?.expanded_themes?.find(t => t.label === theme.label);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay }}
      role="treeitem"
      aria-expanded={isExpanded}
      className={cn(
        'rounded-lg border transition-colors duration-150',
        isExpanded
          ? cn(color.border, color.bg)
          : 'border-neutral-200/80 dark:border-neutral-800/80 hover:border-neutral-300 dark:hover:border-neutral-700',
        isNewTheme && 'ring-1 ring-emerald-300 dark:ring-emerald-700',
      )}
    >
      {/* Theme header */}
      <button
        onClick={onToggle}
        aria-expanded={isExpanded}
        aria-controls={contentId}
        className="w-full text-left px-4 py-3 flex items-center gap-3"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium text-primary-900 dark:text-primary-100 truncate">
              {theme.label}
            </h3>
            <span className={cn(
              'text-xs font-medium px-1.5 py-0.5 rounded-full shrink-0',
              color.bg, color.text, color.border, 'border',
            )}>
              {theme.coverage_pct}%
            </span>
            {isNewTheme && (
              <span className="text-xs px-1.5 py-0.5 bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 rounded-full shrink-0 font-medium">
                New
              </span>
            )}
            {expandedInfo && (
              <span className="text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded-full shrink-0 font-medium">
                +{expandedInfo.growth} chunks
              </span>
            )}
          </div>
          {!isExpanded && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 line-clamp-1">
              {theme.summary}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0 text-xs text-neutral-400 dark:text-neutral-500">
          <span>{pluralize(theme.document_ids.length, 'doc')}</span>
          <ChevronRightIcon
            className={cn(
              'w-4 h-4 transition-transform duration-200',
              isExpanded && 'rotate-90',
            )}
          />
        </div>
      </button>

      {/* Expanded content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            id={contentId}
            role="group"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-3">
              {/* Theme synthesis */}
              <p className="text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed">
                {theme.summary}
              </p>

              {/* Topics */}
              {topics.length > 0 && (
                <div className="space-y-2">
                  <LabelHeading>
                    Topics ({topics.length})
                  </LabelHeading>
                  {topics.map((topic, tidx) => (
                    <TopicCard
                      key={topic.id}
                      topic={topic}
                      parentColor={color}
                      isExpanded={expandedTopicId === topic.id}
                      onToggle={() => onToggleTopic(topic.id)}
                      delay={Math.min(tidx * 0.03, 0.15)}
                    />
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function TopicCard({
  topic,
  parentColor,
  isExpanded,
  onToggle,
  delay,
}: {
  topic: ClusterTreeNode;
  parentColor: (typeof THEME_COLORS)[number];
  isExpanded: boolean;
  onToggle: () => void;
  delay: number;
}) {
  const contentId = `topic-content-${topic.id}`;

  return (
    <motion.div
      initial={{ opacity: 0, x: -4 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.15, delay }}
      role="treeitem"
      aria-expanded={isExpanded}
      className={cn(
        'rounded-md border-l-2 border transition-colors duration-150',
        isExpanded
          ? cn('border-neutral-300 dark:border-neutral-600 bg-white/60 dark:bg-neutral-900/40', parentColor.leftBorder)
          : cn('border-neutral-200/60 dark:border-neutral-800/60 hover:border-neutral-300 dark:hover:border-neutral-700', parentColor.leftBorder),
      )}
    >
      <button
        onClick={onToggle}
        aria-expanded={isExpanded}
        aria-controls={contentId}
        className="w-full text-left px-3 py-2 flex items-center gap-2"
      >
        <div className="flex-1 min-w-0">
          <span className="text-xs font-medium text-primary-800 dark:text-primary-200">
            {topic.label}
          </span>
        </div>
        <span className="text-xs text-neutral-400 dark:text-neutral-500 shrink-0">
          {pluralize(topic.chunk_count, 'passage')}
        </span>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            id={contentId}
            role="group"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-2">
              <p className="text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed">
                {topic.summary}
              </p>

              {/* Source info */}
              <div className="text-xs text-neutral-400 dark:text-neutral-500">
                {pluralize(topic.document_ids.length, 'source')} &middot; {pluralize(topic.chunk_count, 'passage')}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function InsightsPanel({
  insights,
  onAcknowledge,
  onDismiss,
  onOpenCase,
  updatingInsightId,
}: {
  insights: ProjectInsight[];
  onAcknowledge?: (id: string) => void;
  onDismiss?: (id: string) => void;
  onOpenCase?: (context?: { insightId?: string }) => void;
  updatingInsightId?: string | null;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.2 }}
      className="space-y-2"
    >
      <LabelHeading>Observations</LabelHeading>

      <div className="space-y-2">
        {insights.map((insight) => {
          const config = INSIGHT_TYPE_CONFIG[insight.insight_type] ?? { icon: '\ud83d\udcca', label: 'Pattern' };
          const isUpdating = updatingInsightId === insight.id;

          return (
            <div
              key={insight.id}
              className={cn(
                'rounded-lg border p-3',
                'border-neutral-200/80 dark:border-neutral-800/80',
                isUpdating && 'opacity-60 pointer-events-none',
              )}
            >
              <div className="flex items-start gap-2.5">
                <span className="text-sm shrink-0 mt-0.5">{config.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                      {config.label}
                    </span>
                    {insight.confidence >= 0.8 && (
                      <span className="text-xs text-accent-600 dark:text-accent-400">
                        High confidence
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-primary-900 dark:text-primary-100">
                    {insight.title}
                  </p>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1 leading-relaxed">
                    {insight.content}
                  </p>

                  <div className="flex items-center gap-2 mt-2">
                    {onAcknowledge && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onAcknowledge(insight.id)}
                        disabled={isUpdating}
                        className="text-xs h-6 px-2"
                      >
                        Acknowledge
                      </Button>
                    )}
                    {onDismiss && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDismiss(insight.id)}
                        disabled={isUpdating}
                        className="text-xs h-6 px-2 text-neutral-400"
                      >
                        Dismiss
                      </Button>
                    )}
                    {onOpenCase && ['tension', 'blind_spot', 'pattern'].includes(insight.insight_type) && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onOpenCase({ insightId: insight.id })}
                        className="text-xs h-6 px-2 text-accent-600 dark:text-accent-400"
                      >
                        Investigate
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}

function LandscapeBuildingState() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="h-4 w-4 rounded-full border-2 border-accent-300 border-t-transparent animate-spin" />
        <span className="text-sm text-neutral-500 dark:text-neutral-400">
          Building knowledge landscape...
        </span>
      </div>
      <div className="animate-pulse space-y-3">
        <div className="h-16 rounded-lg bg-neutral-100 dark:bg-neutral-800/50" />
        <div className="h-2 rounded-full bg-neutral-100 dark:bg-neutral-800/50" />
        <div className="grid grid-cols-2 gap-3">
          <div className="h-24 rounded-lg bg-neutral-100 dark:bg-neutral-800/50" />
          <div className="h-24 rounded-lg bg-neutral-100 dark:bg-neutral-800/50" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="h-24 rounded-lg bg-neutral-100 dark:bg-neutral-800/50" />
          <div className="h-24 rounded-lg bg-neutral-100 dark:bg-neutral-800/50" />
        </div>
      </div>
    </div>
  );
}

function LandscapeFailedState({
  onRebuild,
  isRebuilding,
}: {
  onRebuild?: () => void;
  isRebuilding?: boolean;
}) {
  return (
    <div className="rounded-lg border border-red-200/60 dark:border-red-800/40 bg-red-50/60 dark:bg-red-950/20 p-6 text-center">
      <p className="text-sm text-red-600 dark:text-red-400 mb-3">
        Failed to build the knowledge landscape.
      </p>
      {onRebuild && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onRebuild}
          disabled={isRebuilding}
          className="text-xs font-medium text-red-700 dark:text-red-300 hover:text-red-800 dark:hover:text-red-200"
        >
          {isRebuilding ? 'Rebuilding...' : 'Try Again'}
        </Button>
      )}
    </div>
  );
}

function LandscapeEmptyState() {
  return (
    <div className="rounded-lg border border-neutral-200/60 dark:border-neutral-800/60 p-6 text-center">
      <span className="text-2xl mb-2 block">&#x1f30d;</span>
      <p className="text-sm text-neutral-500 dark:text-neutral-400">
        No themes detected yet. Upload more documents to build a richer knowledge landscape.
      </p>
    </div>
  );
}
