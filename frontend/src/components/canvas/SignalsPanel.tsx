/**
 * SignalsPanel - Slide-in panel for viewing signals in canvas
 *
 * Shows signal graph visualization with filtering and detail view.
 */

'use client';

import { XMarkIcon } from '@heroicons/react/24/outline';
import { SignalGraphView } from '@/components/cases/SignalGraphView';

interface Signal {
  id: string;
  type: 'claim' | 'assumption' | 'evidence' | 'question' | 'constraint' | 'goal';
  text: string;
  strength: number;
  validation_status?: 'validated' | 'unvalidated' | 'contradicted' | 'pending';
  linked_to?: string[];
  inquiry_id?: string;
}

interface SignalsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  signals: Signal[];
  onSignalClick?: (signal: Signal) => void;
}

export function SignalsPanel({
  isOpen,
  onClose,
  signals,
  onSignalClick,
}: SignalsPanelProps) {
  // Transform signals to the format expected by SignalGraphView
  const formattedSignals = signals.map((s) => ({
    id: s.id,
    type: mapSignalType(s.type),
    text: s.text,
    strength: s.strength,
    validation_status: s.validation_status,
    linked_to: s.linked_to,
    inquiry_id: s.inquiry_id,
  }));

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
          fixed top-0 left-0 h-full w-full max-w-lg
          bg-white shadow-2xl z-50
          transform transition-transform duration-300 ease-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-neutral-200 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">Signals</h2>
            <p className="text-sm text-neutral-500">
              {signals.length} signals extracted from this case
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
        <div className="overflow-y-auto h-[calc(100%-80px)] p-6">
          {signals.length > 0 ? (
            <SignalGraphView
              signals={formattedSignals}
              onSignalClick={onSignalClick}
              compact={false}
            />
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-16 h-16 bg-neutral-100 rounded-full flex items-center justify-center mb-4">
                <svg
                  className="w-8 h-8 text-neutral-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-neutral-900 mb-2">
                No Signals Yet
              </h3>
              <p className="text-sm text-neutral-500 max-w-xs">
                Signals are extracted from your conversations and documents.
                Continue working on your case to generate signals.
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// Map API signal types to the types expected by SignalGraphView
function mapSignalType(
  type: string
): 'claim' | 'assumption' | 'evidence' | 'question' | 'constraint' | 'goal' {
  const typeMap: Record<string, 'claim' | 'assumption' | 'evidence' | 'question' | 'constraint' | 'goal'> = {
    claim: 'claim',
    assumption: 'assumption',
    evidence: 'evidence',
    evidence_mention: 'evidence',
    question: 'question',
    constraint: 'constraint',
    goal: 'goal',
    decision_intent: 'goal',
  };
  return typeMap[type.toLowerCase()] || 'claim';
}
