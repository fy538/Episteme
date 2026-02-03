/**
 * Inquiry suggestions component
 */

'use client';

import { useState } from 'react';
import type { InquirySuggestion } from '@/lib/types/signal';
import { Button } from '@/components/ui/button';
import { inquiriesAPI } from '@/lib/api/inquiries';

export function InquirySuggestions({ 
  suggestions,
  onInquiryCreated 
}: { 
  suggestions: InquirySuggestion[];
  onInquiryCreated?: () => void;
}) {
  const [creating, setCreating] = useState<string | null>(null);

  async function handleCreateInquiry(suggestion: InquirySuggestion) {
    setCreating(suggestion.signal.id);
    try {
      // Promote signal to inquiry
      await inquiriesAPI.promoteSignal(
        suggestion.signal.id,
        suggestion.suggested_title
      );
      
      // Notify parent to refresh
      onInquiryCreated?.();
    } catch (error) {
      console.error('Failed to create inquiry:', error);
    } finally {
      setCreating(null);
    }
  }

  if (suggestions.length === 0) return null;

  return (
    <div className="p-3 bg-accent-50 border border-accent-200 rounded-lg">
      <h3 className="text-sm font-semibold text-accent-900 mb-2">
        Suggested Inquiries ({suggestions.length})
      </h3>
      <p className="text-xs text-accent-700 mb-3">
        These signals appear important enough to investigate
      </p>
      <div className="space-y-3">
        {suggestions.map(suggestion => (
          <div key={suggestion.signal.id} className="bg-white p-2 rounded border border-accent-200">
            <p className="text-sm text-neutral-900 font-medium mb-1">
              {suggestion.suggested_title}
            </p>
            <p className="text-xs text-neutral-600 mb-2">
              {suggestion.reason} • {suggestion.similar_count}x mentioned
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleCreateInquiry(suggestion)}
              disabled={creating === suggestion.signal.id}
            >
              {creating === suggestion.signal.id ? 'Creating...' : 'Create Inquiry'}
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
