/**
 * ActivitySection - Shows active action progress or recent results
 *
 * Displays:
 * - Running action with progress bar and steps
 * - Completed action with result summary
 * - Expandable to see full details
 */

'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import type { ActiveAction } from '@/lib/types/companion';

function Spinner({ size = 'md' }: { size?: 'xs' | 'sm' | 'md' }) {
  const sizeClasses = {
    xs: 'w-3 h-3',
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
  };
  return (
    <span className={cn('inline-block animate-spin', sizeClasses[size])}>
      ◐
    </span>
  );
}

interface ActivitySectionProps {
  action: ActiveAction;
  onStop?: () => void;
  onDismiss?: () => void;
  onViewDetails?: () => void;
}

export function ActivitySection({
  action,
  onStop,
  onDismiss,
  onViewDetails,
}: ActivitySectionProps) {
  const [expanded, setExpanded] = useState(true);
  const isRunning = action.status === 'running';
  const isComplete = action.status === 'complete';
  const isError = action.status === 'error';

  return (
    <section className="border-b border-cyan-900/30">
      {/* Terminal Process Header */}
      <div className="px-3 py-2 flex items-center justify-between font-mono hover:bg-cyan-950/20 transition-colors">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 text-[10px]">{'>'}</span>
          <span
            className={cn(
              'text-[10px] font-medium tracking-wider uppercase',
              isRunning && 'text-cyan-400',
              isComplete && 'text-green-400',
              isError && 'text-red-400'
            )}
          >
            {isRunning && 'ACTIVE_PROCESS'}
            {isComplete && 'PROCESS_COMPLETE'}
            {isError && 'PROCESS_ERROR'}
          </span>
          {isRunning && <Spinner size="sm" />}
          {isComplete && <span className="text-green-400 text-[10px]">[✓]</span>}
          {isError && <span className="text-red-400 text-[10px]">[✗]</span>}
        </div>
        <div className="flex items-center gap-2">
          {isRunning && onStop && (
            <button
              onClick={onStop}
              className="text-[10px] px-2 py-0.5 border border-cyan-800 text-cyan-400 hover:bg-cyan-950/50 font-mono"
            >
              KILL
            </button>
          )}
          {(isComplete || isError) && onDismiss && (
            <button
              onClick={onDismiss}
              className="text-[10px] text-cyan-600 hover:text-cyan-400 font-mono"
            >
              [X]
            </button>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-[10px] text-cyan-600 hover:text-cyan-400 font-mono"
          >
            {expanded ? '[▲]' : '[▼]'}
          </button>
        </div>
      </div>

      {/* Terminal Content */}
      {expanded && (
        <div className="px-3 pb-3 space-y-2 font-mono">
          {/* Process info */}
          <div className="border border-cyan-900/30 bg-cyan-950/10 p-2 text-[10px]">
            <div className="text-cyan-500 mb-1">
              <span className="text-cyan-700">▸ target:</span> "{action.target}"
            </div>

            {/* Progress bar (running) */}
            {isRunning && (
              <div className="space-y-1">
                <div className="text-cyan-700">
                  ▸ progress: {action.progress}%
                </div>
                <div className="text-cyan-400">
                  {Array.from({ length: 20 }).map((_, i) => (
                    <span key={i}>
                      {i < Math.floor(action.progress / 5) ? '█' : '░'}
                    </span>
                  ))}
                </div>

                {/* Steps */}
                <div className="mt-2 space-y-0.5 text-[10px]">
                  {action.steps.map((step) => (
                    <div key={step.id} className="flex items-center gap-2">
                      {step.status === 'complete' && (
                        <span className="text-green-400">✓</span>
                      )}
                      {step.status === 'running' && (
                        <Spinner size="xs" />
                      )}
                      {step.status === 'pending' && (
                        <span className="text-cyan-800">○</span>
                      )}
                      {step.status === 'error' && <span className="text-red-400">✗</span>}
                      <span
                        className={cn(
                          step.status === 'complete' && 'text-cyan-600',
                          step.status === 'running' && 'text-cyan-400',
                          step.status === 'pending' && 'text-cyan-800',
                          step.status === 'error' && 'text-red-400'
                        )}
                      >
                        {step.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

          {/* Result (complete) */}
          {isComplete && action.result && (
            <div className="space-y-1">
              {/* Verdict */}
              {action.result.verdict && (
                <div className="text-cyan-700 text-[10px]">
                  <span className="text-cyan-800">▸ verdict:</span>{' '}
                  <span
                    className={cn(
                      'font-medium tracking-wider uppercase',
                      action.result.verdict === 'true' && 'text-green-400',
                      action.result.verdict === 'false' && 'text-red-400',
                      action.result.verdict === 'partial' && 'text-amber-400'
                    )}
                  >
                    {action.result.verdict === 'true' && '[VALIDATED]'}
                    {action.result.verdict === 'false' && '[REFUTED]'}
                    {action.result.verdict === 'partial' && '[PARTIAL]'}
                  </span>
                </div>
              )}

              {/* Summary */}
              <div className="text-cyan-700 text-[10px]">
                <span className="text-cyan-800">▸ summary:</span>
              </div>
              <p className="text-[10px] text-cyan-400 leading-relaxed pl-4 border-l-2 border-cyan-900/50">
                {action.result.summary}
              </p>

              {/* Sources */}
              {action.result.sources && action.result.sources.length > 0 && (
                <div className="mt-2">
                  <div className="text-cyan-700 text-[10px]">
                    <span className="text-cyan-800">▸ sources:</span>
                  </div>
                  <div className="space-y-0.5 pl-4">
                    {action.result.sources.slice(0, 3).map((source, i) => (
                      <div key={i} className="flex items-center gap-1 text-[10px]">
                        <span className="text-cyan-800">•</span>
                        {source.url ? (
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-cyan-500 hover:text-cyan-300 flex items-center gap-1"
                          >
                            {source.title}
                            <span className="text-[9px]">↗</span>
                          </a>
                        ) : (
                          <span className="text-cyan-600">
                            {source.title}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* View details link */}
              {onViewDetails && (
                <button
                  onClick={onViewDetails}
                  className="text-[10px] text-cyan-500 hover:text-cyan-300 mt-2"
                >
                  [VIEW_FULL_ANALYSIS] →
                </button>
              )}
            </div>
          )}

          {/* Error */}
          {isError && action.error && (
            <div className="space-y-1">
              <div className="text-red-700 text-[10px]">
                <span className="text-red-800">▸ error:</span>
              </div>
              <p className="text-[10px] text-red-400 leading-relaxed pl-4 border-l-2 border-red-900/50">
                {action.error}
              </p>
            </div>
          )}
          </div>
        </div>
      )}
    </section>
  );
}
