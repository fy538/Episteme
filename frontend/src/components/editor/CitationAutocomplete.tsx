/**
 * Citation autocomplete - suggests documents when typing [[...]]
 */

'use client';

import { useState, useEffect } from 'react';
import type { Editor } from '@tiptap/react';
import { documentsAPI } from '@/lib/api/documents';
import type { CaseDocument } from '@/lib/types/case';

interface CitationAutocompleteProps {
  editor: Editor | null;
  caseId: string;
}

export function CitationAutocomplete({ 
  editor, 
  caseId 
}: CitationAutocompleteProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<CaseDocument[]>([]);
  const [query, setQuery] = useState('');
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Load all documents for the case
  useEffect(() => {
    async function loadDocuments() {
      if (caseId) {
        try {
          const docs = await documentsAPI.getByCase(caseId);
          setSuggestions(docs);
        } catch (error) {
          console.error('Failed to load documents:', error);
        }
      }
    }
    loadDocuments();
  }, [caseId]);

  // Listen for [[ typing
  useEffect(() => {
    if (!editor) return;

    function handleUpdate() {
      const { from } = editor.state.selection;
      const textBefore = editor.state.doc.textBetween(
        Math.max(0, from - 50),
        from
      );

      // Check if typing [[
      const match = textBefore.match(/\[\[([^\]]*?)$/);
      
      if (match) {
        setQuery(match[1]);
        setIsOpen(true);
        setSelectedIndex(0);
      } else {
        setIsOpen(false);
      }
    }

    editor.on('update', handleUpdate);
    editor.on('selectionUpdate', handleUpdate);
    
    return () => {
      editor.off('update', handleUpdate);
      editor.off('selectionUpdate', handleUpdate);
    };
  }, [editor]);

  // Filter suggestions based on query
  const filteredSuggestions = suggestions.filter(d =>
    d.title.toLowerCase().includes(query.toLowerCase())
  ).slice(0, 5);

  function insertCitation(doc: CaseDocument) {
    if (!editor) return;

    const { from } = editor.state.selection;
    const textBefore = editor.state.doc.textBetween(
      Math.max(0, from - 50),
      from
    );
    const match = textBefore.match(/\[\[([^\]]*?)$/);
    
    if (match) {
      const startPos = from - match[0].length;
      editor
        .chain()
        .focus()
        .deleteRange({ from: startPos, to: from })
        .insertContent(`[[${doc.title}]]`)
        .run();
    }

    setIsOpen(false);
  }

  // Handle keyboard navigation
  useEffect(() => {
    if (!isOpen || !editor) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => 
          Math.min(prev + 1, filteredSuggestions.length - 1)
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (filteredSuggestions[selectedIndex]) {
          insertCitation(filteredSuggestions[selectedIndex]);
        }
      } else if (e.key === 'Escape') {
        setIsOpen(false);
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filteredSuggestions, selectedIndex, editor]);

  if (!isOpen || filteredSuggestions.length === 0) return null;

  return (
    <div className="fixed z-50 bg-white border border-gray-300 rounded-lg shadow-xl w-80">
      <div className="text-xs text-gray-500 px-3 py-2 border-b border-gray-200">
        Citation suggestions (↑↓ to navigate, ⏎ to select):
      </div>
      <div className="max-h-64 overflow-y-auto">
        {filteredSuggestions.map((doc, index) => (
          <button
            key={doc.id}
            onClick={() => insertCitation(doc)}
            className={`w-full text-left px-3 py-2 border-b border-gray-100 last:border-0 transition-colors ${
              index === selectedIndex ? 'bg-blue-50' : 'hover:bg-gray-50'
            }`}
          >
            <div className="font-medium text-gray-900 text-sm">{doc.title}</div>
            <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-2">
              <span>{doc.document_type.replace('_', ' ')}</span>
              {doc.times_cited > 0 && (
                <span>• Cited {doc.times_cited}x</span>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
