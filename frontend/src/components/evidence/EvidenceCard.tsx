/**
 * Evidence Card Component
 *
 * Displays a single evidence item with credibility rating, source preview,
 * and provenance information (source domain, retrieval method, published date).
 */

'use client';

import { useState } from 'react';
import { evidenceAPI, type Evidence } from '@/lib/api/evidence';

interface EvidenceCardProps {
  evidence: Evidence;
  onUpdate?: (evidence: Evidence) => void;
  showLinkButton?: boolean;
}

export function EvidenceCard({ evidence, onUpdate, showLinkButton }: EvidenceCardProps) {
  const [rating, setRating] = useState(evidence.user_credibility_rating || 0);
  const [isRating, setIsRating] = useState(false);
  const [showSource, setShowSource] = useState(false);

  const handleRate = async (newRating: number) => {
    setIsRating(true);
    try {
      const updated = await evidenceAPI.rate(evidence.id, newRating);
      setRating(newRating);
      onUpdate?.(updated);
    } catch (error) {
      console.error('Failed to rate evidence:', error);
    } finally {
      setIsRating(false);
    }
  };

  const getTypeBadgeColor = () => {
    switch (evidence.type) {
      case 'metric': return 'bg-accent-100 text-accent-800';
      case 'benchmark': return 'bg-purple-100 text-purple-800';
      case 'fact': return 'bg-green-100 text-green-800';
      case 'claim': return 'bg-yellow-100 text-yellow-800';
      case 'quote': return 'bg-pink-100 text-pink-800';
      default: return 'bg-neutral-100 text-neutral-800';
    }
  };

  return (
    <div className="border rounded-lg p-4 bg-white dark:bg-neutral-900 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <span className={`px-2 py-1 rounded text-xs font-medium ${getTypeBadgeColor()}`}>
          {evidence.type}
        </span>

        {/* Confidence indicator */}
        <div className="flex items-center gap-2 text-xs text-neutral-500">
          <span>Confidence: {Math.round(evidence.extraction_confidence * 100)}%</span>
        </div>
      </div>

      {/* Evidence text */}
      <p className="text-neutral-900 dark:text-neutral-100 mb-3">{evidence.text}</p>

      {/* Provenance bar */}
      {(evidence.source_domain || evidence.retrieval_method) && (
        <div className="flex flex-wrap items-center gap-1.5 mb-3">
          {evidence.retrieval_method && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400">
              <RetrievalIcon method={evidence.retrieval_method} />
              {getRetrievalLabel(evidence.retrieval_method)}
            </span>
          )}
          {evidence.source_domain && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-accent-50 text-accent-700 dark:bg-accent-900/20 dark:text-accent-400">
              {evidence.source_url ? (
                <a
                  href={evidence.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline flex items-center gap-1"
                  title={evidence.source_url}
                >
                  <ExternalLinkIcon />
                  {evidence.source_domain}
                </a>
              ) : (
                evidence.source_domain
              )}
            </span>
          )}
          {evidence.source_published_date && (
            <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
              {evidence.source_published_date}
            </span>
          )}
        </div>
      )}

      {/* Source info */}
      <div className="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
        <span className="font-medium">From:</span>{' '}
        {evidence.source_title || evidence.document_title}
        {evidence.chunk_preview && (
          <button
            onClick={() => setShowSource(!showSource)}
            className="ml-2 text-accent-600 hover:underline"
          >
            {showSource ? 'Hide' : 'Show'} source
          </button>
        )}
      </div>

      {/* Source preview */}
      {showSource && evidence.chunk_preview && (
        <div className="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded text-sm mb-3">
          <div className="text-xs text-neutral-500 mb-1">
            Chunk {evidence.chunk_preview.chunk_index} ({evidence.chunk_preview.token_count} tokens)
          </div>
          <p className="text-neutral-700 dark:text-neutral-300 italic">{evidence.chunk_preview.text_preview}</p>
        </div>
      )}

      {/* Rating */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-neutral-600 dark:text-neutral-400">Credibility:</span>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              onClick={() => handleRate(star)}
              disabled={isRating}
              className={`text-lg ${
                star <= rating ? 'text-yellow-400' : 'text-neutral-300 dark:text-neutral-600'
              } hover:text-yellow-500 disabled:opacity-50`}
            >
              ★
            </button>
          ))}
        </div>
        {rating > 0 && (
          <span className="text-sm text-neutral-500">({rating}/5)</span>
        )}
      </div>

      {/* Link button (optional) */}
      {showLinkButton && (
        <button className="mt-3 text-sm text-accent-600 hover:underline">
          Link to Signal
        </button>
      )}
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────

function getRetrievalLabel(method: string): string {
  switch (method) {
    case 'research_loop': return 'Research';
    case 'external_paste': return 'Pasted';
    case 'url_fetch': return 'URL';
    case 'chat_bridged': return 'Chat';
    case 'document_upload': return 'Document';
    case 'user_observation': return 'Observation';
    default: return method;
  }
}

function RetrievalIcon({ method }: { method: string }) {
  const cls = 'w-3 h-3';
  switch (method) {
    case 'research_loop':
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" strokeLinecap="round" />
        </svg>
      );
    case 'external_paste':
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2" strokeLinecap="round" strokeLinejoin="round" />
          <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
        </svg>
      );
    case 'url_fetch':
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case 'chat_bridged':
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    default:
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <path d="M14 2v6h6" strokeLinecap="round" />
        </svg>
      );
  }
}

function ExternalLinkIcon() {
  return (
    <svg className="w-3 h-3 inline-block" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="15 3 21 3 21 9" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="10" y1="14" x2="21" y2="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
