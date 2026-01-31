/**
 * Evidence Card Component
 * 
 * Displays a single evidence item with credibility rating and source preview.
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
      case 'metric': return 'bg-blue-100 text-blue-800';
      case 'benchmark': return 'bg-purple-100 text-purple-800';
      case 'fact': return 'bg-green-100 text-green-800';
      case 'claim': return 'bg-yellow-100 text-yellow-800';
      case 'quote': return 'bg-pink-100 text-pink-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="border rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <span className={`px-2 py-1 rounded text-xs font-medium ${getTypeBadgeColor()}`}>
          {evidence.type}
        </span>
        
        {/* Confidence indicator */}
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>Confidence: {Math.round(evidence.extraction_confidence * 100)}%</span>
        </div>
      </div>

      {/* Evidence text */}
      <p className="text-gray-900 mb-3">{evidence.text}</p>

      {/* Source info */}
      <div className="text-sm text-gray-600 mb-3">
        <span className="font-medium">From:</span> {evidence.document_title}
        <button
          onClick={() => setShowSource(!showSource)}
          className="ml-2 text-blue-600 hover:underline"
        >
          {showSource ? 'Hide' : 'Show'} source
        </button>
      </div>

      {/* Source preview */}
      {showSource && (
        <div className="bg-gray-50 p-3 rounded text-sm mb-3">
          <div className="text-xs text-gray-500 mb-1">
            Chunk {evidence.chunk_preview.chunk_index} ({evidence.chunk_preview.token_count} tokens)
          </div>
          <p className="text-gray-700 italic">{evidence.chunk_preview.text_preview}</p>
        </div>
      )}

      {/* Rating */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600">Credibility:</span>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              onClick={() => handleRate(star)}
              disabled={isRating}
              className={`text-lg ${
                star <= rating ? 'text-yellow-400' : 'text-gray-300'
              } hover:text-yellow-500 disabled:opacity-50`}
            >
              ★
            </button>
          ))}
        </div>
        {rating > 0 && (
          <span className="text-sm text-gray-500">({rating}/5)</span>
        )}
      </div>

      {/* Link button (optional) */}
      {showLinkButton && (
        <button className="mt-3 text-sm text-blue-600 hover:underline">
          Link to Signal
        </button>
      )}
    </div>
  );
}
