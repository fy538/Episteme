/**
 * Investigation Setup Modal - preview and configure inquiry before creating
 * Reduces time-to-research from 5 minutes to 15 seconds
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface InvestigationSetupModalProps {
  isOpen: boolean;
  context: {
    type: 'text_selection' | 'manual' | 'signal' | 'assumption';
    selectedText?: string;
    suggestedTitle?: string;
    caseId: string;
    briefId?: string;
    signalId?: string;
  };
  onConfirm: (config: {
    title: string;
    generatePlan: boolean;
    extractEvidence: boolean;
    aiFirstMessage: boolean;
  }) => void;
  onCancel: () => void;
  isCreating?: boolean;
}

export function InvestigationSetupModal({
  isOpen,
  context,
  onConfirm,
  onCancel,
  isCreating = false,
}: InvestigationSetupModalProps) {
  const [title, setTitle] = useState(context.suggestedTitle || context.selectedText || '');
  const [generatePlan, setGeneratePlan] = useState(true);
  const [extractEvidence, setExtractEvidence] = useState(true);
  const [aiFirstMessage, setAiFirstMessage] = useState(true);

  if (!isOpen) return null;

  const contextLabels = {
    text_selection: 'From your brief',
    manual: 'New investigation',
    signal: 'From conversation',
    assumption: 'From detected assumption',
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-neutral-200">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-2xl font-bold text-neutral-900">Start Investigation</h2>
            <Button onClick={onCancel} variant="ghost" size="icon">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </Button>
          </div>
          <p className="text-neutral-600">{contextLabels[context.type]}</p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 p-6">
          {/* Left: Configuration */}
          <div className="space-y-6">
            {/* Context Display */}
            {context.selectedText && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs font-medium text-blue-900 mb-1">Selected from brief:</p>
                <p className="text-sm text-neutral-800 italic">"{context.selectedText}"</p>
              </div>
            )}

            {/* Title */}
            <div>
              <label htmlFor="investigation-title" className="block text-sm font-medium text-neutral-700 mb-2">
                Investigation Question
              </label>
              <Input
                id="investigation-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="What question are you investigating?"
                className="text-lg border-2 border-purple-300 focus:ring-purple-500"
              />
            </div>

            {/* Setup Options */}
            <div>
              <h3 className="text-sm font-medium text-neutral-700 mb-3">AI Setup Options</h3>
              <div className="space-y-3">
                <label className="flex items-start gap-3 p-3 border-2 border-neutral-200 rounded-lg cursor-pointer hover:border-purple-300 transition-colors">
                  <input
                    type="checkbox"
                    checked={generatePlan}
                    onChange={(e) => setGeneratePlan(e.target.checked)}
                    className="mt-1"
                  />
                  <div>
                    <div className="font-medium text-neutral-900">Generate Investigation Plan</div>
                    <div className="text-xs text-neutral-600">
                      AI creates hypothesis, research approaches, and success criteria
                    </div>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 border-2 border-neutral-200 rounded-lg cursor-pointer hover:border-purple-300 transition-colors">
                  <input
                    type="checkbox"
                    checked={extractEvidence}
                    onChange={(e) => setExtractEvidence(e.target.checked)}
                    className="mt-1"
                  />
                  <div>
                    <div className="font-medium text-neutral-900">Extract Evidence from Documents</div>
                    <div className="text-xs text-neutral-600">
                      AI scans case documents for relevant facts and data
                    </div>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 border-2 border-neutral-200 rounded-lg cursor-pointer hover:border-purple-300 transition-colors">
                  <input
                    type="checkbox"
                    checked={aiFirstMessage}
                    onChange={(e) => setAiFirstMessage(e.target.checked)}
                    className="mt-1"
                  />
                  <div>
                    <div className="font-medium text-neutral-900">AI Research Assistant</div>
                    <div className="text-xs text-neutral-600">
                      AI suggests specific research actions to get started
                    </div>
                  </div>
                </label>
              </div>
            </div>
          </div>

          {/* Right: Preview */}
          <div className="bg-gradient-to-br from-purple-50 to-blue-50 border-2 border-purple-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-purple-900 mb-4">What You'll Get</h3>
            
            <div className="space-y-4">
              {generatePlan && (
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-purple-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <div className="font-medium text-neutral-900">Investigation Plan</div>
                    <div className="text-sm text-neutral-600">Hypothesis, research approaches, success criteria</div>
                  </div>
                </div>
              )}

              {extractEvidence && (
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-purple-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <div className="font-medium text-neutral-900">Evidence Suggestions</div>
                    <div className="text-sm text-neutral-600">AI-extracted facts from your documents</div>
                  </div>
                </div>
              )}

              {aiFirstMessage && (
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-purple-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <div className="font-medium text-neutral-900">AI Research Partner</div>
                    <div className="text-sm text-neutral-600">Proactive suggestions for next steps</div>
                  </div>
                </div>
              )}

              <div className="mt-6 pt-4 border-t border-purple-200">
                <div className="flex items-center gap-2 text-sm text-purple-900">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                  </svg>
                  <span>Setup time: ~15 seconds</span>
                </div>
                <p className="text-xs text-purple-700 mt-2">
                  Saves you 5-10 minutes of research setup
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-neutral-200 bg-neutral-50 flex items-center justify-between">
          <Button
            onClick={onCancel}
            disabled={isCreating}
            variant="ghost"
          >
            Cancel
          </Button>
          <div className="flex gap-3">
            <Button
              onClick={() => onConfirm({ title, generatePlan: false, extractEvidence: false, aiFirstMessage: false })}
              disabled={isCreating || !title.trim()}
              variant="outline"
            >
              Just Create Empty
            </Button>
            <Button
              onClick={() => onConfirm({ title, generatePlan, extractEvidence, aiFirstMessage })}
              disabled={isCreating || !title.trim()}
              className="bg-purple-600 hover:bg-purple-700"
            >
              {isCreating ? 'Setting up...' : '🔍 Start Investigating'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
