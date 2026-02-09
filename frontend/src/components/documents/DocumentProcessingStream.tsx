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
import { useDocumentProcessing } from '@/hooks/useDocumentProcessing';
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
        className="h-full rounded-full transition-all duration-500 ease-out bg-blue-500 dark:bg-blue-400"
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
        if (thisIdx < currentIdx) color = 'text-green-500 dark:text-green-400';
        if (thisIdx === currentIdx) color = 'text-blue-500 dark:text-blue-400 font-medium';

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
          <div className="h-4 w-4 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
          <p className="text-sm text-neutral-600 dark:text-neutral-300">Connecting...</p>
        </div>
      </div>
    );
  }

  if (isFailed) {
    return (
      <div className="mt-4 p-3 bg-red-50 dark:bg-red-950/30 rounded-lg border border-red-200 dark:border-red-800">
        <p className="text-sm font-medium text-red-700 dark:text-red-300">Processing failed</p>
        {error && <p className="text-xs text-red-600 dark:text-red-400 mt-1">{error}</p>}
        <div className="flex items-center gap-3 mt-2">
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="text-xs font-medium text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 underline underline-offset-2 disabled:opacity-50"
          >
            {retrying ? 'Retrying...' : 'Retry'}
          </button>
        </div>
      </div>
    );
  }

  if (isComplete) {
    return (
      <div className="mt-4 p-3 bg-green-50 dark:bg-green-950/30 rounded-lg border border-green-200 dark:border-green-800">
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <p className="text-sm font-medium text-green-700 dark:text-green-300">Processing complete</p>
        </div>
        <CountsDisplay counts={progress.counts} />
      </div>
    );
  }

  // Processing in progress
  return (
    <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
          <p className="text-sm font-medium text-blue-700 dark:text-blue-300">
            {progress.stage_label}
          </p>
        </div>
        {abort && (
          <button
            onClick={handleCancel}
            className="text-xs text-blue-500/60 hover:text-blue-600 dark:text-blue-400/60 dark:hover:text-blue-300 transition-colors"
          >
            Cancel
          </button>
        )}
      </div>
      <ProgressBar stageIndex={progress.stage_index} totalStages={progress.total_stages} />
      <CountsDisplay counts={progress.counts} />
      <StageIndicator progress={progress} />
    </div>
  );
}
