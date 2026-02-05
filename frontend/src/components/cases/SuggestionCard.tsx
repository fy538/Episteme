/**
 * SuggestionCard - AI suggestion with accept/reject/edit actions
 *
 * Used for displaying AI-generated suggestions that the user can
 * approve, reject, or modify before applying.
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
  ChevronDownIcon,
  ChevronUpIcon,
  LightBulbIcon,
  QuestionMarkCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

export type SuggestionType =
  | 'inquiry'
  | 'constraint'
  | 'criterion'
  | 'assumption'
  | 'evidence_source'
  | 'brief_edit'
  | 'gap';

interface BaseSuggestion {
  type: SuggestionType;
  reason: string;
  priority?: 'low' | 'medium' | 'high';
}

interface InquirySuggestion extends BaseSuggestion {
  type: 'inquiry';
  title: string;
  description: string;
}

interface ConstraintSuggestion extends BaseSuggestion {
  type: 'constraint';
  constraint_type: string;
  description: string;
}

interface CriterionSuggestion extends BaseSuggestion {
  type: 'criterion';
  criterion: string;
  measurable?: string;
}

interface AssumptionSuggestion extends BaseSuggestion {
  type: 'assumption';
  text: string;
  validation_approach?: string;
}

interface EvidenceSourceSuggestion extends BaseSuggestion {
  type: 'evidence_source';
  inquiry_id: string;
  suggestion: string;
  source_type: string;
}

interface BriefEditSuggestion extends BaseSuggestion {
  type: 'brief_edit';
  section_id: string;
  current_content?: string;
  suggested_content: string;
  edit_type: 'add' | 'replace' | 'delete';
}

interface GapSuggestion extends BaseSuggestion {
  type: 'gap';
  gap_type: 'missing_perspective' | 'unvalidated_assumption' | 'contradiction';
  text: string;
}

export type Suggestion =
  | InquirySuggestion
  | ConstraintSuggestion
  | CriterionSuggestion
  | AssumptionSuggestion
  | EvidenceSourceSuggestion
  | BriefEditSuggestion
  | GapSuggestion;

interface SuggestionCardProps {
  suggestion: Suggestion;
  onAccept: (suggestion: Suggestion, edited?: string | Record<string, unknown>) => Promise<void>;
  onReject: (suggestion: Suggestion) => void;
  isLoading?: boolean;
}

export function SuggestionCard({
  suggestion,
  onAccept,
  onReject,
  isLoading = false,
}: SuggestionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editedContent, setEditedContent] = useState<string>('');
  const [accepting, setAccepting] = useState(false);

  const Icon = getSuggestionIcon(suggestion.type);
  const title = getSuggestionTitle(suggestion);
  const priorityColor = getPriorityColor(suggestion.priority);

  const handleAccept = async () => {
    setAccepting(true);
    try {
      if (editing && editedContent) {
        await onAccept(suggestion, editedContent);
      } else {
        await onAccept(suggestion);
      }
    } finally {
      setAccepting(false);
    }
  };

  const handleEdit = () => {
    setEditing(true);
    setEditedContent(getEditableContent(suggestion));
    setExpanded(true);
  };

  return (
    <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start gap-3 p-3">
        <div className="flex-shrink-0 p-2 bg-accent-50 rounded-lg">
          <Icon className="w-4 h-4 text-accent-600" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="neutral" className="text-xs">
              {formatSuggestionType(suggestion.type)}
            </Badge>
            {suggestion.priority && (
              <span
                className="text-xs px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: priorityColor + '20',
                  color: priorityColor,
                }}
              >
                {suggestion.priority}
              </span>
            )}
          </div>
          <p className="text-sm font-medium text-neutral-900 line-clamp-2">
            {title}
          </p>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="flex-shrink-0 p-1 text-neutral-400 hover:text-neutral-600"
        >
          {expanded ? (
            <ChevronUpIcon className="w-4 h-4" />
          ) : (
            <ChevronDownIcon className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-3 pb-3 space-y-3">
          {/* Reason */}
          <div className="flex items-start gap-2 text-sm text-neutral-600 bg-neutral-50 rounded p-2">
            <SparklesIcon className="w-4 h-4 text-accent-500 flex-shrink-0 mt-0.5" />
            <p>{suggestion.reason}</p>
          </div>

          {/* Type-specific content */}
          {renderSuggestionDetails(suggestion)}

          {/* Edit mode */}
          {editing && (
            <div className="space-y-2">
              <Textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                className="text-sm"
                rows={3}
                placeholder="Edit the suggestion..."
              />
            </div>
          )}
        </div>
      )}

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
          Dismiss
        </Button>
        {!editing && (
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
        <Button
          size="sm"
          onClick={handleAccept}
          disabled={isLoading || accepting}
        >
          <CheckIcon className="w-4 h-4 mr-1" />
          {accepting ? 'Applying...' : 'Accept'}
        </Button>
      </div>
    </div>
  );
}

/**
 * List of suggestion cards with batch actions
 */
export function SuggestionList({
  suggestions,
  onAccept,
  onReject,
  onAcceptAll,
  onDismissAll,
  title = 'AI Suggestions',
  isLoading = false,
}: {
  suggestions: Suggestion[];
  onAccept: (suggestion: Suggestion, edited?: string | Record<string, unknown>) => Promise<void>;
  onReject: (suggestion: Suggestion) => void;
  onAcceptAll?: () => Promise<void>;
  onDismissAll?: () => void;
  title?: string;
  isLoading?: boolean;
}) {
  if (suggestions.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SparklesIcon className="w-5 h-5 text-accent-500" />
          <h3 className="font-medium text-neutral-900">{title}</h3>
          <Badge variant="neutral">{suggestions.length}</Badge>
        </div>
        {(onAcceptAll || onDismissAll) && (
          <div className="flex gap-2">
            {onDismissAll && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onDismissAll}
                disabled={isLoading}
              >
                Dismiss All
              </Button>
            )}
            {onAcceptAll && (
              <Button
                variant="outline"
                size="sm"
                onClick={onAcceptAll}
                disabled={isLoading}
              >
                Accept All
              </Button>
            )}
          </div>
        )}
      </div>

      <div className="space-y-2">
        {suggestions.map((suggestion, index) => (
          <SuggestionCard
            key={index}
            suggestion={suggestion}
            onAccept={onAccept}
            onReject={onReject}
            isLoading={isLoading}
          />
        ))}
      </div>
    </div>
  );
}

// Helper functions

function getSuggestionIcon(type: SuggestionType) {
  switch (type) {
    case 'inquiry':
      return QuestionMarkCircleIcon;
    case 'gap':
      return ExclamationTriangleIcon;
    case 'assumption':
      return ExclamationTriangleIcon;
    default:
      return LightBulbIcon;
  }
}

function getSuggestionTitle(suggestion: Suggestion): string {
  switch (suggestion.type) {
    case 'inquiry':
      return suggestion.title;
    case 'constraint':
      return `${suggestion.constraint_type}: ${suggestion.description}`;
    case 'criterion':
      return suggestion.criterion;
    case 'assumption':
      return suggestion.text;
    case 'evidence_source':
      return suggestion.suggestion;
    case 'brief_edit':
      return `${suggestion.edit_type} in section`;
    case 'gap':
      return suggestion.text;
  }
}

function formatSuggestionType(type: SuggestionType): string {
  return type
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function getPriorityColor(priority?: 'low' | 'medium' | 'high'): string {
  switch (priority) {
    case 'high':
      return '#ef4444';
    case 'medium':
      return '#f97316';
    case 'low':
      return '#22c55e';
    default:
      return '#6b7280';
  }
}

function getEditableContent(suggestion: Suggestion): string {
  switch (suggestion.type) {
    case 'inquiry':
      return suggestion.title;
    case 'constraint':
      return suggestion.description;
    case 'criterion':
      return suggestion.criterion;
    case 'assumption':
      return suggestion.text;
    case 'evidence_source':
      return suggestion.suggestion;
    case 'brief_edit':
      return suggestion.suggested_content;
    case 'gap':
      return suggestion.text;
  }
}

function renderSuggestionDetails(suggestion: Suggestion) {
  switch (suggestion.type) {
    case 'inquiry':
      return suggestion.description ? (
        <p className="text-sm text-neutral-600">{suggestion.description}</p>
      ) : null;

    case 'assumption':
      return suggestion.validation_approach ? (
        <div className="text-sm text-neutral-600">
          <span className="font-medium">How to validate: </span>
          {suggestion.validation_approach}
        </div>
      ) : null;

    case 'evidence_source':
      return (
        <div className="text-sm text-neutral-600">
          <span className="font-medium">Source type: </span>
          {suggestion.source_type}
        </div>
      );

    case 'brief_edit':
      return suggestion.current_content ? (
        <div className="space-y-2 text-sm">
          <div className="bg-error-50 p-2 rounded text-error-700 line-through">
            {suggestion.current_content}
          </div>
          <div className="bg-success-50 p-2 rounded text-success-700">
            {suggestion.suggested_content}
          </div>
        </div>
      ) : (
        <div className="bg-success-50 p-2 rounded text-sm text-success-700">
          {suggestion.suggested_content}
        </div>
      );

    default:
      return null;
  }
}
