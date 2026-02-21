/**
 * Cost Summary Component
 *
 * Displays a compact cost breakdown for an agent workflow.
 * Extracts data from the AgentTrajectory event's payload, which contains:
 *   - total_cost_usd, total_tokens_used, total_steps
 *   - Per-step breakdown (step_name, tokens_used, cost_usd, duration_ms)
 *
 * Can be used standalone with a correlationId (auto-fetches) or with
 * pre-loaded event data.
 */

'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { eventsAPI, type EventItem } from '@/lib/api/events';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface CostSummaryProps {
  /** Correlation ID to auto-fetch events (preferred) */
  correlationId?: string;
  /** Pre-loaded events (alternative to correlationId) */
  events?: EventItem[];
  /** Additional CSS classes */
  className?: string;
  /** Compact mode hides per-step breakdown by default */
  compact?: boolean;
}

interface CostData {
  totalCostUsd: number;
  totalTokensUsed: number;
  totalSteps: number;
  totalDurationMs: number;
  model?: string;
  steps: StepCost[];
}

interface StepCost {
  name: string;
  tokensUsed: number;
  costUsd: number;
  durationMs: number;
}

/* ------------------------------------------------------------------ */
/*  Data extraction                                                   */
/* ------------------------------------------------------------------ */

function extractCostData(events: EventItem[]): CostData | null {
  // Find the AgentTrajectory event — it contains the full cost breakdown
  const trajectory = events.find(e => e.type === 'AgentTrajectory');
  if (!trajectory?.payload) return null;

  const payload = trajectory.payload;
  const steps: StepCost[] = (payload.events || []).map((step: any) => ({
    name: step.step_name || 'unknown',
    tokensUsed: step.tokens_used || 0,
    costUsd: step.cost_usd || 0,
    durationMs: step.duration_ms || 0,
  }));

  return {
    totalCostUsd: payload.total_cost_usd || steps.reduce((sum, s) => sum + s.costUsd, 0),
    totalTokensUsed: payload.total_tokens_used || steps.reduce((sum, s) => sum + s.tokensUsed, 0),
    totalSteps: payload.total_steps || steps.length,
    totalDurationMs: payload.total_duration_ms || steps.reduce((sum, s) => sum + s.durationMs, 0),
    model: payload.model || undefined,
    steps,
  };
}

/* ------------------------------------------------------------------ */
/*  Main component                                                    */
/* ------------------------------------------------------------------ */

export function CostSummary({ correlationId, events: propEvents, className, compact = false }: CostSummaryProps) {
  const [expanded, setExpanded] = useState(!compact);

  // Auto-fetch if correlationId provided and no events passed
  const { data: fetchedEvents = [] } = useQuery({
    queryKey: ['workflow-events', correlationId],
    queryFn: () => eventsAPI.getWorkflowEvents(correlationId!),
    enabled: !!correlationId && !propEvents,
  });

  const events = propEvents || fetchedEvents;
  const costData = useMemo(() => extractCostData(events), [events]);

  if (!costData) {
    if (correlationId && !propEvents) {
      // Still loading or no data yet
      return null;
    }
    return null;
  }

  return (
    <div className={cn(
      'rounded-lg border border-neutral-200/80 dark:border-neutral-800/80',
      'bg-white dark:bg-primary-900',
      className,
    )}>
      {/* Summary header (always visible) */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={cn(
          'w-full flex items-center justify-between px-4 py-3',
          'hover:bg-neutral-50 dark:hover:bg-neutral-800/30',
          'transition-colors rounded-lg',
          compact && 'cursor-pointer',
        )}
      >
        <div className="flex items-center gap-3">
          {/* Cost icon */}
          <div className="flex items-center justify-center w-7 h-7 rounded-md bg-accent-50 dark:bg-accent-900/30">
            <svg
              className="w-4 h-4 text-accent-600 dark:text-accent-400"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="12" y1="1" x2="12" y2="23" strokeLinecap="round" />
              <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>

          <div className="text-left">
            <p className="text-sm font-medium text-primary-900 dark:text-primary-50">
              Generation Cost
            </p>
            <p className="text-xs text-neutral-400 dark:text-neutral-500">
              {costData.totalSteps} steps &middot; {formatDuration(costData.totalDurationMs)}
              {costData.model && <> &middot; {costData.model}</>}
            </p>
          </div>
        </div>

        {/* Total cost + tokens */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm font-semibold tabular-nums text-primary-900 dark:text-primary-50">
              ${costData.totalCostUsd.toFixed(4)}
            </p>
            <p className="text-xs tabular-nums text-neutral-400 dark:text-neutral-500">
              {formatTokens(costData.totalTokensUsed)} tokens
            </p>
          </div>

          {/* Expand chevron */}
          {compact && (
            <svg
              className={cn(
                'w-4 h-4 text-neutral-400 transition-transform',
                expanded && 'rotate-180',
              )}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polyline points="6 9 12 15 18 9" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </div>
      </button>

      {/* Per-step breakdown */}
      {expanded && costData.steps.length > 0 && (
        <div className="px-4 pb-3">
          <div className="border-t border-neutral-100 dark:border-neutral-800/60 pt-3">
            {/* Column headers */}
            <div className="flex items-center gap-2 mb-1.5 px-1">
              <span className="flex-1 text-xs font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider">
                Step
              </span>
              <span className="w-16 text-right text-xs font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider">
                Duration
              </span>
              <span className="w-16 text-right text-xs font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider">
                Tokens
              </span>
              <span className="w-16 text-right text-xs font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider">
                Cost
              </span>
            </div>

            {/* Rows */}
            {costData.steps.map((step, idx) => (
              <StepCostRow key={`${step.name}-${idx}`} step={step} total={costData.totalCostUsd} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Per-step row                                                      */
/* ------------------------------------------------------------------ */

function StepCostRow({ step, total }: { step: StepCost; total: number }) {
  const pct = total > 0 ? (step.costUsd / total) * 100 : 0;

  return (
    <div className="flex items-center gap-2 py-1 px-1 rounded hover:bg-neutral-50 dark:hover:bg-neutral-800/20 transition-colors">
      {/* Step name + cost bar */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs text-primary-800 dark:text-primary-200 capitalize truncate">
            {step.name}
          </span>
        </div>
        {/* Proportional cost bar */}
        <div className="mt-0.5 h-1 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-accent-400 dark:bg-accent-500 transition-all"
            style={{ width: `${Math.max(pct, 2)}%` }}
          />
        </div>
      </div>

      {/* Duration */}
      <span className="w-16 text-right text-xs tabular-nums text-neutral-500 dark:text-neutral-400">
        {formatDuration(step.durationMs)}
      </span>

      {/* Tokens */}
      <span className="w-16 text-right text-xs tabular-nums text-neutral-500 dark:text-neutral-400">
        {formatTokens(step.tokensUsed)}
      </span>

      {/* Cost */}
      <span className="w-16 text-right text-xs tabular-nums text-neutral-500 dark:text-neutral-400">
        ${step.costUsd.toFixed(4)}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Formatting helpers                                                */
/* ------------------------------------------------------------------ */

function formatDuration(ms: number): string {
  if (ms === 0) return '-';
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m${rem}s`;
}

function formatTokens(n: number): string {
  if (n === 0) return '-';
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}
