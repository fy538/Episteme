/**
 * SuggestionReviewPanel - Cursor-like panel for reviewing AI suggestions
 *
 * Provides a focused view for accepting/rejecting multiple suggestions
 * with keyboard navigation and batch operations.
 */

'use client';

import { useState, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  SparklesIcon,
  CheckIcon,
  XMarkIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import type { BriefSectionSuggestion } from './BriefSuggestion';

interface SuggestionReviewPanelProps {
  suggestions: BriefSectionSuggestion[];
  onAccept: (suggestion: BriefSectionSuggestion, editedContent?: string) => Promise<void>;
  onReject: (suggestion: BriefSectionSuggestion) => void;
  onAcceptAll: () => Promise<void>;
  onRejectAll: () => void;
  onRefresh: () => void;
  isLoading?: boolean;
  isRefreshing?: boolean;
  onClose?: () => void;
}

export function SuggestionReviewPanel({
  suggestions,
  onAccept,
  onReject,
  onAcceptAll,
  onRejectAll,
  onRefresh,
  isLoading = false,
  isRefreshing = false,
  onClose,
}: SuggestionReviewPanelProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [accepting, setAccepting] = useState(false);

  const pendingSuggestions = suggestions.filter((s) => s.status === 'pending');
  const currentSuggestion = pendingSuggestions[currentIndex];

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLTextAreaElement) return;

      switch (e.key) {
        case 'j':
        case 'ArrowDown':
          e.preventDefault();
          setCurrentIndex((i) => Math.min(i + 1, pendingSuggestions.length - 1));
          break;
        case 'k':
        case 'ArrowUp':
          e.preventDefault();
          setCurrentIndex((i) => Math.max(i - 1, 0));
          break;
        case 'Enter':
        case 'y':
          if (currentSuggestion && !accepting) {
            e.preventDefault();
            handleAccept();
          }
          break;
        case 'n':
        case 'Escape':
          if (currentSuggestion) {
            e.preventDefault();
            handleReject();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentIndex, pendingSuggestions.length, currentSuggestion, accepting]);

  const handleAccept = async () => {
    if (!currentSuggestion || accepting) return;
    setAccepting(true);
    try {
      await onAccept(currentSuggestion);
      // Move to next suggestion after accepting
      if (currentIndex >= pendingSuggestions.length - 1) {
        setCurrentIndex(Math.max(0, currentIndex - 1));
      }
    } finally {
      setAccepting(false);
    }
  };

  const handleReject = () => {
    if (!currentSuggestion) return;
    onReject(currentSuggestion);
    // Move to next suggestion after rejecting
    if (currentIndex >= pendingSuggestions.length - 1) {
      setCurrentIndex(Math.max(0, currentIndex - 1));
    }
  };

  if (pendingSuggestions.length === 0) {
    return (
      <div className="bg-white border border-neutral-200 rounded-lg p-6 text-center">
        <SparklesIcon className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-neutral-900 mb-2">
          No Suggestions to Review
        </h3>
        <p className="text-neutral-500 mb-4">
          {suggestions.length === 0
            ? 'Generate suggestions to get AI-powered improvements for your brief.'
            : 'All suggestions have been reviewed.'}
        </p>
        <div className="flex justify-center gap-3">
          <Button onClick={onRefresh} disabled={isRefreshing} variant="outline">
            <ArrowPathIcon className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Analyzing...' : 'Generate Suggestions'}
          </Button>
          {onClose && (
            <Button onClick={onClose} variant="ghost">
              Close
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-neutral-50 border-b flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SparklesIcon className="w-5 h-5 text-accent-500" />
          <h3 className="font-medium text-neutral-900">
            Review Suggestions
          </h3>
          <Badge variant="neutral">
            {pendingSuggestions.length} remaining
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={onRefresh}
            disabled={isRefreshing}
            className="text-neutral-600"
          >
            <ArrowPathIcon className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
          {onClose && (
            <Button size="sm" variant="ghost" onClick={onClose}>
              <XMarkIcon className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="px-4 py-2 bg-neutral-50 border-b flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentIndex((i) => Math.max(i - 1, 0))}
            disabled={currentIndex === 0}
            className="p-1 rounded hover:bg-neutral-200 disabled:opacity-30"
          >
            <ChevronUpIcon className="w-4 h-4" />
          </button>
          <span className="text-neutral-600">
            {currentIndex + 1} / {pendingSuggestions.length}
          </span>
          <button
            onClick={() => setCurrentIndex((i) => Math.min(i + 1, pendingSuggestions.length - 1))}
            disabled={currentIndex >= pendingSuggestions.length - 1}
            className="p-1 rounded hover:bg-neutral-200 disabled:opacity-30"
          >
            <ChevronDownIcon className="w-4 h-4" />
          </button>
        </div>
        <div className="text-neutral-500">
          <kbd className="px-1.5 py-0.5 bg-neutral-200 rounded text-xs">j/k</kbd>
          <span className="mx-1">navigate</span>
          <kbd className="px-1.5 py-0.5 bg-neutral-200 rounded text-xs">y</kbd>
          <span className="mx-1">accept</span>
          <kbd className="px-1.5 py-0.5 bg-neutral-200 rounded text-xs">n</kbd>
          <span className="mx-1">reject</span>
        </div>
      </div>

      {/* Current suggestion */}
      {currentSuggestion && (
        <div className="p-4">
          {/* Type badge */}
          <div className="flex items-center gap-2 mb-3">
            <Badge
              variant={
                currentSuggestion.suggestion_type === 'add'
                  ? 'default'
                  : currentSuggestion.suggestion_type === 'delete'
                  ? 'error'
                  : 'neutral'
              }
            >
              {getSuggestionTypeLabel(currentSuggestion.suggestion_type)}
            </Badge>
            {currentSuggestion.confidence !== undefined && (
              <span className="text-xs text-neutral-500">
                {Math.round(currentSuggestion.confidence * 100)}% confident
              </span>
            )}
            {currentSuggestion.section_id && currentSuggestion.section_id !== 'general' && (
              <span className="text-xs text-neutral-500">
                in {formatSectionName(currentSuggestion.section_id)}
              </span>
            )}
          </div>

          {/* Reason */}
          <p className="text-sm text-neutral-700 mb-4">
            {currentSuggestion.reason}
          </p>

          {/* Diff view */}
          <div className="space-y-3 mb-4">
            {/* Current content (for replace/delete) */}
            {currentSuggestion.current_content && (
              <div className="bg-error-50 border border-error-200 rounded-lg p-3">
                <div className="text-xs font-medium text-error-600 mb-1">
                  {currentSuggestion.suggestion_type === 'delete' ? 'Remove:' : 'Replace:'}
                </div>
                <p className="text-sm text-error-800 line-through whitespace-pre-wrap">
                  {currentSuggestion.current_content}
                </p>
              </div>
            )}

            {/* Suggested content (for add/replace/cite/clarify) */}
            {currentSuggestion.suggestion_type !== 'delete' && (
              <div className="bg-success-50 border border-success-200 rounded-lg p-3">
                <div className="text-xs font-medium text-success-600 mb-1">
                  {currentSuggestion.suggestion_type === 'add' ? 'Add:' : 'With:'}
                </div>
                <p className="text-sm text-success-800 whitespace-pre-wrap">
                  {currentSuggestion.suggested_content}
                </p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              onClick={handleReject}
              disabled={isLoading}
              className="text-neutral-600"
            >
              <XMarkIcon className="w-4 h-4 mr-2" />
              Reject
            </Button>
            <Button
              onClick={handleAccept}
              disabled={isLoading || accepting}
            >
              <CheckIcon className="w-4 h-4 mr-2" />
              {accepting ? 'Applying...' : 'Accept'}
            </Button>
          </div>
        </div>
      )}

      {/* Batch actions */}
      <div className="px-4 py-3 bg-neutral-50 border-t flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          onClick={onRejectAll}
          disabled={isLoading}
          className="text-error-600 hover:text-error-700"
        >
          Reject All
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onAcceptAll}
          disabled={isLoading}
          className="text-success-600 hover:text-success-700"
        >
          Accept All
        </Button>
      </div>
    </div>
  );
}

// Helpers
function getSuggestionTypeLabel(type: BriefSectionSuggestion['suggestion_type']): string {
  switch (type) {
    case 'add':
      return 'Add';
    case 'replace':
      return 'Replace';
    case 'delete':
      return 'Remove';
    case 'cite':
      return 'Citation';
    case 'clarify':
      return 'Clarify';
    default:
      return 'Suggestion';
  }
}

function formatSectionName(section: string): string {
  return section
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
