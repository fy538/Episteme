/**
 * BriefSuggestion - Inline suggestion component for brief editing
 *
 * Shows AI suggestions as inline annotations that can be accepted,
 * rejected, or edited before applying to the brief.
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  SparklesIcon,
  CheckIcon,
  XMarkIcon,
  PencilIcon,
  LinkIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

export interface BriefSectionSuggestion {
  id: string;
  section_id: string;
  suggestion_type: 'add' | 'replace' | 'delete' | 'cite' | 'clarify';
  current_content?: string;
  suggested_content: string;
  reason: string;
  confidence?: number;
  status: 'pending' | 'accepted' | 'rejected';
}

interface BriefSuggestionProps {
  suggestion: BriefSectionSuggestion;
  onAccept: (suggestion: BriefSectionSuggestion, editedContent?: string) => Promise<void>;
  onReject: (suggestion: BriefSectionSuggestion) => void;
  isInline?: boolean;
  isLoading?: boolean;
}

export function BriefSuggestion({
  suggestion,
  onAccept,
  onReject,
  isInline = false,
  isLoading = false,
}: BriefSuggestionProps) {
  const [editing, setEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(suggestion.suggested_content);
  const [accepting, setAccepting] = useState(false);

  const handleAccept = async () => {
    setAccepting(true);
    try {
      await onAccept(suggestion, editing ? editedContent : undefined);
    } finally {
      setAccepting(false);
    }
  };

  const handleEdit = () => {
    setEditing(true);
    setEditedContent(suggestion.suggested_content);
  };

  const typeLabel = getSuggestionTypeLabel(suggestion.suggestion_type);
  const typeColor = getSuggestionTypeColor(suggestion.suggestion_type);

  // Inline compact version for margin annotations
  if (isInline) {
    return (
      <div
        className={`relative ml-2 p-2 border-l-2 ${typeColor} bg-white rounded-r shadow-sm max-w-xs`}
      >
        <div className="flex items-start gap-2">
          <SparklesIcon className="w-4 h-4 text-accent-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-neutral-600 line-clamp-2">{suggestion.reason}</p>
            <div className="flex gap-1 mt-1">
              <button
                onClick={handleAccept}
                disabled={isLoading || accepting}
                className="p-1 text-success-600 hover:bg-success-50 rounded"
                title="Accept"
              >
                <CheckIcon className="w-3 h-3" />
              </button>
              <button
                onClick={() => onReject(suggestion)}
                disabled={isLoading}
                className="p-1 text-error-600 hover:bg-error-50 rounded"
                title="Reject"
              >
                <XMarkIcon className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Full suggestion card
  return (
    <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
      {/* Header */}
      <div className={`px-3 py-2 border-b ${typeColor.replace('border-l-', 'bg-').replace('-500', '-50')}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SparklesIcon className="w-4 h-4 text-accent-500" />
            <Badge variant="neutral" className="text-xs">
              {typeLabel}
            </Badge>
            {suggestion.confidence !== undefined && (
              <span className="text-xs text-neutral-500">
                {Math.round(suggestion.confidence * 100)}% confident
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-3 space-y-3">
        {/* Reason */}
        <p className="text-sm text-neutral-600">{suggestion.reason}</p>

        {/* Diff view for replacements */}
        {suggestion.suggestion_type === 'replace' && suggestion.current_content && (
          <div className="space-y-2 text-sm">
            <div className="bg-error-50 p-2 rounded border border-error-200">
              <div className="text-xs text-error-600 font-medium mb-1">Remove:</div>
              <p className="text-error-800 line-through">{suggestion.current_content}</p>
            </div>
            <div className="bg-success-50 p-2 rounded border border-success-200">
              <div className="text-xs text-success-600 font-medium mb-1">Add:</div>
              <p className="text-success-800">{suggestion.suggested_content}</p>
            </div>
          </div>
        )}

        {/* Add view */}
        {suggestion.suggestion_type === 'add' && !editing && (
          <div className="bg-success-50 p-2 rounded border border-success-200 text-sm">
            <div className="text-xs text-success-600 font-medium mb-1">Add:</div>
            <p className="text-success-800">{suggestion.suggested_content}</p>
          </div>
        )}

        {/* Delete view */}
        {suggestion.suggestion_type === 'delete' && (
          <div className="bg-error-50 p-2 rounded border border-error-200 text-sm">
            <div className="text-xs text-error-600 font-medium mb-1">Remove:</div>
            <p className="text-error-800 line-through">
              {suggestion.current_content || suggestion.suggested_content}
            </p>
          </div>
        )}

        {/* Clarify view */}
        {suggestion.suggestion_type === 'clarify' && (
          <div className="bg-warning-50 p-2 rounded border border-warning-200 text-sm">
            <div className="flex items-center gap-1 text-xs text-warning-600 font-medium mb-1">
              <ExclamationTriangleIcon className="w-3 h-3" />
              Clarification needed:
            </div>
            <p className="text-warning-800">{suggestion.suggested_content}</p>
          </div>
        )}

        {/* Cite view */}
        {suggestion.suggestion_type === 'cite' && (
          <div className="bg-accent-50 p-2 rounded border border-accent-200 text-sm">
            <div className="flex items-center gap-1 text-xs text-accent-600 font-medium mb-1">
              <LinkIcon className="w-3 h-3" />
              Add citation:
            </div>
            <p className="text-accent-800">{suggestion.suggested_content}</p>
          </div>
        )}

        {/* Edit mode */}
        {editing && (
          <div className="space-y-2">
            <Textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              className="text-sm"
              rows={3}
            />
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setEditing(false);
                  setEditedContent(suggestion.suggested_content);
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 px-3 py-2 bg-neutral-50 border-t">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onReject(suggestion)}
          disabled={isLoading || accepting}
          className="text-neutral-600"
        >
          <XMarkIcon className="w-4 h-4 mr-1" />
          Reject
        </Button>
        {!editing && suggestion.suggestion_type !== 'delete' && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleEdit}
            disabled={isLoading || accepting}
            className="text-neutral-600"
          >
            <PencilIcon className="w-4 h-4 mr-1" />
            Edit
          </Button>
        )}
        <Button size="sm" onClick={handleAccept} disabled={isLoading || accepting}>
          <CheckIcon className="w-4 h-4 mr-1" />
          {accepting ? 'Applying...' : 'Accept'}
        </Button>
      </div>
    </div>
  );
}

/**
 * List of brief suggestions grouped by section
 */
export function BriefSuggestionList({
  suggestions,
  onAccept,
  onReject,
  isLoading = false,
}: {
  suggestions: BriefSectionSuggestion[];
  onAccept: (suggestion: BriefSectionSuggestion, editedContent?: string) => Promise<void>;
  onReject: (suggestion: BriefSectionSuggestion) => void;
  isLoading?: boolean;
}) {
  const pendingSuggestions = suggestions.filter((s) => s.status === 'pending');

  if (pendingSuggestions.length === 0) {
    return null;
  }

  // Group by section
  const bySection = pendingSuggestions.reduce((acc, s) => {
    const section = s.section_id || 'general';
    if (!acc[section]) acc[section] = [];
    acc[section].push(s);
    return acc;
  }, {} as Record<string, BriefSectionSuggestion[]>);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <SparklesIcon className="w-5 h-5 text-accent-500" />
        <h3 className="font-medium text-neutral-900">AI Suggestions</h3>
        <Badge variant="neutral">{pendingSuggestions.length}</Badge>
      </div>

      {Object.entries(bySection).map(([section, sectionSuggestions]) => (
        <div key={section} className="space-y-2">
          <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
            {formatSectionName(section)}
          </p>
          {sectionSuggestions.map((suggestion) => (
            <BriefSuggestion
              key={suggestion.id}
              suggestion={suggestion}
              onAccept={onAccept}
              onReject={onReject}
              isLoading={isLoading}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// Helper functions

function getSuggestionTypeLabel(type: BriefSectionSuggestion['suggestion_type']): string {
  switch (type) {
    case 'add':
      return 'Add Content';
    case 'replace':
      return 'Replace';
    case 'delete':
      return 'Remove';
    case 'cite':
      return 'Add Citation';
    case 'clarify':
      return 'Needs Clarification';
    default:
      return 'Suggestion';
  }
}

function getSuggestionTypeColor(type: BriefSectionSuggestion['suggestion_type']): string {
  switch (type) {
    case 'add':
      return 'border-l-success-500';
    case 'replace':
      return 'border-l-warning-500';
    case 'delete':
      return 'border-l-error-500';
    case 'cite':
      return 'border-l-accent-500';
    case 'clarify':
      return 'border-l-warning-500';
    default:
      return 'border-l-neutral-300';
  }
}

function formatSectionName(section: string): string {
  return section
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
