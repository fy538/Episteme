/**
 * AICopilotPanel - AI assistant panel for the decision canvas
 *
 * Features:
 * - "What am I missing?" gap analysis
 * - Inquiry suggestions with accept/dismiss
 * - Evidence source suggestions
 * - Quick actions for case improvement
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  SparklesIcon,
  XMarkIcon,
  LightBulbIcon,
  ExclamationTriangleIcon,
  CheckIcon,
  ChevronRightIcon,
  ArrowPathIcon,
  QuestionMarkCircleIcon,
  DocumentMagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { useAICopilot, getCopilotActionLabel } from '@/hooks/useAICopilot';

interface AICopilotPanelProps {
  caseId: string;
  isOpen: boolean;
  onClose: () => void;
  onInquiryCreated?: (inquiryId: string) => void;
  onInquiryClick?: (inquiryId: string) => void;
}

export function AICopilotPanel({
  caseId,
  isOpen,
  onClose,
  onInquiryCreated,
  onInquiryClick,
}: AICopilotPanelProps) {
  const [activeTab, setActiveTab] = useState<'gaps' | 'inquiries'>('gaps');

  const {
    isLoading,
    action,
    error,
    gapAnalysis,
    analyzeGaps,
    inquirySuggestions,
    suggestInquiries,
    acceptInquirySuggestion,
    dismissInquirySuggestion,
    clearAll,
  } = useAICopilot({ caseId, onInquiryCreated });

  if (!isOpen) return null;

  return (
    <div className="absolute top-4 right-4 w-96 bg-white rounded-xl shadow-2xl border border-neutral-200 overflow-hidden z-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-500 to-purple-600 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-white">
          <SparklesIcon className="w-5 h-5" />
          <span className="font-medium">AI Copilot</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-white/80 hover:text-white rounded"
        >
          <XMarkIcon className="w-5 h-5" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        <button
          onClick={() => setActiveTab('gaps')}
          className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'gaps'
              ? 'text-indigo-600 border-b-2 border-indigo-600'
              : 'text-neutral-500 hover:text-neutral-700'
          }`}
        >
          <QuestionMarkCircleIcon className="w-4 h-4 inline mr-1" />
          Gap Analysis
        </button>
        <button
          onClick={() => setActiveTab('inquiries')}
          className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'inquiries'
              ? 'text-indigo-600 border-b-2 border-indigo-600'
              : 'text-neutral-500 hover:text-neutral-700'
          }`}
        >
          <LightBulbIcon className="w-4 h-4 inline mr-1" />
          Suggestions
          {inquirySuggestions.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 bg-indigo-100 text-indigo-600 rounded-full text-xs">
              {inquirySuggestions.length}
            </span>
          )}
        </button>
      </div>

      {/* Content */}
      <div className="max-h-[60vh] overflow-y-auto">
        {/* Loading state */}
        {isLoading && (
          <div className="p-6 flex flex-col items-center justify-center">
            <ArrowPathIcon className="w-8 h-8 text-indigo-500 animate-spin mb-3" />
            <p className="text-sm text-neutral-600">{getCopilotActionLabel(action)}</p>
          </div>
        )}

        {/* Error state */}
        {error && !isLoading && (
          <div className="p-4 m-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Gap Analysis Tab */}
        {activeTab === 'gaps' && !isLoading && (
          <div className="p-4">
            {!gapAnalysis ? (
              <div className="text-center py-8">
                <QuestionMarkCircleIcon className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
                <h3 className="text-lg font-medium text-neutral-900 mb-2">
                  What am I missing?
                </h3>
                <p className="text-sm text-neutral-500 mb-4">
                  AI will analyze your case for blind spots, unvalidated assumptions,
                  and contradictions.
                </p>
                <Button onClick={analyzeGaps}>
                  <SparklesIcon className="w-4 h-4 mr-2" />
                  Analyze Gaps
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Missing perspectives */}
                {gapAnalysis.missing_perspectives.length > 0 && (
                  <GapSection
                    title="Missing Perspectives"
                    icon={<DocumentMagnifyingGlassIcon className="w-4 h-4" />}
                    items={gapAnalysis.missing_perspectives}
                    color="blue"
                  />
                )}

                {/* Unvalidated assumptions */}
                {gapAnalysis.unvalidated_assumptions.length > 0 && (
                  <GapSection
                    title="Unvalidated Assumptions"
                    icon={<ExclamationTriangleIcon className="w-4 h-4" />}
                    items={gapAnalysis.unvalidated_assumptions}
                    color="amber"
                  />
                )}

                {/* Contradictions */}
                {gapAnalysis.contradictions.length > 0 && (
                  <GapSection
                    title="Contradictions"
                    icon={<ExclamationTriangleIcon className="w-4 h-4" />}
                    items={gapAnalysis.contradictions}
                    color="red"
                  />
                )}

                {/* Evidence gaps */}
                {gapAnalysis.evidence_gaps?.length > 0 && (
                  <GapSection
                    title="Evidence Gaps"
                    icon={<DocumentMagnifyingGlassIcon className="w-4 h-4" />}
                    items={gapAnalysis.evidence_gaps}
                    color="purple"
                  />
                )}

                {/* Recommendations */}
                {gapAnalysis.recommendations?.length > 0 && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <h4 className="text-sm font-medium text-green-800 mb-2 flex items-center gap-2">
                      <LightBulbIcon className="w-4 h-4" />
                      Recommendations
                    </h4>
                    <ul className="space-y-1.5">
                      {gapAnalysis.recommendations.map((rec, i) => (
                        <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                          <ChevronRightIcon className="w-4 h-4 flex-shrink-0 mt-0.5" />
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Empty state */}
                {gapAnalysis.missing_perspectives.length === 0 &&
                  gapAnalysis.unvalidated_assumptions.length === 0 &&
                  gapAnalysis.contradictions.length === 0 && (
                    <div className="text-center py-6">
                      <CheckIcon className="w-12 h-12 text-green-500 mx-auto mb-2" />
                      <p className="text-sm text-neutral-600">
                        Looking good! No major gaps detected.
                      </p>
                    </div>
                  )}

                {/* Refresh button */}
                <div className="pt-2 border-t">
                  <Button variant="outline" size="sm" onClick={analyzeGaps} className="w-full">
                    <ArrowPathIcon className="w-4 h-4 mr-2" />
                    Refresh Analysis
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Inquiry Suggestions Tab */}
        {activeTab === 'inquiries' && !isLoading && (
          <div className="p-4">
            {inquirySuggestions.length === 0 ? (
              <div className="text-center py-8">
                <LightBulbIcon className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
                <h3 className="text-lg font-medium text-neutral-900 mb-2">
                  Get Inquiry Suggestions
                </h3>
                <p className="text-sm text-neutral-500 mb-4">
                  AI will suggest questions to investigate based on your case.
                </p>
                <Button onClick={suggestInquiries}>
                  <SparklesIcon className="w-4 h-4 mr-2" />
                  Suggest Inquiries
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {inquirySuggestions.map((suggestion, index) => (
                  <InquirySuggestionCard
                    key={index}
                    suggestion={suggestion}
                    onAccept={() => acceptInquirySuggestion(suggestion)}
                    onDismiss={() => dismissInquirySuggestion(index)}
                  />
                ))}

                {/* Get more button */}
                <div className="pt-2 border-t">
                  <Button variant="outline" size="sm" onClick={suggestInquiries} className="w-full">
                    <ArrowPathIcon className="w-4 h-4 mr-2" />
                    Get More Suggestions
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer with quick actions */}
      <div className="border-t bg-neutral-50 px-4 py-2">
        <p className="text-xs text-neutral-500 text-center">
          Press <kbd className="px-1 py-0.5 bg-neutral-200 rounded text-xs">?</kbd> for keyboard shortcuts
        </p>
      </div>
    </div>
  );
}

/**
 * Gap section component
 */
function GapSection({
  title,
  icon,
  items,
  color,
}: {
  title: string;
  icon: React.ReactNode;
  items: string[];
  color: 'blue' | 'amber' | 'red' | 'purple';
}) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-800',
    amber: 'bg-amber-50 border-amber-200 text-amber-800',
    red: 'bg-red-50 border-red-200 text-red-800',
    purple: 'bg-purple-50 border-purple-200 text-purple-800',
  };

  const textColor = {
    blue: 'text-blue-700',
    amber: 'text-amber-700',
    red: 'text-red-700',
    purple: 'text-purple-700',
  };

  return (
    <div className={`rounded-lg border p-3 ${colorClasses[color]}`}>
      <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
        {icon}
        {title}
        <span className="text-xs opacity-70">({items.length})</span>
      </h4>
      <ul className="space-y-1.5">
        {items.slice(0, 5).map((item, i) => (
          <li key={i} className={`text-sm ${textColor[color]}`}>
            • {item}
          </li>
        ))}
        {items.length > 5 && (
          <li className={`text-xs ${textColor[color]} opacity-70`}>
            +{items.length - 5} more...
          </li>
        )}
      </ul>
    </div>
  );
}

/**
 * Inquiry suggestion card
 */
function InquirySuggestionCard({
  suggestion,
  onAccept,
  onDismiss,
}: {
  suggestion: {
    title: string;
    description: string;
    reason: string;
    priority: number;
  };
  onAccept: () => void;
  onDismiss: () => void;
}) {
  const [accepting, setAccepting] = useState(false);

  const handleAccept = async () => {
    setAccepting(true);
    await onAccept();
    setAccepting(false);
  };

  return (
    <div className="border border-neutral-200 rounded-lg p-3 hover:border-indigo-300 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <h4 className="text-sm font-medium text-neutral-900 flex-1 pr-2">
          {suggestion.title}
        </h4>
        <span
          className={`text-xs px-1.5 py-0.5 rounded ${
            suggestion.priority >= 3
              ? 'bg-red-100 text-red-700'
              : suggestion.priority >= 2
              ? 'bg-amber-100 text-amber-700'
              : 'bg-neutral-100 text-neutral-600'
          }`}
        >
          P{suggestion.priority}
        </span>
      </div>

      {/* Description */}
      {suggestion.description && (
        <p className="text-xs text-neutral-600 mb-2 line-clamp-2">
          {suggestion.description}
        </p>
      )}

      {/* Reason */}
      <p className="text-xs text-indigo-600 mb-3">
        <SparklesIcon className="w-3 h-3 inline mr-1" />
        {suggestion.reason}
      </p>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          onClick={handleAccept}
          disabled={accepting}
          className="flex-1"
        >
          {accepting ? (
            <ArrowPathIcon className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <CheckIcon className="w-4 h-4 mr-1" />
              Create
            </>
          )}
        </Button>
        <Button size="sm" variant="outline" onClick={onDismiss}>
          <XMarkIcon className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}

/**
 * Floating trigger button for the copilot
 */
export function AICopilotTrigger({
  onClick,
  hasResults,
}: {
  onClick: () => void;
  hasResults?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        p-3 rounded-xl shadow-lg border transition-all hover:scale-105
        ${
          hasResults
            ? 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white border-transparent'
            : 'bg-white text-indigo-600 border-indigo-200 hover:border-indigo-400'
        }
      `}
      title="AI Copilot"
    >
      <SparklesIcon className="w-5 h-5" />
      {hasResults && (
        <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
      )}
    </button>
  );
}
