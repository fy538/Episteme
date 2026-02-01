/**
 * Diff viewer - shows changes with accept/reject/edit actions
 */

'use client';

import { useState } from 'react';
import { diffLines, Change } from 'diff';
import { Button } from './button';

interface DiffViewerProps {
  original: string;
  proposed: string;
  title?: string;
  onAccept: (content: string) => void;
  onReject: () => void;
  onClose: () => void;
}

export function DiffViewer({
  original,
  proposed,
  title = 'Suggested Changes',
  onAccept,
  onReject,
  onClose,
}: DiffViewerProps) {
  const [editedContent, setEditedContent] = useState(proposed);
  const [isEditing, setIsEditing] = useState(false);

  const diff = diffLines(original, proposed);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isEditing ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Edit the proposed changes:
              </label>
              <textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                className="w-full min-h-[400px] px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              />
            </div>
          ) : (
            <div className="space-y-1 font-mono text-sm">
              {diff.map((part: Change, idx: number) => {
                const bgColor = part.added
                  ? 'bg-green-100'
                  : part.removed
                  ? 'bg-red-100'
                  : 'bg-transparent';
                
                const textColor = part.added
                  ? 'text-green-900'
                  : part.removed
                  ? 'text-red-900'
                  : 'text-gray-700';

                const prefix = part.added ? '+ ' : part.removed ? '- ' : '  ';

                return (
                  <div
                    key={idx}
                    className={`${bgColor} ${textColor} px-3 py-1 whitespace-pre-wrap`}
                  >
                    {part.value.split('\n').map((line, lineIdx) => (
                      <div key={lineIdx}>
                        {prefix}
                        {line}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}

          {/* Summary */}
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">Change Summary</h4>
            <div className="text-sm text-blue-800 space-y-1">
              <p>
                <span className="font-medium text-green-700">
                  +{diff.filter((p) => p.added).reduce((sum, p) => sum + p.value.split('\n').length, 0)} lines added
                </span>
              </p>
              <p>
                <span className="font-medium text-red-700">
                  -{diff.filter((p) => p.removed).reduce((sum, p) => sum + p.value.split('\n').length, 0)} lines removed
                </span>
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
          <div className="flex gap-2">
            <Button
              onClick={() => setIsEditing(!isEditing)}
              variant="outline"
              size="sm"
            >
              {isEditing ? 'View Diff' : 'Edit'}
            </Button>
          </div>
          
          <div className="flex gap-3">
            <Button onClick={onReject} variant="outline">
              Reject
            </Button>
            <Button onClick={() => onAccept(editedContent)}>
              Accept Changes
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
