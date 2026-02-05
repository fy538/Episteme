/**
 * Case creation preview - shows AI analysis before creating case
 * Reduces time-to-aha by pre-filling content
 */

'use client';

import { useState } from 'react';
import { Streamdown } from 'streamdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface CaseCreationPreviewProps {
  analysis: {
    suggested_title: string;
    position_draft: string;
    key_questions: string[];
    assumptions: string[];
    background_summary: string;
    confidence: number;
  };
  onConfirm: (edits?: { title?: string; position?: string }) => void;
  onDismiss: () => void;
  isCreating?: boolean;
}

export function CaseCreationPreview({
  analysis,
  onConfirm,
  onDismiss,
  isCreating = false,
}: CaseCreationPreviewProps) {
  const [title, setTitle] = useState(analysis.suggested_title);

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onDismiss}>
      <div
        className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-neutral-200">
          <h2 className="text-2xl tracking-tight font-bold text-neutral-900 mb-2">Create Decision Case</h2>
          <p className="text-neutral-600">
            I analyzed your conversation and drafted this case structure
          </p>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Title - Editable */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Case Title
            </label>
            <Input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-4 py-3 text-lg border-2 border-primary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-accent-500 outline-none"
              placeholder="What are you deciding?"
            />
          </div>

          {/* Position Draft */}
          <div>
            <h3 className="text-sm font-medium text-neutral-700 mb-2">
              Your Position (draft)
            </h3>
            <div className="p-4 bg-accent-50 border border-accent-200 rounded-lg">
              <p className="text-neutral-800 leading-relaxed">{analysis.position_draft}</p>
            </div>
          </div>

          {/* Key Questions */}
          <div>
            <h3 className="text-sm font-medium text-neutral-700 mb-2 flex items-center gap-2">
              Questions to Investigate
              <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-medium rounded-full">
                {analysis.key_questions.length}
              </span>
            </h3>
            <div className="space-y-2">
              {analysis.key_questions.map((q, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 bg-purple-50 border border-purple-200 rounded-lg"
                >
                  <svg
                    className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span className="text-neutral-800 flex-1">{q}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-neutral-500 mt-2">
              These will become inquiries you can investigate
            </p>
          </div>

          {/* Assumptions */}
          {analysis.assumptions.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-neutral-700 mb-2 flex items-center gap-2">
                Assumptions to Validate
                <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">
                  {analysis.assumptions.length}
                </span>
              </h3>
              <div className="space-y-2">
                {analysis.assumptions.map((a, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg"
                  >
                    <svg
                      className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span className="text-neutral-800 flex-1">{a}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-neutral-500 mt-2">
                These will be highlighted in your brief for easy validation
              </p>
            </div>
          )}

          {/* Value Proposition */}
          <div className="p-4 bg-gradient-to-r from-accent-50 to-purple-50 dark:from-accent-900/20 dark:to-purple-900/20 border border-accent-200 dark:border-accent-800 rounded-lg">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-accent-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                  clipRule="evenodd"
                />
              </svg>
              <p className="text-sm text-neutral-800">
                This will save you <span className="font-semibold">~10 minutes</span> of organizing
                your thoughts. Everything is editable once created.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-neutral-200 bg-neutral-50 flex items-center justify-between">
          <button
            onClick={onDismiss}
            disabled={isCreating}
            className="text-neutral-600 hover:text-neutral-900 font-medium transition-colors disabled:opacity-50"
          >
            Keep Chatting
          </button>
          <button
            onClick={() => onConfirm({ title })}
            disabled={isCreating || !title.trim()}
            className="px-6 py-3 bg-accent-600 text-white rounded-lg hover:bg-accent-700 font-medium disabled:opacity-50 transition-colors"
          >
            {isCreating ? 'Creating...' : '✨ Create This Case'}
          </button>
        </div>
      </div>
    </div>
  );
}
