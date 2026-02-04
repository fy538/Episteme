/**
 * useBriefSuggestions - Hook for managing AI suggestions for brief documents
 *
 * Handles fetching, accepting, rejecting suggestions with optimistic updates.
 */

import { useState, useCallback } from 'react';
import { documentsAPI } from '@/lib/api/documents';
import type { BriefSectionSuggestion } from '@/components/cases/BriefSuggestion';

interface UseBriefSuggestionsOptions {
  documentId: string;
  onContentUpdate?: (newContent: string) => void;
}

interface UseBriefSuggestionsReturn {
  suggestions: BriefSectionSuggestion[];
  isLoading: boolean;
  isGenerating: boolean;
  error: string | null;
  generateSuggestions: (maxSuggestions?: number) => Promise<void>;
  acceptSuggestion: (
    suggestion: BriefSectionSuggestion,
    editedContent?: string
  ) => Promise<void>;
  rejectSuggestion: (suggestion: BriefSectionSuggestion) => void;
  acceptAllSuggestions: () => Promise<void>;
  rejectAllSuggestions: () => void;
  clearSuggestions: () => void;
  pendingCount: number;
}

export function useBriefSuggestions({
  documentId,
  onContentUpdate,
}: UseBriefSuggestionsOptions): UseBriefSuggestionsReturn {
  const [suggestions, setSuggestions] = useState<BriefSectionSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateSuggestions = useCallback(
    async (maxSuggestions: number = 5) => {
      if (!documentId) return;

      setIsGenerating(true);
      setError(null);

      try {
        const newSuggestions = await documentsAPI.generateSuggestions(
          documentId,
          maxSuggestions
        );

        // Map to BriefSectionSuggestion format
        const mappedSuggestions: BriefSectionSuggestion[] = newSuggestions.map(
          (s) => ({
            id: s.id,
            section_id: s.section_id,
            suggestion_type: s.suggestion_type,
            current_content: s.current_content ?? undefined,
            suggested_content: s.suggested_content,
            reason: s.reason,
            linked_signal_id: s.linked_signal_id ?? undefined,
            confidence: s.confidence,
            status: 'pending' as const,
          })
        );

        setSuggestions(mappedSuggestions);
      } catch (err) {
        console.error('Failed to generate suggestions:', err);
        setError(
          err instanceof Error ? err.message : 'Failed to generate suggestions'
        );
      } finally {
        setIsGenerating(false);
      }
    },
    [documentId]
  );

  const acceptSuggestion = useCallback(
    async (suggestion: BriefSectionSuggestion, editedContent?: string) => {
      if (!documentId) return;

      setIsLoading(true);

      // Optimistically update the suggestion status
      setSuggestions((prev) =>
        prev.map((s) =>
          s.id === suggestion.id ? { ...s, status: 'accepted' as const } : s
        )
      );

      try {
        const result = await documentsAPI.applySuggestion(documentId, {
          id: suggestion.id,
          suggestion_type: suggestion.suggestion_type,
          current_content: suggestion.current_content,
          suggested_content: editedContent ?? suggestion.suggested_content,
          section_id: suggestion.section_id,
        });

        // Notify parent of content update
        if (onContentUpdate && result.updated_content) {
          onContentUpdate(result.updated_content);
        }

        // Remove the suggestion from the list
        setSuggestions((prev) => prev.filter((s) => s.id !== suggestion.id));
      } catch (err) {
        console.error('Failed to apply suggestion:', err);
        // Revert optimistic update
        setSuggestions((prev) =>
          prev.map((s) =>
            s.id === suggestion.id ? { ...s, status: 'pending' as const } : s
          )
        );
        setError(
          err instanceof Error ? err.message : 'Failed to apply suggestion'
        );
      } finally {
        setIsLoading(false);
      }
    },
    [documentId, onContentUpdate]
  );

  const rejectSuggestion = useCallback((suggestion: BriefSectionSuggestion) => {
    setSuggestions((prev) =>
      prev.map((s) =>
        s.id === suggestion.id ? { ...s, status: 'rejected' as const } : s
      )
    );

    // Remove after animation
    setTimeout(() => {
      setSuggestions((prev) => prev.filter((s) => s.id !== suggestion.id));
    }, 300);
  }, []);

  const clearSuggestions = useCallback(() => {
    setSuggestions([]);
    setError(null);
  }, []);

  const acceptAllSuggestions = useCallback(async () => {
    const pending = suggestions.filter((s) => s.status === 'pending');
    if (pending.length === 0) return;

    setIsLoading(true);

    for (const suggestion of pending) {
      try {
        const result = await documentsAPI.applySuggestion(documentId, {
          id: suggestion.id,
          suggestion_type: suggestion.suggestion_type,
          current_content: suggestion.current_content,
          suggested_content: suggestion.suggested_content,
          section_id: suggestion.section_id,
        });

        // Update content after each suggestion
        if (onContentUpdate && result.updated_content) {
          onContentUpdate(result.updated_content);
        }
      } catch (err) {
        console.error(`Failed to apply suggestion ${suggestion.id}:`, err);
      }
    }

    // Clear all suggestions
    setSuggestions([]);
    setIsLoading(false);
  }, [suggestions, documentId, onContentUpdate]);

  const rejectAllSuggestions = useCallback(() => {
    setSuggestions((prev) =>
      prev.map((s) =>
        s.status === 'pending' ? { ...s, status: 'rejected' as const } : s
      )
    );

    // Remove after animation
    setTimeout(() => {
      setSuggestions([]);
    }, 300);
  }, []);

  const pendingCount = suggestions.filter((s) => s.status === 'pending').length;

  return {
    suggestions,
    isLoading,
    isGenerating,
    error,
    generateSuggestions,
    acceptSuggestion,
    rejectSuggestion,
    acceptAllSuggestions,
    rejectAllSuggestions,
    clearSuggestions,
    pendingCount,
  };
}
