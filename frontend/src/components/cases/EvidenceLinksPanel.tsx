/**
 * EvidenceLinksPanel - Shows claims linked to evidence
 *
 * Displays:
 * - List of claims extracted from document
 * - Evidence links for each claim
 * - Coverage metrics
 * - Actions to add citations
 */

'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  LinkIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
  DocumentTextIcon,
  ArrowPathIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { useEvidenceLinks } from '@/hooks/useEvidenceLinks';

interface EvidenceLinksPanelProps {
  documentId: string;
  onNavigateToSignal?: (signalId: string) => void;
  onContentUpdated?: (newContent: string) => void;
}

export function EvidenceLinksPanel({
  documentId,
  onNavigateToSignal,
  onContentUpdated,
}: EvidenceLinksPanelProps) {
  const [showAll, setShowAll] = useState(false);
  const [citationPreview, setCitationPreview] = useState<string | null>(null);

  const {
    claims,
    summary,
    evidenceCoverage,
    isLoading,
    error,
    loadEvidenceLinks,
    addCitations,
    substantiatedClaims,
    unsubstantiatedClaims,
  } = useEvidenceLinks({ documentId });

  useEffect(() => {
    loadEvidenceLinks();
  }, [loadEvidenceLinks]);

  const handleAddCitations = async (save: boolean) => {
    const content = await addCitations(save);
    if (content) {
      if (save && onContentUpdated) {
        onContentUpdated(content);
      } else {
        setCitationPreview(content);
      }
    }
  };

  const displayClaims = showAll ? claims : claims.slice(0, 5);

  return (
    <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-neutral-50 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <LinkIcon className="w-5 h-5 text-accent-500" />
            <h3 className="font-medium text-neutral-900">Evidence Links</h3>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => loadEvidenceLinks()}
            disabled={isLoading}
          >
            <ArrowPathIcon
              className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}
            />
          </Button>
        </div>
      </div>

      {/* Coverage metrics */}
      {summary && (
        <div className="px-4 py-3 border-b">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-neutral-600">Evidence Coverage</span>
            <span className="text-sm font-medium">
              {Math.round(evidenceCoverage * 100)}%
            </span>
          </div>
          <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all ${
                evidenceCoverage >= 0.7
                  ? 'bg-success-500'
                  : evidenceCoverage >= 0.4
                  ? 'bg-warning-500'
                  : 'bg-error-500'
              }`}
              style={{ width: `${evidenceCoverage * 100}%` }}
            />
          </div>
          <div className="flex justify-between mt-2 text-xs text-neutral-500">
            <span>{summary.substantiated} substantiated</span>
            <span>{summary.unsubstantiated} need evidence</span>
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && claims.length === 0 && (
        <div className="p-8 text-center">
          <ArrowPathIcon className="w-8 h-8 text-neutral-300 animate-spin mx-auto mb-2" />
          <p className="text-sm text-neutral-500">Analyzing claims...</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-4 bg-error-50 text-error-700 text-sm">{error}</div>
      )}

      {/* Claims list */}
      {!isLoading && claims.length > 0 && (
        <div className="divide-y">
          {displayClaims.map((claim) => (
            <div key={claim.id} className="p-4">
              <div className="flex items-start gap-3">
                {claim.is_substantiated ? (
                  <CheckCircleIcon className="w-5 h-5 text-success-500 flex-shrink-0 mt-0.5" />
                ) : (
                  <ExclamationCircleIcon className="w-5 h-5 text-warning-500 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-neutral-800">"{claim.text}"</p>
                  <p className="text-xs text-neutral-500 mt-1">
                    {claim.location}
                  </p>

                  {/* Linked signals */}
                  {claim.linked_signals.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {claim.linked_signals.map((signal, idx) => (
                        <button
                          key={idx}
                          onClick={() => onNavigateToSignal?.(signal.signal_id)}
                          className="flex items-center gap-2 text-xs text-accent-600 hover:text-accent-700"
                        >
                          <DocumentTextIcon className="w-3.5 h-3.5" />
                          <span className="truncate">{signal.excerpt}</span>
                          <Badge variant="neutral" className="text-xs">
                            {Math.round(signal.relevance * 100)}%
                          </Badge>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Suggestion for unsubstantiated */}
                  {!claim.is_substantiated && claim.suggestion && (
                    <p className="text-xs text-warning-600 mt-2 italic">
                      💡 {claim.suggestion}
                    </p>
                  )}

                  {/* Confidence */}
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-neutral-500">Confidence:</span>
                    <div className="flex-1 max-w-20 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          claim.confidence >= 0.7
                            ? 'bg-success-500'
                            : claim.confidence >= 0.4
                            ? 'bg-warning-500'
                            : 'bg-error-500'
                        }`}
                        style={{ width: `${claim.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium">
                      {Math.round(claim.confidence * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Show more */}
          {claims.length > 5 && (
            <button
              onClick={() => setShowAll(!showAll)}
              className="w-full py-2 text-sm text-accent-600 hover:bg-accent-50 transition-colors"
            >
              {showAll ? 'Show less' : `Show ${claims.length - 5} more claims`}
            </button>
          )}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && claims.length === 0 && !error && (
        <div className="p-8 text-center">
          <LinkIcon className="w-8 h-8 text-neutral-300 mx-auto mb-2" />
          <p className="text-sm text-neutral-500">No claims extracted yet</p>
        </div>
      )}

      {/* Actions */}
      {claims.length > 0 && (
        <div className="px-4 py-3 bg-neutral-50 border-t flex items-center justify-between">
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleAddCitations(false)}
            disabled={isLoading || substantiatedClaims.length === 0}
          >
            Preview Citations
          </Button>
          <Button
            size="sm"
            onClick={() => handleAddCitations(true)}
            disabled={isLoading || substantiatedClaims.length === 0}
            className="flex items-center gap-2"
          >
            <SparklesIcon className="w-4 h-4" />
            Add {substantiatedClaims.length} Citations
          </Button>
        </div>
      )}

      {/* Citation preview modal */}
      {citationPreview && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
            <div className="px-4 py-3 border-b flex items-center justify-between">
              <h3 className="font-medium">Citation Preview</h3>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setCitationPreview(null)}
              >
                Close
              </Button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <pre className="text-sm text-neutral-700 whitespace-pre-wrap">
                {citationPreview}
              </pre>
            </div>
            <div className="px-4 py-3 border-t flex justify-end gap-2">
              <Button
                variant="ghost"
                onClick={() => setCitationPreview(null)}
              >
                Cancel
              </Button>
              <Button
                onClick={() => {
                  handleAddCitations(true);
                  setCitationPreview(null);
                }}
              >
                Apply Citations
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Compact coverage indicator
 */
export function EvidenceCoverageBadge({
  coverage,
  onClick,
}: {
  coverage: number;
  onClick?: () => void;
}) {
  const color =
    coverage >= 0.7
      ? 'text-success-600 bg-success-50'
      : coverage >= 0.4
      ? 'text-warning-600 bg-warning-50'
      : 'text-error-600 bg-error-50';

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${color} hover:opacity-90 transition-opacity`}
    >
      <LinkIcon className="w-3.5 h-3.5" />
      {Math.round(coverage * 100)}% linked
    </button>
  );
}
