/**
 * InlineSuggestion - Ghost text completion for the editor
 *
 * Shows AI-suggested completions as ghost text that can be
 * accepted with Tab or rejected with Escape.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { Editor } from '@tiptap/react';
import { documentsAPI } from '@/lib/api/documents';

interface InlineSuggestionProps {
  editor: Editor | null;
  documentId: string;
  enabled?: boolean;
  debounceMs?: number;
}

export function InlineSuggestion({
  editor,
  documentId,
  enabled = true,
  debounceMs = 1000,
}: InlineSuggestionProps) {
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [suggestionPosition, setSuggestionPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Handle keyboard events for accepting/rejecting suggestions
  useEffect(() => {
    if (!editor || !enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (!suggestion) return;

      if (event.key === 'Tab') {
        event.preventDefault();
        // Accept the suggestion
        editor.commands.insertContent(suggestion);
        setSuggestion(null);
      } else if (event.key === 'Escape') {
        // Reject the suggestion
        setSuggestion(null);
      } else if (
        event.key !== 'Shift' &&
        event.key !== 'Control' &&
        event.key !== 'Alt' &&
        event.key !== 'Meta'
      ) {
        // Any other key dismisses the suggestion
        setSuggestion(null);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [editor, suggestion, enabled]);

  // Fetch suggestions when user pauses typing
  useEffect(() => {
    if (!editor || !enabled || !documentId) return;

    let timeoutId: NodeJS.Timeout;

    const handleUpdate = () => {
      // Clear any pending suggestion fetch
      clearTimeout(timeoutId);
      setSuggestion(null);

      // Wait for user to pause
      timeoutId = setTimeout(async () => {
        const { from } = editor.state.selection;
        const content = editor.getText();

        // Only suggest if cursor is at end of content or line
        const cursorAtEnd = from === editor.state.doc.content.size;
        const textBefore = content.slice(0, from);
        const cursorAtLineEnd = textBefore.endsWith('\n') || cursorAtEnd;

        if (!cursorAtLineEnd && textBefore.length < 20) return;

        // Get context
        const contextBefore = textBefore.slice(-200);
        const contextAfter = content.slice(from, from + 100);

        // Skip if too little context
        if (contextBefore.trim().length < 10) return;

        setIsLoading(true);

        try {
          const result = await documentsAPI.getInlineCompletion(
            documentId,
            contextBefore,
            contextAfter,
            50
          );

          if (result.completion) {
            setSuggestion(result.completion);

            // Calculate position for ghost text
            const selection = window.getSelection();
            if (selection && selection.rangeCount > 0) {
              const range = selection.getRangeAt(0);
              const rect = range.getBoundingClientRect();
              setSuggestionPosition({
                top: rect.top,
                left: rect.left,
              });
            }
          }
        } catch (err) {
          console.error('Inline suggestion error:', err);
        } finally {
          setIsLoading(false);
        }
      }, debounceMs);
    };

    editor.on('update', handleUpdate);
    return () => {
      clearTimeout(timeoutId);
      editor.off('update', handleUpdate);
    };
  }, [editor, enabled, documentId, debounceMs]);

  // Don't render anything if no suggestion
  if (!suggestion || !suggestionPosition) return null;

  return (
    <div
      className="fixed pointer-events-none z-50"
      style={{
        top: suggestionPosition.top,
        left: suggestionPosition.left,
      }}
    >
      <span className="text-neutral-400 italic">{suggestion}</span>
      <span className="ml-2 text-xs text-neutral-300 bg-neutral-100 px-1 rounded">
        Tab to accept
      </span>
    </div>
  );
}

/**
 * Hook for managing inline suggestions
 */
export function useInlineSuggestions(
  editor: Editor | null,
  documentId: string,
  enabled: boolean = true
) {
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const acceptSuggestion = useCallback(() => {
    if (!editor || !suggestion) return;
    editor.commands.insertContent(suggestion);
    setSuggestion(null);
  }, [editor, suggestion]);

  const rejectSuggestion = useCallback(() => {
    setSuggestion(null);
  }, []);

  const triggerSuggestion = useCallback(async () => {
    if (!editor || !documentId) return;

    const { from } = editor.state.selection;
    const content = editor.getText();
    const contextBefore = content.slice(Math.max(0, from - 200), from);
    const contextAfter = content.slice(from, from + 100);

    if (contextBefore.trim().length < 10) return;

    setIsLoading(true);

    try {
      // This would call the backend for suggestions
      // For now, return a placeholder
      setSuggestion(null);
    } catch (err) {
      console.error('Failed to get suggestion:', err);
    } finally {
      setIsLoading(false);
    }
  }, [editor, documentId]);

  return {
    suggestion,
    isLoading,
    acceptSuggestion,
    rejectSuggestion,
    triggerSuggestion,
  };
}
