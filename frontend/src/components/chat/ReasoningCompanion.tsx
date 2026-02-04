/**
 * Reasoning Companion - Dual-mode sidebar with meta-reflection and background work
 *
 * Top section: Natural language thinking (Socratic, questioning)
 * Bottom section: Background work tracking (signals, evidence, connections)
 *
 * Supports two modes:
 * 1. Unified stream mode: Receives reflection from unified chat stream (no separate SSE)
 * 2. Legacy mode: Uses separate SSE connection to companion-stream endpoint
 *
 * Progressive disclosure: Quiet → Active → Focused modes
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { useReasoningCompanion } from '@/hooks/useReasoningCompanion';
import { KnowledgeGraphView } from '@/components/graph/KnowledgeGraphView';
import { cn } from '@/lib/utils';
import type { BackgroundActivity, Reflection } from '@/lib/types/companion';

type VisibilityMode = 'quiet' | 'active' | 'focused';

interface ReasoningCompanionProps {
  threadId: string | null;
  caseId?: string | null;
  /** Unified stream mode: reflection content from ChatInterface */
  unifiedReflection?: string;
  /** Whether unified reflection is streaming */
  isUnifiedStreaming?: boolean;
  /** Use unified stream mode (disables legacy SSE) */
  useUnifiedStream?: boolean;
}

export function ReasoningCompanion({
  threadId,
  caseId,
  unifiedReflection,
  isUnifiedStreaming,
  useUnifiedStream = true, // Default to unified mode
}: ReasoningCompanionProps) {
  // Legacy SSE-based companion hook (only used when not in unified mode)
  const legacyCompanion = useReasoningCompanion(useUnifiedStream ? null : threadId);

  // Unified mode state
  const [unifiedReflectionState, setUnifiedReflectionState] = useState<Reflection | null>(null);

  // Update unified reflection state when prop changes
  useEffect(() => {
    if (useUnifiedStream && unifiedReflection !== undefined) {
      setUnifiedReflectionState({
        id: 'unified-' + Date.now(),
        text: unifiedReflection,
        trigger_type: 'user_message',
        patterns: {
          ungrounded_assumptions: [],
          contradictions: [],
          strong_claims: [],
          recurring_themes: [],
          missing_considerations: [],
        },
        created_at: new Date().toISOString(),
      });
    }
  }, [useUnifiedStream, unifiedReflection]);

  // Choose data source based on mode
  const reflection = useUnifiedStream ? unifiedReflectionState : legacyCompanion.reflection;
  const backgroundActivity = useUnifiedStream ? null : legacyCompanion.backgroundActivity;
  const currentTopic = useUnifiedStream ? null : legacyCompanion.currentTopic;
  const isActive = useUnifiedStream ? isUnifiedStreaming : legacyCompanion.isActive;
  const error = useUnifiedStream ? null : legacyCompanion.error;

  const [showGraph, setShowGraph] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  if (!threadId) {
    return null;
  }

  return (
    <>
      {/* Knowledge Graph Modal */}
      {showGraph && caseId && (
        <KnowledgeGraphView
          caseId={caseId}
          onClose={() => setShowGraph(false)}
        />
      )}

      <div
        ref={containerRef}
        className="w-80 border-l border-neutral-900/10 dark:border-neutral-100/10 bg-gradient-to-b from-neutral-50/80 to-white/80 dark:from-neutral-950/80 dark:to-neutral-900/80 backdrop-blur-xl flex-shrink-0"
      >

      {/* Header */}
      <div className="border-b border-neutral-900/5 dark:border-neutral-100/5 p-6 pb-5">
        <div className="flex items-center gap-2">
          <div className={cn(
            "w-2 h-2 rounded-full transition-colors",
            isActive ? "bg-accent-500 animate-pulse" : "bg-neutral-300"
          )} />
          <h2 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
            Reasoning
          </h2>
          {useUnifiedStream && (
            <span className="text-[10px] text-neutral-400 ml-auto">unified</span>
          )}
        </div>
      </div>

      {/* Error state (legacy mode only) */}
      {error && (
        <div className="p-6 pb-0">
          <div className="text-xs text-warning-600 dark:text-warning-400 bg-warning-50 dark:bg-warning-950/30 p-3 rounded">
            {error}
          </div>
        </div>
      )}

      <div className="overflow-y-auto max-h-[calc(100vh-200px)]">
        {/* Top Section: Thinking */}
        {reflection && reflection.text && (
          <div className="p-6 space-y-4">
            <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
              <span className="text-base">💭</span>
              <span className="text-xs uppercase tracking-wider font-medium">
                Thinking
              </span>
              {isActive && (
                <span className="ml-auto flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-accent-500 animate-pulse" />
                  <span className="w-1 h-1 rounded-full bg-accent-500 animate-pulse" style={{ animationDelay: '0.2s' }} />
                  <span className="w-1 h-1 rounded-full bg-accent-500 animate-pulse" style={{ animationDelay: '0.4s' }} />
                </span>
              )}
            </div>

            <div className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 space-y-3">
              {reflection.text.split('\n\n').map((paragraph, i) => (
                <p key={i}>{paragraph}</p>
              ))}
            </div>
          </div>
        )}

        {/* Divider - only show if both sections have content */}
        {reflection && backgroundActivity && (
          <div className="px-6">
            <div className="h-px bg-gradient-to-r from-transparent via-neutral-300 dark:via-neutral-700 to-transparent" />
          </div>
        )}

        {/* Bottom Section: Background Work (legacy mode only) */}
        {backgroundActivity && (
          <BackgroundSection
            activity={backgroundActivity}
            caseId={caseId}
            currentTopic={currentTopic}
            onViewGraph={() => setShowGraph(true)}
          />
        )}

        {/* Empty state */}
        {!reflection && !backgroundActivity && isActive && (
          <div className="p-6">
            <div className="flex items-center gap-2 text-neutral-400 dark:text-neutral-600 text-sm">
              <div className="w-1 h-1 rounded-full bg-neutral-400 animate-pulse" />
              <div className="w-1 h-1 rounded-full bg-neutral-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
              <div className="w-1 h-1 rounded-full bg-neutral-400 animate-pulse" style={{ animationDelay: '0.4s' }} />
              <span className="ml-2">Analyzing...</span>
            </div>
          </div>
        )}

        {/* Waiting state (unified mode, no reflection yet) */}
        {useUnifiedStream && !reflection && !isActive && (
          <div className="p-6">
            <div className="text-sm text-neutral-400 dark:text-neutral-600">
              Reflection will appear when you send a message...
            </div>
          </div>
        )}
      </div>
    </div>
    </>
  );
}

function QuietMode({
  reflection,
  backgroundActivity,
  onExpand,
  caseId,
  onViewGraph,
}: {
  reflection: any;
  backgroundActivity: BackgroundActivity | null;
  onExpand: () => void;
  caseId?: string | null;
  onViewGraph?: () => void;
}) {
  // Extract key stats
  const signalsCount = backgroundActivity?.signals_extracted.count || 0;
  const ungoundedCount = reflection?.patterns?.ungrounded_assumptions?.length || 0;
  const questionsCount = reflection?.patterns?.missing_considerations?.length || 0;

  // Get top claim/insight from reflection
  const topClaim = reflection?.patterns?.strong_claims?.[0];
  const topInsight = reflection?.text.split('\n\n')[0]; // First paragraph

  return (
    <div className="p-5 space-y-4">
      {/* Minimal stats */}
      <div className="space-y-1 text-xs text-neutral-600 dark:text-neutral-400">
        <div className="text-[11px] uppercase tracking-wider text-neutral-400 dark:text-neutral-600 mb-2">
          In this thread
        </div>

        {signalsCount > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-neutral-400">✓</span>
            <span>{signalsCount} claim{signalsCount !== 1 ? 's' : ''}</span>
          </div>
        )}

        {ungoundedCount > 0 && (
          <div className="flex items-center gap-2 text-warning-600 dark:text-warning-500">
            <span className="text-warning-400">⚠</span>
            <span>{ungoundedCount} ungrounded</span>
          </div>
        )}

        {questionsCount > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-neutral-400">?</span>
            <span>{questionsCount} open</span>
          </div>
        )}
      </div>

      {/* Top claim or insight */}
      {(topClaim || topInsight) && (
        <>
          <div className="h-px bg-neutral-200/50 dark:bg-neutral-800/50" />

          <div className="space-y-1">
            <p className="text-sm text-neutral-800 dark:text-neutral-200 leading-relaxed line-clamp-2">
              {topClaim?.text || topInsight}
            </p>
            {topClaim && (
              <div className="flex items-center gap-2 text-[11px] text-neutral-500">
                <span className="font-medium tabular-nums">
                  {Math.round(topClaim.avg_confidence * 100)}%
                </span>
              </div>
            )}
          </div>
        </>
      )}

      {/* Expand button */}
      <button
        onClick={onExpand}
        className="text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
      >
        Expand insights →
      </button>
    </div>
  );
}

function BackgroundSection({
  activity,
  caseId,
  currentTopic,
  onViewGraph
}: {
  activity: BackgroundActivity;
  caseId?: string | null;
  currentTopic?: string | null;
  onViewGraph?: () => void;
}) {
  // Helper to check if item is relevant to current topic
  const isRelevant = (text: string) => {
    if (!currentTopic) return false;
    return text.toLowerCase().includes(currentTopic.toLowerCase()) ||
           currentTopic.toLowerCase().includes(text.toLowerCase().substring(0, 20));
  };
  const hasActivity =
    activity.signals_extracted.count > 0 ||
    activity.evidence_linked.count > 0 ||
    activity.connections_built.count > 0 ||
    activity.confidence_updates.length > 0;

  if (!hasActivity) {
    return null;
  }

  return (
    <div className="p-6 pt-5 space-y-4">
      <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
        <span className="text-base">⚙️</span>
        <span className="text-xs uppercase tracking-wider font-medium">
          Background
        </span>
      </div>

      <div className="space-y-3 text-[13px] leading-relaxed text-neutral-600 dark:text-neutral-400">
        {/* Signals extracted - Visual */}
        {activity.signals_extracted.count > 0 && (
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-neutral-400">
                {Array.from({ length: Math.min(activity.signals_extracted.count, 5) }).map((_, i) => (
                  <span key={i} className="inline-block">●</span>
                ))}
                {activity.signals_extracted.count > 5 && '...'}
              </span>
              <span>{activity.signals_extracted.count} signal{activity.signals_extracted.count !== 1 ? 's' : ''}</span>
            </div>
            {activity.signals_extracted.items.length > 0 && (
              <div className="pl-4 space-y-0.5">
                {activity.signals_extracted.items.map((item, i) => {
                  const relevant = isRelevant(item.text);
                  return (
                    <div
                      key={i}
                      className={cn(
                        "text-xs transition-all duration-200 flex items-start gap-1",
                        relevant
                          ? "text-primary-600 dark:text-primary-400 font-medium"
                          : "text-neutral-500 dark:text-neutral-500"
                      )}
                    >
                      {relevant && <span className="text-sm">⚡</span>}
                      <span className="line-clamp-1">{item.text}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Evidence linked - Visual bar */}
        {activity.evidence_linked.count > 0 && (
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-success-500 dark:bg-success-600 transition-all"
                  style={{ width: `${Math.min(activity.evidence_linked.count * 20, 100)}%` }}
                />
              </div>
              <span>{activity.evidence_linked.count} evidence</span>
            </div>
            {activity.evidence_linked.sources.length > 0 && (
              <div className="pl-2 text-xs text-neutral-500">
                from {activity.evidence_linked.sources.slice(0, 2).join(', ')}
                {activity.evidence_linked.sources.length > 2 && ` +${activity.evidence_linked.sources.length - 2}`}
              </div>
            )}
          </div>
        )}

        {/* Connections built - Graph symbol */}
        {activity.connections_built.count > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-neutral-400 text-base">╱╲</span>
            <span>{activity.connections_built.count} connection{activity.connections_built.count !== 1 ? 's' : ''}</span>
          </div>
        )}

        {/* Confidence updates */}
        {activity.confidence_updates.length > 0 && (
          <div className="space-y-2 mt-3">
            {activity.confidence_updates.map((update, i) => {
              const relevant = isRelevant(update.title);
              return (
                <ConfidenceUpdate
                  key={i}
                  update={update}
                  highlighted={relevant}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function ConfidenceUpdate({
  update,
  highlighted = false
}: {
  update: { inquiry_id: string; title: string; old: number | null; new: number };
  highlighted?: boolean;
}) {
  const [showTimeline, setShowTimeline] = useState(false);
  const [timeline, setTimeline] = useState<Array<{ confidence: number; reason: string; timestamp: string }> | null>(null);

  const hasChange = update.old !== null;
  const direction = hasChange && update.new > update.old! ? 'up' : 'down';
  const delta = hasChange ? Math.abs(update.new - update.old!) : null;

  const loadTimeline = async () => {
    if (timeline) {
      setShowTimeline(!showTimeline);
      return;
    }

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/inquiries/${update.inquiry_id}/confidence-history/`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setTimeline(data);
        setShowTimeline(true);
      }
    } catch (err) {
      console.error('Failed to load confidence timeline:', err);
    }
  };

  return (
    <div className={cn(
      "space-y-1 transition-all duration-200",
      highlighted && "bg-primary-50/50 dark:bg-primary-950/20 -mx-2 px-2 py-1 rounded"
    )}>
      <div className={cn(
        "text-[13px] transition-colors",
        highlighted
          ? "text-primary-700 dark:text-primary-300 font-medium"
          : "text-neutral-700 dark:text-neutral-300"
      )}>
        {highlighted && <span className="mr-1">⚡</span>}
        {update.title}
      </div>

      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs">
          {hasChange && (
            <>
              <span className="text-neutral-500 tabular-nums">
                {Math.round(update.old! * 100)}%
              </span>
              <span className="text-neutral-400">→</span>
            </>
          )}
          <span className={cn(
            "font-medium tabular-nums",
            hasChange
              ? direction === 'up'
                ? "text-success-600 dark:text-success-400"
                : "text-warning-600 dark:text-warning-400"
              : "text-neutral-700 dark:text-neutral-300"
          )}>
            {Math.round(update.new * 100)}%
          </span>
          {hasChange && delta && (
            <span className="text-neutral-400">
              {direction === 'up' ? '↑' : '↓'} {Math.round(delta * 100)}%
            </span>
          )}
        </div>

        <button
          onClick={loadTimeline}
          className="text-[10px] text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
        >
          {showTimeline ? '−' : '+'}
        </button>
      </div>

      {/* Timeline visualization */}
      {showTimeline && timeline && timeline.length > 0 && (
        <div className="mt-2 pl-2 border-l-2 border-neutral-200 dark:border-neutral-800 space-y-2">
          {timeline.map((entry, i) => (
            <div key={i} className="text-[11px] space-y-0.5">
              <div className="flex items-center gap-2">
                <span className="font-medium tabular-nums text-neutral-700 dark:text-neutral-300">
                  {Math.round(entry.confidence * 100)}%
                </span>
                <span className="text-neutral-400">
                  {new Date(entry.timestamp).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric'
                  })}
                </span>
              </div>
              <div className="text-neutral-500 dark:text-neutral-500">
                {entry.reason}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
