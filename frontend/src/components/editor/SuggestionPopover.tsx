/**
 * SuggestionPopover - Floating popover for inline suggestion accept/reject.
 *
 * Shown when user clicks a suggestion mark in the editor.
 * Supports:
 * - Accept (applies suggested change)
 * - Reject (removes mark, keeps original)
 * - Edit before accepting (editable textarea)
 * - Shows reason and confidence
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import type { BriefSectionSuggestion } from '@/components/cases/BriefSuggestion';

interface SuggestionPopoverProps {
  suggestion: BriefSectionSuggestion;
  position: { x: number; y: number };
  onAccept: (suggestion: BriefSectionSuggestion, editedContent?: string) => void;
  onReject: (suggestion: BriefSectionSuggestion) => void;
  onClose: () => void;
}

const TYPE_LABELS: Record<string, string> = {
  add: 'Add content',
  replace: 'Replace text',
  delete: 'Remove text',
  cite: 'Add citation',
  clarify: 'Clarify text',
};

export function SuggestionPopover({
  suggestion,
  position,
  onAccept,
  onReject,
  onClose,
}: SuggestionPopoverProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(suggestion.suggested_content);

  const confidencePercent = Math.round((suggestion.confidence ?? 0) * 100);

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40" onClick={onClose} />

      {/* Popover */}
      <div
        className="fixed z-50 bg-white border border-neutral-200 rounded-xl shadow-xl w-80"
        style={{
          left: `${Math.min(position.x, window.innerWidth - 340)}px`,
          top: `${position.y + 12}px`,
        }}
      >
        {/* Header */}
        <div className="px-4 py-2.5 border-b border-neutral-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-neutral-500">
              {TYPE_LABELS[suggestion.suggestion_type] || suggestion.suggestion_type}
            </span>
            <span
              className={`text-xs px-1.5 py-0.5 rounded-full ${
                confidencePercent >= 80
                  ? 'bg-green-100 text-green-700'
                  : confidencePercent >= 50
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-neutral-100 text-neutral-600'
              }`}
            >
              {confidencePercent}%
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 text-sm"
          >
            &times;
          </button>
        </div>

        {/* Body */}
        <div className="px-4 py-3 space-y-3">
          {/* Reason */}
          <p className="text-sm text-neutral-700 leading-relaxed">{suggestion.reason}</p>

          {/* Current → Suggested diff */}
          {suggestion.current_content && suggestion.suggestion_type === 'replace' && (
            <div className="space-y-1.5">
              <div className="bg-red-50 rounded px-2.5 py-1.5 text-sm">
                <span className="text-xs font-medium text-red-500 block mb-0.5">Remove</span>
                <span className="text-red-700 line-through">{suggestion.current_content}</span>
              </div>
              {!isEditing ? (
                <div className="bg-green-50 rounded px-2.5 py-1.5 text-sm">
                  <span className="text-xs font-medium text-green-500 block mb-0.5">Add</span>
                  <span className="text-green-800">{suggestion.suggested_content}</span>
                </div>
              ) : (
                <textarea
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  className="w-full border border-green-300 rounded px-2.5 py-1.5 text-sm text-green-800 bg-green-50 focus:outline-none focus:ring-1 focus:ring-green-400"
                  rows={3}
                />
              )}
            </div>
          )}

          {/* Add-only suggestion */}
          {suggestion.suggestion_type === 'add' && (
            <div className="bg-green-50 rounded px-2.5 py-1.5 text-sm">
              <span className="text-xs font-medium text-green-500 block mb-0.5">Insert</span>
              {!isEditing ? (
                <span className="text-green-800">{suggestion.suggested_content}</span>
              ) : (
                <textarea
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  className="w-full border border-green-300 rounded px-2.5 py-1.5 text-sm text-green-800 bg-green-50 focus:outline-none focus:ring-1 focus:ring-green-400 mt-1"
                  rows={3}
                />
              )}
            </div>
          )}

          {/* Delete suggestion */}
          {suggestion.suggestion_type === 'delete' && suggestion.current_content && (
            <div className="bg-red-50 rounded px-2.5 py-1.5 text-sm">
              <span className="text-xs font-medium text-red-500 block mb-0.5">Delete</span>
              <span className="text-red-700 line-through">{suggestion.current_content}</span>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="px-4 py-2.5 border-t border-neutral-100 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            {!isEditing && (
              <button
                onClick={() => setIsEditing(true)}
                className="text-xs text-neutral-500 hover:text-neutral-700 underline"
              >
                Edit first
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                onReject(suggestion);
                onClose();
              }}
              className="text-xs h-7"
            >
              Reject
            </Button>
            <Button
              size="sm"
              onClick={() => {
                onAccept(
                  suggestion,
                  isEditing ? editedContent : undefined
                );
                onClose();
              }}
              className="text-xs h-7"
            >
              {isEditing ? 'Accept Edited' : 'Accept'}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
