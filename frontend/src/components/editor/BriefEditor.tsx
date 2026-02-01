/**
 * Brief editor - low friction editing with auto-save
 */

'use client';

import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { useDebounce } from 'use-debounce';
import { useEffect, useState } from 'react';
import { CitationAutocomplete } from './CitationAutocomplete';
import { EditorToolbar } from './EditorToolbar';
import { FloatingActionMenu } from './FloatingActionMenu';
import { documentsAPI } from '@/lib/api/documents';
import type { CaseDocument } from '@/lib/types/case';

interface BriefEditorProps {
  document: CaseDocument;
  onSave?: (content: string) => void;
  onCreateInquiry?: (selectedText: string) => void;
  onMarkAssumption?: (selectedText: string) => void;
}

export function BriefEditor({ document, onSave, onCreateInquiry, onMarkAssumption }: BriefEditorProps) {
  const [content, setContent] = useState(document.content_markdown);
  const [debouncedContent] = useDebounce(content, 1000); // 1s delay
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [selectedText, setSelectedText] = useState('');
  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 });
  const [showFloatingMenu, setShowFloatingMenu] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-blue-600 underline',
        },
      }),
      Placeholder.configure({
        placeholder: 'Start writing your brief... Use [[document-name]] to cite other documents.',
      }),
    ],
    content: document.content_markdown,
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[500px] px-6 py-4',
      },
    },
    onUpdate: ({ editor }) => {
      const markdown = editor.getHTML(); // Get HTML for now, can parse to markdown later
      setContent(markdown);
    },
    onSelectionUpdate: ({ editor }) => {
      const { from, to } = editor.state.selection;
      const text = editor.state.doc.textBetween(from, to);
      
      if (text.length >= 10) {
        // Get selection position
        const selection = window.getSelection();
        if (selection && selection.rangeCount > 0) {
          const range = selection.getRangeAt(0);
          const rect = range.getBoundingClientRect();
          
          setSelectedText(text);
          setMenuPosition({ x: rect.left + rect.width / 2, y: rect.top });
          setShowFloatingMenu(true);
        }
      } else {
        setShowFloatingMenu(false);
      }
    },
  });

  // Auto-save on content change
  useEffect(() => {
    async function save() {
      if (debouncedContent && debouncedContent !== document.content_markdown) {
        setIsSaving(true);
        try {
          await documentsAPI.updateDocument(document.id, debouncedContent);
          setLastSaved(new Date());
          onSave?.(debouncedContent);
        } catch (error) {
          console.error('Auto-save failed:', error);
        } finally {
          setIsSaving(false);
        }
      }
    }
    save();
  }, [debouncedContent, document.content_markdown, document.id, onSave]);

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header with title and save status */}
      <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between bg-white">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">
            {document.title}
          </h1>
          <p className="text-sm text-gray-600">
            {document.document_type === 'case_brief' ? 'Case Brief' : 'Inquiry Brief'} • Edit freely
          </p>
        </div>
        <div className="text-sm text-gray-500">
          {isSaving && 'Saving...'}
          {!isSaving && lastSaved && `Saved ${lastSaved.toLocaleTimeString()}`}
        </div>
      </div>

      {/* Toolbar */}
      <EditorToolbar editor={editor} />

      {/* Editor */}
      <div className="flex-1 overflow-y-auto">
        <EditorContent editor={editor} />
      </div>

      {/* Citation autocomplete */}
      <CitationAutocomplete
        editor={editor}
        caseId={document.case}
      />
      
      {/* Floating action menu for selected text */}
      <FloatingActionMenu
        visible={showFloatingMenu}
        x={menuPosition.x}
        y={menuPosition.y}
        onCreateInquiry={() => onCreateInquiry?.(selectedText)}
        onMarkAssumption={() => onMarkAssumption?.(selectedText)}
        onClose={() => setShowFloatingMenu(false)}
      />
    </div>
  );
}
