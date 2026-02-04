/**
 * ReadinessPanel - Slide-in panel for decision readiness
 *
 * Shows:
 * - Evidence landscape (counts, not scores)
 * - User's self-assessed confidence
 * - User-defined readiness checklist
 * - Blind spot prompts
 *
 * Philosophy: User judges readiness, system shows evidence.
 */

'use client';

import { XMarkIcon } from '@heroicons/react/24/outline';
import { EvidenceLandscape } from '@/components/cases/EvidenceLandscape';
import { UserConfidenceInput } from '@/components/cases/UserConfidenceInput';
import { ReadinessChecklist } from '@/components/cases/ReadinessChecklist';
import { BlindSpotPrompts } from '@/components/cases/BlindSpotPrompts';
import type { Case } from '@/lib/types/case';

interface ReadinessPanelProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseData?: Case;
  onReadyClick?: () => void;
  onCreateInquiry?: (text: string) => void;
}

export function ReadinessPanel({
  isOpen,
  onClose,
  caseId,
  caseData,
  onReadyClick,
  onCreateInquiry,
}: ReadinessPanelProps) {
  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/10 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div
        className={`
          fixed top-0 left-0 h-full w-full max-w-md
          bg-white shadow-2xl z-50
          transform transition-transform duration-300 ease-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-neutral-200 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">Ready to decide?</h2>
            <p className="text-sm text-neutral-500">
              Review your evidence and assess your confidence
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-neutral-400 hover:text-neutral-600 rounded-lg hover:bg-neutral-100"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto h-[calc(100%-80px)] p-6 space-y-6">
          {/* Evidence Landscape - what do you have? */}
          <div>
            <h3 className="text-sm font-medium text-neutral-700 mb-3">What you have</h3>
            <EvidenceLandscape caseId={caseId} />
          </div>

          {/* User Confidence - how confident are you? */}
          <div>
            <h3 className="text-sm font-medium text-neutral-700 mb-3">Your assessment</h3>
            <UserConfidenceInput
              caseId={caseId}
              initialConfidence={caseData?.user_confidence}
              initialWhatWouldChange={caseData?.what_would_change_mind}
            />
          </div>

          {/* Readiness Checklist - what needs to be true? */}
          <div>
            <h3 className="text-sm font-medium text-neutral-700 mb-3">Readiness criteria</h3>
            <ReadinessChecklist
              caseId={caseId}
              onReadyClick={onReadyClick}
              onNotYetClick={onClose}
            />
          </div>

          {/* Blind Spot Prompts - what might you be missing? */}
          <div>
            <h3 className="text-sm font-medium text-neutral-700 mb-3">Consider</h3>
            <BlindSpotPrompts
              caseId={caseId}
              onCreateInquiry={onCreateInquiry}
              maxPrompts={3}
            />
          </div>

          {/* Philosophy note */}
          <div className="p-4 bg-neutral-50 rounded-lg">
            <p className="text-xs text-neutral-500">
              Only you can decide when you're ready. The system shows what you have
              and surfaces what you might be missing, but the judgment is yours.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
