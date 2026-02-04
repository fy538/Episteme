/**
 * AgenticTaskDialog - UI for executing complex document editing tasks
 *
 * Shows:
 * - Task input
 * - Planning/execution progress
 * - Step-by-step plan with status
 * - Diff preview
 * - Review score and notes
 * - Accept/reject controls
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  SparklesIcon,
  PlayIcon,
  CheckIcon,
  XMarkIcon,
  ChevronRightIcon,
  DocumentTextIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useAgenticTask } from '@/hooks/useAgenticTask';

interface AgenticTaskDialogProps {
  documentId: string;
  isOpen: boolean;
  onClose: () => void;
  onApplied: () => void;
}

export function AgenticTaskDialog({
  documentId,
  isOpen,
  onClose,
  onApplied,
}: AgenticTaskDialogProps) {
  const [taskInput, setTaskInput] = useState('');

  const {
    phase,
    result,
    error,
    isRunning,
    executeTask,
    applyResult,
    discardResult,
    reset,
    plan,
    diffSummary,
    reviewScore,
    reviewNotes,
  } = useAgenticTask({
    documentId,
    onSuccess: () => {},
    onError: (err) => console.error('Task error:', err),
  });

  if (!isOpen) return null;

  const handleExecute = async () => {
    if (!taskInput.trim()) return;
    await executeTask(taskInput);
  };

  const handleApply = async () => {
    await applyResult();
    onApplied();
    onClose();
  };

  const handleDiscard = () => {
    discardResult();
    setTaskInput('');
  };

  const handleClose = () => {
    reset();
    setTaskInput('');
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SparklesIcon className="w-5 h-5 text-accent-500" />
            <h2 className="text-lg font-semibold text-neutral-900">
              AI Document Task
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1 text-neutral-400 hover:text-neutral-600"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {/* Task input (idle state) */}
          {phase === 'idle' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Describe what you want to do
                </label>
                <Textarea
                  value={taskInput}
                  onChange={(e) => setTaskInput(e.target.value)}
                  placeholder="e.g., Add citations to all claims, rewrite the risks section to be more specific, restructure the brief to follow the MECE framework..."
                  rows={4}
                  className="w-full"
                />
              </div>

              {/* Example tasks */}
              <div>
                <p className="text-xs text-neutral-500 mb-2">Examples:</p>
                <div className="flex flex-wrap gap-2">
                  {EXAMPLE_TASKS.map((task) => (
                    <button
                      key={task}
                      onClick={() => setTaskInput(task)}
                      className="text-xs px-2 py-1 bg-neutral-100 hover:bg-neutral-200 rounded text-neutral-600 transition-colors"
                    >
                      {task}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Progress (running state) */}
          {isRunning && (
            <div className="space-y-6">
              {/* Phase indicator */}
              <div className="flex items-center justify-center gap-4">
                <PhaseStep
                  label="Planning"
                  active={phase === 'planning'}
                  complete={phase !== 'planning'}
                />
                <ChevronRightIcon className="w-4 h-4 text-neutral-300" />
                <PhaseStep
                  label="Executing"
                  active={phase === 'executing'}
                  complete={phase === 'reviewing'}
                />
                <ChevronRightIcon className="w-4 h-4 text-neutral-300" />
                <PhaseStep
                  label="Reviewing"
                  active={phase === 'reviewing'}
                  complete={false}
                />
              </div>

              {/* Plan steps */}
              {plan.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-neutral-700">
                    Execution Plan:
                  </p>
                  {plan.map((step, idx) => (
                    <div
                      key={step.id}
                      className={`flex items-start gap-3 p-3 rounded-lg ${
                        step.status === 'completed'
                          ? 'bg-success-50'
                          : step.status === 'failed'
                          ? 'bg-error-50'
                          : 'bg-neutral-50'
                      }`}
                    >
                      <span className="text-xs font-medium text-neutral-400 mt-0.5">
                        {idx + 1}
                      </span>
                      <div className="flex-1">
                        <p className="text-sm text-neutral-800">
                          {step.description}
                        </p>
                        {step.target_section && (
                          <p className="text-xs text-neutral-500 mt-0.5">
                            Target: {step.target_section}
                          </p>
                        )}
                      </div>
                      <StatusBadge status={step.status} />
                    </div>
                  ))}
                </div>
              )}

              {/* Loading animation */}
              <div className="flex items-center justify-center py-4">
                <ArrowPathIcon className="w-6 h-6 text-accent-500 animate-spin" />
              </div>
            </div>
          )}

          {/* Result (completed state) */}
          {phase === 'completed' && result && (
            <div className="space-y-6">
              {/* Review score */}
              <div className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-neutral-700">
                    Review Score
                  </p>
                  <p className="text-xs text-neutral-500">{reviewNotes}</p>
                </div>
                <div className="text-3xl font-bold text-accent-600">
                  {reviewScore}
                </div>
              </div>

              {/* Diff summary */}
              <div>
                <p className="text-sm font-medium text-neutral-700 mb-2">
                  Changes Made
                </p>
                <p className="text-sm text-neutral-600">{diffSummary}</p>
              </div>

              {/* Plan completion */}
              <div>
                <p className="text-sm font-medium text-neutral-700 mb-2">
                  Completed Steps
                </p>
                <div className="space-y-1">
                  {plan.map((step) => (
                    <div
                      key={step.id}
                      className="flex items-center gap-2 text-sm"
                    >
                      {step.status === 'completed' ? (
                        <CheckIcon className="w-4 h-4 text-success-500" />
                      ) : (
                        <XMarkIcon className="w-4 h-4 text-error-500" />
                      )}
                      <span
                        className={
                          step.status === 'completed'
                            ? 'text-neutral-700'
                            : 'text-error-600'
                        }
                      >
                        {step.description}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Preview toggle */}
              <details className="group">
                <summary className="cursor-pointer text-sm font-medium text-accent-600 hover:text-accent-700">
                  Preview final content
                </summary>
                <div className="mt-2 p-3 bg-neutral-50 rounded-lg max-h-60 overflow-auto">
                  <pre className="text-xs text-neutral-700 whitespace-pre-wrap">
                    {result.final_content.slice(0, 2000)}
                    {result.final_content.length > 2000 && '...'}
                  </pre>
                </div>
              </details>
            </div>
          )}

          {/* Error state */}
          {phase === 'failed' && (
            <div className="text-center py-8">
              <XMarkIcon className="w-12 h-12 text-error-500 mx-auto mb-3" />
              <p className="text-neutral-700 font-medium">Task Failed</p>
              <p className="text-sm text-neutral-500 mt-1">{error}</p>
              <Button onClick={reset} variant="outline" className="mt-4">
                Try Again
              </Button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex items-center justify-between">
          {phase === 'idle' && (
            <>
              <Button variant="ghost" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                onClick={handleExecute}
                disabled={!taskInput.trim()}
                className="flex items-center gap-2"
              >
                <PlayIcon className="w-4 h-4" />
                Execute Task
              </Button>
            </>
          )}

          {isRunning && (
            <div className="w-full text-center text-sm text-neutral-500">
              Processing... This may take a moment.
            </div>
          )}

          {phase === 'completed' && (
            <>
              <Button variant="ghost" onClick={handleDiscard}>
                Discard Changes
              </Button>
              <Button onClick={handleApply} className="flex items-center gap-2">
                <CheckIcon className="w-4 h-4" />
                Apply Changes
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// Sub-components

function PhaseStep({
  label,
  active,
  complete,
}: {
  label: string;
  active: boolean;
  complete: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
        active
          ? 'bg-accent-100 text-accent-700'
          : complete
          ? 'bg-success-100 text-success-700'
          : 'bg-neutral-100 text-neutral-500'
      }`}
    >
      {complete && <CheckIcon className="w-4 h-4" />}
      {active && <ArrowPathIcon className="w-4 h-4 animate-spin" />}
      <span>{label}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return (
        <Badge variant="default" className="bg-success-100 text-success-700">
          Done
        </Badge>
      );
    case 'in_progress':
      return (
        <Badge variant="neutral">
          <ArrowPathIcon className="w-3 h-3 animate-spin mr-1" />
          Running
        </Badge>
      );
    case 'failed':
      return <Badge variant="error">Failed</Badge>;
    default:
      return <Badge variant="neutral">Pending</Badge>;
  }
}

// Example tasks
const EXAMPLE_TASKS = [
  'Add citations to all claims',
  'Rewrite risks section',
  'Strengthen the conclusion',
  'Add executive summary',
  'Fix logical inconsistencies',
];
