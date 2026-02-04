/**
 * CanvasControls - Control panel for the decision canvas
 *
 * Provides:
 * - Quick actions (add inquiry, view brief, signals)
 * - Readiness assessment button (no score)
 * - Stats summary
 */

'use client';

import { Button } from '@/components/ui/button';
import {
  PlusIcon,
  DocumentTextIcon,
  SignalIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

interface CanvasControlsProps {
  onAddInquiry: () => void;
  onOpenBrief: () => void;
  onOpenSignals?: () => void;
  onOpenReadiness?: () => void;
  inquiryCount: number;
  openCount: number;
  resolvedCount?: number;
  signalCount?: number;
}

export function CanvasControls({
  onAddInquiry,
  onOpenBrief,
  onOpenSignals,
  onOpenReadiness,
  inquiryCount,
  openCount,
  resolvedCount = 0,
  signalCount = 0,
}: CanvasControlsProps) {
  return (
    <div className="flex flex-col gap-2">
      {/* Primary actions */}
      <div className="bg-white/90 backdrop-blur rounded-xl shadow-lg border border-neutral-200 p-2">
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={onOpenBrief}
            className="flex items-center gap-2"
          >
            <DocumentTextIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Brief</span>
          </Button>

          <div className="w-px h-6 bg-neutral-200" />

          <Button
            size="sm"
            onClick={onAddInquiry}
            className="flex items-center gap-2"
          >
            <PlusIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Inquiry</span>
          </Button>
        </div>
      </div>

      {/* Signals button */}
      {onOpenSignals && (
        <button
          onClick={onOpenSignals}
          className="bg-white/90 backdrop-blur rounded-xl shadow-lg border border-neutral-200 p-2.5 hover:bg-white transition-colors flex items-center gap-2"
          title="View Signals"
        >
          <SignalIcon className="w-5 h-5 text-purple-600" />
          {signalCount > 0 && (
            <span className="text-xs font-medium text-purple-600">{signalCount}</span>
          )}
        </button>
      )}

      {/* Readiness button - opens assessment panel, no score shown */}
      {onOpenReadiness && (
        <button
          onClick={onOpenReadiness}
          className="bg-white/90 backdrop-blur rounded-xl shadow-lg border border-neutral-200 p-3 hover:bg-white transition-colors"
          title="Am I ready to decide?"
        >
          <div className="flex items-center gap-2">
            <CheckCircleIcon className="w-5 h-5 text-accent-600" />
            <div className="text-left">
              <div className="text-xs font-medium text-neutral-700">Ready?</div>
              <div className="text-xs text-neutral-500">
                Assess readiness
              </div>
            </div>
          </div>
        </button>
      )}

      {/* Quick stats - inquiry counts */}
      <div className="bg-white/90 backdrop-blur rounded-xl shadow-lg border border-neutral-200 p-3">
        <div className="text-xs text-neutral-500 mb-1">Inquiries</div>
        <div className="flex items-baseline gap-1">
          <span className="text-2xl font-bold text-neutral-900">{openCount}</span>
          <span className="text-neutral-400">open</span>
        </div>
        {resolvedCount > 0 && (
          <div className="text-xs text-green-600 mt-1">
            {resolvedCount} resolved
          </div>
        )}
      </div>
    </div>
  );
}
