/**
 * ProjectSummaryView — renders the AI-generated project summary.
 *
 * Displays 5 sections (overview, key findings, emerging picture,
 * attention needed, what changed) with inline node citations that
 * link to the graph view.
 */

'use client';

import { useMemo, Fragment } from 'react';
import { Button } from '@/components/ui/button';
import type { ProjectSummary, GraphNode, NodeType } from '@/lib/types/graph';

// ── Inline SVG icons (project doesn't use lucide-react) ──

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 2v6h-6" /><path d="M3 12a9 9 0 0115.36-6.36L21 8" />
      <path d="M3 22v-6h6" /><path d="M21 12a9 9 0 01-15.36 6.36L3 16" />
    </svg>
  );
}

function AlertIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l2.09 6.26L20 10l-5.91 1.74L12 18l-2.09-6.26L4 10l5.91-1.74z" />
    </svg>
  );
}

function TrendIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" />
    </svg>
  );
}

function EyeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" />
    </svg>
  );
}

// ── Citation colors (matches GraphCanvas MINIMAP_COLORS) ──

const CITATION_COLORS: Record<NodeType, { bg: string; text: string; border: string }> = {
  claim: { bg: 'bg-blue-50 dark:bg-blue-950/40', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-200 dark:border-blue-800' },
  evidence: { bg: 'bg-emerald-50 dark:bg-emerald-950/40', text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-200 dark:border-emerald-800' },
  assumption: { bg: 'bg-amber-50 dark:bg-amber-950/40', text: 'text-amber-700 dark:text-amber-300', border: 'border-amber-200 dark:border-amber-800' },
  tension: { bg: 'bg-rose-50 dark:bg-rose-950/40', text: 'text-rose-700 dark:text-rose-300', border: 'border-rose-200 dark:border-rose-800' },
};

const CITATION_LABELS: Record<NodeType, string> = {
  claim: 'C',
  evidence: 'E',
  assumption: 'A',
  tension: 'T',
};

// ── Citation regex ──

const CITATION_REGEX = /\[nodeId:([a-f0-9-]+)\]/g;

// ── Props ──

interface ProjectSummaryViewProps {
  summary: ProjectSummary;
  isStale: boolean;
  isGenerating: boolean;
  onRegenerate: () => void;
  onCitationClick: (nodeId: string) => void;
  /** Graph nodes for resolving citation tooltips */
  graphNodes?: GraphNode[];
  className?: string;
}

export function ProjectSummaryView({
  summary,
  isStale,
  isGenerating,
  onRegenerate,
  onCitationClick,
  graphNodes = [],
  className = '',
}: ProjectSummaryViewProps) {
  const nodeMap = useMemo(() => {
    const map = new Map<string, GraphNode>();
    for (const node of graphNodes) {
      map.set(node.id, node);
    }
    return map;
  }, [graphNodes]);

  // ── Seed state ──
  if (summary.status === 'seed') {
    return (
      <div className={className}>
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <div className="flex items-center gap-2 mb-3">
            <SparklesIcon className="w-4 h-4 text-accent-500" />
            <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-200">
              Project Summary
            </h3>
          </div>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
            {summary.sections.overview || 'Your knowledge graph is still small.'}
          </p>
          {summary.sections.key_findings?.length > 0 && (
            <div className="space-y-1.5">
              {summary.sections.key_findings[0]?.narrative && (
                <p className="text-xs text-neutral-500 dark:text-neutral-400">
                  {summary.sections.key_findings[0].narrative}
                </p>
              )}
            </div>
          )}
          <p className="mt-4 text-xs text-neutral-400 dark:text-neutral-500">
            Add more documents to generate a full AI summary.
          </p>
        </div>
      </div>
    );
  }

  // ── Generating state ──
  if (summary.status === 'generating' || isGenerating) {
    return (
      <div className={className}>
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <div className="flex items-center gap-2 mb-4">
            <RefreshIcon className="w-4 h-4 text-accent-500 animate-spin" />
            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-200">
              Generating summary...
            </span>
          </div>
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-full mb-2" />
                <div className="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const { sections } = summary;

  return (
    <div className={className}>
      {/* Header with staleness */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-100">
          Project Summary
        </h2>
        <div className="flex items-center gap-2">
          {summary.updated_at && (
            <span className="text-xs text-neutral-400 dark:text-neutral-500 flex items-center gap-1">
              <ClockIcon className="w-3 h-3" />
              {formatRelativeTime(summary.updated_at)}
            </span>
          )}
          {isStale && (
            <span className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-1.5 py-0.5 rounded">
              Outdated
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={onRegenerate}
            disabled={isGenerating}
            className="h-7 px-2 text-xs"
          >
            <RefreshIcon className={`w-3 h-3 mr-1 ${isGenerating ? 'animate-spin' : ''}`} />
            Regenerate
          </Button>
        </div>
      </div>

      <div className="space-y-5">
        {/* Overview */}
        {sections.overview && (
          <section>
            <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
              <RenderWithCitations
                text={sections.overview}
                nodeMap={nodeMap}
                onCitationClick={onCitationClick}
              />
            </p>
          </section>
        )}

        {/* Key Findings */}
        {sections.key_findings?.length > 0 && (
          <section>
            <SectionHeader icon={EyeIcon} label="Key Findings" />
            <div className="space-y-3 mt-2">
              {sections.key_findings.map((theme, i) => (
                <div key={i} className="pl-3 border-l-2 border-accent-200 dark:border-accent-800">
                  <h4 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1">
                    {theme.theme_label}
                  </h4>
                  <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
                    <RenderWithCitations
                      text={theme.narrative}
                      nodeMap={nodeMap}
                      onCitationClick={onCitationClick}
                    />
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Emerging Picture */}
        {sections.emerging_picture && (
          <section>
            <SectionHeader icon={TrendIcon} label="Emerging Picture" />
            <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed mt-2">
              <RenderWithCitations
                text={sections.emerging_picture}
                nodeMap={nodeMap}
                onCitationClick={onCitationClick}
              />
            </p>
          </section>
        )}

        {/* Attention Needed */}
        {sections.attention_needed && (
          <section className="rounded-md bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-800/40 p-3">
            <SectionHeader icon={AlertIcon} label="Attention Needed" className="text-amber-700 dark:text-amber-300" />
            <p className="text-sm text-amber-800 dark:text-amber-200 leading-relaxed mt-2">
              <RenderWithCitations
                text={sections.attention_needed}
                nodeMap={nodeMap}
                onCitationClick={onCitationClick}
              />
            </p>
          </section>
        )}

        {/* What Changed */}
        {sections.what_changed && sections.what_changed !== 'This is the first project summary.' && (
          <section className="pt-3 border-t border-neutral-200/60 dark:border-neutral-700/60">
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              <span className="font-medium">What changed: </span>
              <RenderWithCitations
                text={sections.what_changed}
                nodeMap={nodeMap}
                onCitationClick={onCitationClick}
              />
            </p>
          </section>
        )}
      </div>
    </div>
  );
}


// ── Section header ──

function SectionHeader({
  icon: Icon,
  label,
  className = '',
}: {
  icon: React.ElementType;
  label: string;
  className?: string;
}) {
  return (
    <div className={`flex items-center gap-1.5 ${className}`}>
      <Icon className="w-3.5 h-3.5" />
      <h3 className="text-xs font-semibold uppercase tracking-wider">
        {label}
      </h3>
    </div>
  );
}


// ── Citation rendering ──

function RenderWithCitations({
  text,
  nodeMap,
  onCitationClick,
}: {
  text: string;
  nodeMap: Map<string, GraphNode>;
  onCitationClick: (nodeId: string) => void;
}) {
  const parts = useMemo(() => {
    const result: Array<{ type: 'text'; value: string } | { type: 'citation'; nodeId: string }> = [];
    let lastIndex = 0;

    for (const match of text.matchAll(CITATION_REGEX)) {
      const index = match.index!;
      if (index > lastIndex) {
        result.push({ type: 'text', value: text.slice(lastIndex, index) });
      }
      result.push({ type: 'citation', nodeId: match[1] });
      lastIndex = index + match[0].length;
    }

    if (lastIndex < text.length) {
      result.push({ type: 'text', value: text.slice(lastIndex) });
    }

    return result;
  }, [text]);

  return (
    <>
      {parts.map((part, i) => {
        if (part.type === 'text') {
          return <Fragment key={i}>{part.value}</Fragment>;
        }

        const node = nodeMap.get(part.nodeId);
        const nodeType = node?.node_type ?? 'claim';
        const colors = CITATION_COLORS[nodeType];
        const label = CITATION_LABELS[nodeType];

        return (
          <button
            key={i}
            onClick={() => onCitationClick(part.nodeId)}
            title={node ? `[${nodeType}] ${node.content.slice(0, 120)}` : part.nodeId}
            className={`
              inline-flex items-center justify-center
              w-4 h-4 rounded text-[9px] font-bold
              ${colors.bg} ${colors.text} ${colors.border}
              border cursor-pointer
              hover:opacity-80 transition-opacity
              align-text-top mx-0.5
            `}
          >
            {label}
          </button>
        );
      })}
    </>
  );
}


// ── Time formatting ──

function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);

  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}
