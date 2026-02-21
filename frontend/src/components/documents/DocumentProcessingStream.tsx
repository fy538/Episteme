/**
 * Real-time document processing progress indicator.
 *
 * Streams progress from the backend via SSE and shows stage-by-stage
 * updates with a progress bar and running counts.
 *
 * Two-phase pipeline:
 * - Phase 1 (user-facing, ~15-30s): chunk → embed → extract structure → done
 * - Phase 2 (background): integration with existing graph (no user wait)
 *
 * Features:
 * - 5-stage progress indicator with color transitions
 * - Running counts (chunks, claims, etc.)
 * - Retry button on failure
 * - Cancel link during processing
 * - Completion actions
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useDocumentProcessing } from '@/hooks/useDocumentProcessing';
import { Spinner } from '@/components/ui/spinner';
import { documentsAPI } from '@/lib/api/documents';
import type { ProcessingProgress } from '@/hooks/useDocumentProcessing';

interface DocumentProcessingStreamProps {
  documentId: string;
  onComplete?: () => void;
  onRetry?: () => void;
}

const STAGE_LABELS: Record<string, string> = {
  received: 'Received',
  chunking: 'Chunking',
  embedding: 'Embedding',
  extracting_graph: 'Structure',
  completed: 'Complete',
};

function ProgressBar({ stageIndex, totalStages }: { stageIndex: number; totalStages: number }) {
  const pct = Math.round((stageIndex / (totalStages - 1)) * 100);
  return (
    <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-1.5 overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500 ease-out bg-info-500 dark:bg-info-400"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function CountsDisplay({ counts }: { counts: Record<string, number> }) {
  const parts: string[] = [];
  if (counts.chunks) parts.push(`${counts.chunks} chunks`);
  if (counts.claims) parts.push(`${counts.claims} claims`);
  if (counts.assumptions) parts.push(`${counts.assumptions} assumptions`);
  if (counts.edges) parts.push(`${counts.edges} relationships`);
  if (counts.tensions) parts.push(`${counts.tensions} tensions`);

  if (parts.length === 0) return null;

  return (
    <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
      {parts.join(' \u00b7 ')}
    </p>
  );
}

function StageIndicator({ progress }: { progress: ProcessingProgress }) {
  return (
    <div className="flex items-center gap-2 text-xs text-neutral-400 dark:text-neutral-500 mt-2">
      {Object.entries(STAGE_LABELS).map(([key, label]) => {
        const stageOrder = ['received', 'chunking', 'embedding', 'extracting_graph', 'completed'];
        const currentIdx = stageOrder.indexOf(progress.stage);
        const thisIdx = stageOrder.indexOf(key);

        let color = 'text-neutral-300 dark:text-neutral-600';
        if (thisIdx < currentIdx) color = 'text-success-500 dark:text-success-400';
        if (thisIdx === currentIdx) color = 'text-info-500 dark:text-info-400 font-medium';

        return (
          <span key={key} className={color}>
            {label}
          </span>
        );
      })}
    </div>
  );
}

export function DocumentProcessingStream({ documentId, onComplete, onRetry }: DocumentProcessingStreamProps) {
  const { progress, isProcessing, isComplete, isFailed, error, abort } = useDocumentProcessing(documentId);
  const [retrying, setRetrying] = useState(false);

  // Notify parent on completion
  if (isComplete && onComplete) {
    onComplete();
  }

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await documentsAPI.reprocessDocument(documentId);
      onRetry?.();
      // The SSE will reconnect automatically when the component re-mounts
      window.location.reload(); // Simple approach — re-fetch everything
    } catch {
      // Fall back to just notifying parent
      onRetry?.();
    } finally {
      setRetrying(false);
    }
  };

  const handleCancel = () => {
    abort?.();
  };

  if (!progress) {
    return (
      <div className="mt-4 p-3 bg-neutral-50 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center gap-2">
          <Spinner className="text-accent-500" />
          <p className="text-sm text-neutral-600 dark:text-neutral-300">Connecting...</p>
        </div>
      </div>
    );
  }

  if (isFailed) {
    return (
      <div className="mt-4 p-3 bg-error-50 dark:bg-error-950/30 rounded-lg border border-error-200 dark:border-error-800">
        <p className="text-sm font-medium text-error-700 dark:text-error-300">Processing failed</p>
        {error && <p className="text-xs text-error-600 dark:text-error-400 mt-1">{error}</p>}
        <div className="flex items-center gap-3 mt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRetry}
            disabled={retrying}
            className="text-xs font-medium text-error-600 dark:text-error-400 hover:text-error-800 dark:hover:text-error-200 underline underline-offset-2 h-auto px-1"
          >
            {retrying ? 'Retrying...' : 'Retry'}
          </Button>
        </div>
      </div>
    );
  }

  if (isComplete) {
    return (
      <div className="mt-4 p-3 bg-success-50 dark:bg-success-950/30 rounded-lg border border-success-200 dark:border-success-800">
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-success-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <p className="text-sm font-medium text-success-700 dark:text-success-300">Processing complete</p>
        </div>
        <CountsDisplay counts={progress.counts} />
      </div>
    );
  }

  // Processing in progress
  return (
    <div className="mt-4 p-3 bg-info-50 dark:bg-info-950/20 rounded-lg border border-info-200 dark:border-info-800">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Spinner className="text-accent-500" />
          <p className="text-sm font-medium text-info-700 dark:text-info-300">
            {progress.stage_label}
          </p>
        </div>
        {abort && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCancel}
            className="text-xs text-info-500/60 hover:text-info-600 dark:text-info-400/60 dark:hover:text-info-300 h-auto px-1"
          >
            Cancel
          </Button>
        )}
      </div>
      <ProgressBar stageIndex={progress.stage_index} totalStages={progress.total_stages} />
      <CountsDisplay counts={progress.counts} />
      <StageIndicator progress={progress} />
    </div>
  );
}
