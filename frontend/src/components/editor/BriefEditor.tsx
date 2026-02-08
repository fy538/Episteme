/**
 * Brief editor - low friction editing with auto-save and section awareness
 *
 * Features:
 * - TipTap rich text editor with auto-save (1s debounce)
 * - AI ghost text completions (Tab/Escape)
 * - Citation autocomplete ([[doc-name]])
 * - Floating action menu on text selection
 * - Version history with one-click restore
 * - Section marker awareness for grounding gutter integration
 */

'use client';

import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { useDebounce } from 'use-debounce';
import { useEffect, useState, useCallback, useRef } from 'react';
import { CitationAutocomplete } from './CitationAutocomplete';
import { EditorToolbar } from './EditorToolbar';
import { FloatingActionMenu } from './FloatingActionMenu';
import { InlineSuggestion } from './InlineSuggestion';
import { SuggestionMark } from './SuggestionMark';
import { SuggestionPopover } from './SuggestionPopover';
import { SectionNode, preprocessSectionMarkers, postprocessSectionMarkers } from './SectionNode';
import { SectionGroundingGutter } from './SectionGroundingGutter';
import { documentsAPI } from '@/lib/api/documents';
import type { CaseDocument, BriefSection } from '@/lib/types/case';
import type { BriefSectionSuggestion } from '@/components/cases/BriefSuggestion';

interface DocumentVersion {
  id: string;
  version: number;
  diff_summary: string;
  created_by: 'user' | 'ai_suggestion' | 'ai_task' | 'auto_save' | 'restore';
  task_description: string;
  created_at: string;
}

const VERSION_LABELS: Record<string, string> = {
  user: 'Manual edit',
  ai_suggestion: 'AI suggestion',
  ai_task: 'AI task',
  auto_save: 'Auto-save',
  restore: 'Restored',
};

interface BriefEditorProps {
  document: CaseDocument;
  onSave?: (content: string) => void;
  onCreateInquiry?: (selectedText: string) => void;
  onMarkAssumption?: (selectedText: string) => void;
  /** Enable AI ghost text completions (Tab to accept, Escape to dismiss) */
  inlineEnabled?: boolean;
  /** Inline suggestion marks from AI suggestions */
  suggestions?: BriefSectionSuggestion[];
  onAcceptSuggestion?: (suggestion: BriefSectionSuggestion, editedContent?: string) => void;
  onRejectSuggestion?: (suggestion: BriefSectionSuggestion) => void;
  /** Section data for grounding gutter (optional — gutter only renders when provided) */
  sections?: BriefSection[];
  /** Currently active section ID (marker ID, e.g. "sf-abc12345") */
  activeSectionId?: string | null;
  /** Called when cursor moves into a different section */
  onActiveSectionChange?: (sectionId: string | null) => void;
  /** Hide the built-in header (when embedded in UnifiedBriefView which has its own header) */
  hideHeader?: boolean;
}

export function BriefEditor({
  document,
  onSave,
  onCreateInquiry,
  onMarkAssumption,
  inlineEnabled = false,
  suggestions,
  onAcceptSuggestion,
  onRejectSuggestion,
  sections,
  activeSectionId,
  onActiveSectionChange,
  hideHeader = false,
}: BriefEditorProps) {
  const [content, setContent] = useState(document.content_markdown);
  const [debouncedContent] = useDebounce(content, 1000); // 1s delay
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [selectedText, setSelectedText] = useState('');
  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 });
  const [showFloatingMenu, setShowFloatingMenu] = useState(false);

  // Version history state
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);

  // Suggestion popover state
  const [activeSuggestion, setActiveSuggestion] = useState<BriefSectionSuggestion | null>(null);
  const [popoverPosition, setPopoverPosition] = useState({ x: 0, y: 0 });
  const editorContainerRef = useRef<HTMLDivElement>(null);

  // Preprocess content to convert section markers for TipTap
  const initialContent = preprocessSectionMarkers(document.content_markdown);

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
          class: 'text-accent-600 underline',
        },
      }),
      Placeholder.configure({
        placeholder: 'Start writing your brief... Use [[document-name]] to cite other documents.',
      }),
      SuggestionMark,
      SectionNode,
    ],
    content: initialContent,
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[500px] px-6 py-4',
      },
      handleClick: (view, pos, event) => {
        // Check if clicked element is a suggestion mark
        const target = event.target as HTMLElement;
        const markEl = target.closest('[data-suggestion-id]');
        if (markEl && suggestions) {
          const suggestionId = markEl.getAttribute('data-suggestion-id');
          const suggestion = suggestions.find((s) => s.id === suggestionId);
          if (suggestion) {
            const rect = markEl.getBoundingClientRect();
            setPopoverPosition({ x: rect.left, y: rect.bottom });
            setActiveSuggestion(suggestion);
            return true; // Prevent default
          }
        }
        return false;
      },
    },
    onUpdate: ({ editor }) => {
      // Postprocess to convert section marker divs back to comments for storage
      const html = editor.getHTML();
      const processed = postprocessSectionMarkers(html);
      setContent(processed);
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

      // Track which section the cursor is in
      if (onActiveSectionChange && sections) {
        const resolved = editor.state.doc.resolve(from);
        let sectionId: string | null = null;

        // Walk backwards through the document to find the nearest section marker
        for (let pos = from; pos >= 0; pos--) {
          try {
            const node = editor.state.doc.nodeAt(pos);
            if (node?.type.name === 'sectionMarker') {
              sectionId = node.attrs.sectionId;
              break;
            }
          } catch {
            // Position may be invalid, continue searching
          }
        }

        onActiveSectionChange(sectionId);
      }
    },
  });

  // Apply suggestion marks to editor when suggestions change
  useEffect(() => {
    if (!editor || !suggestions) return;

    // Clear all existing suggestion marks first
    const { doc, tr } = editor.state;
    let modified = false;
    doc.descendants((node, pos) => {
      node.marks.forEach((mark) => {
        if (mark.type.name === 'suggestion') {
          tr.removeMark(pos, pos + node.nodeSize, mark.type);
          modified = true;
        }
      });
    });
    if (modified) {
      editor.view.dispatch(tr);
    }

    // Apply marks for pending suggestions
    const pendingSuggestions = suggestions.filter((s) => s.status === 'pending');
    for (const suggestion of pendingSuggestions) {
      const content = suggestion.current_content || suggestion.suggested_content;
      if (!content) continue;

      // For delete/replace: find current_content in the document and mark it
      if (
        (suggestion.suggestion_type === 'replace' || suggestion.suggestion_type === 'delete') &&
        suggestion.current_content
      ) {
        const searchText = suggestion.current_content;
        const docText = editor.state.doc.textContent;
        const index = docText.indexOf(searchText);
        if (index !== -1) {
          // Convert text offset to prosemirror position
          let from = 0;
          let found = false;
          editor.state.doc.descendants((node, pos) => {
            if (found) return false;
            if (node.isText && node.text) {
              const nodeText = node.text;
              const localIndex = docText.indexOf(searchText, from) - from;
              if (localIndex >= 0 && from + localIndex === index) {
                // Found the text node containing our match
                const markType = suggestion.suggestion_type === 'replace' ? 'replace_old' : 'delete';
                editor.commands.setTextSelection({
                  from: pos + localIndex,
                  to: pos + localIndex + searchText.length,
                });
                editor.commands.setSuggestion({
                  suggestionId: suggestion.id,
                  type: markType,
                  newContent: suggestion.suggested_content,
                });
                found = true;
                return false;
              }
            }
            from = pos + node.nodeSize;
          });
          // Reset selection to avoid visual selection
          if (found) {
            editor.commands.setTextSelection(0);
          }
        }
      }

      // For add/cite/clarify: find the insertion point near suggested location
      // These don't have current_content to mark, so we skip inline marks for now
      // They'll still appear in the review panel
    }
  }, [editor, suggestions]);

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

  // Load version history
  const loadVersionHistory = useCallback(async () => {
    setIsLoadingVersions(true);
    try {
      const history = await documentsAPI.getVersionHistory(document.id);
      setVersions(history);
    } catch (error) {
      console.error('Failed to load version history:', error);
    } finally {
      setIsLoadingVersions(false);
    }
  }, [document.id]);

  // Toggle version history panel
  const handleToggleVersionHistory = useCallback(() => {
    const newShow = !showVersionHistory;
    setShowVersionHistory(newShow);
    if (newShow) {
      loadVersionHistory();
    }
  }, [showVersionHistory, loadVersionHistory]);

  // Restore a version
  const handleRestoreVersion = useCallback(async (versionId: string, versionNumber: number) => {
    setIsRestoring(true);
    try {
      const result = await documentsAPI.restoreVersion(document.id, versionId);
      if (result.success && editor) {
        const preprocessed = preprocessSectionMarkers(result.content);
        editor.commands.setContent(preprocessed);
        setContent(result.content);
        setLastSaved(new Date());
        // Refresh version list to show the restore snapshot
        loadVersionHistory();
      }
    } catch (error) {
      console.error('Failed to restore version:', error);
    } finally {
      setIsRestoring(false);
    }
  }, [document.id, editor, loadVersionHistory]);

  // Scroll to a section marker in the editor
  const scrollToSection = useCallback((sectionId: string) => {
    if (!editorContainerRef.current) return;
    const marker = editorContainerRef.current.querySelector(`[data-section-id="${sectionId}"]`);
    if (marker) {
      marker.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  const showGutter = !!sections && sections.length > 0;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-neutral-950">
      {/* Header with title, save status, and version history */}
      {!hideHeader && (
        <div className="border-b border-neutral-200 dark:border-neutral-800 px-6 py-4 flex items-center justify-between bg-white dark:bg-neutral-950">
          <div>
            <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
              {document.title}
            </h1>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              {document.document_type === 'case_brief' ? 'Case Brief' : 'Inquiry Brief'} • Edit freely
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-sm text-neutral-500">
              {isSaving && 'Saving...'}
              {!isSaving && lastSaved && `Saved ${lastSaved.toLocaleTimeString()}`}
            </div>
            <button
              onClick={handleToggleVersionHistory}
              className={`text-xs px-2.5 py-1.5 rounded-md border transition-colors ${
                showVersionHistory
                  ? 'bg-accent-50 border-accent-200 text-accent-700'
                  : 'border-neutral-200 text-neutral-600 hover:bg-neutral-50'
              }`}
            >
              History
            </button>
          </div>
        </div>
      )}

      {/* Save status bar (when header is hidden, show compact status) */}
      {hideHeader && (
        <div className="flex items-center justify-between px-4 py-1.5 border-b border-neutral-100 dark:border-neutral-900 bg-neutral-50/50 dark:bg-neutral-900/50">
          <div className="text-xs text-neutral-400">
            {isSaving && 'Saving...'}
            {!isSaving && lastSaved && `Saved ${lastSaved.toLocaleTimeString()}`}
          </div>
          <button
            onClick={handleToggleVersionHistory}
            className={`text-xs px-2 py-1 rounded-md border transition-colors ${
              showVersionHistory
                ? 'bg-accent-50 border-accent-200 text-accent-700'
                : 'border-neutral-200 dark:border-neutral-700 text-neutral-500 hover:bg-neutral-50 dark:hover:bg-neutral-800'
            }`}
          >
            History
          </button>
        </div>
      )}

      {/* Version History Panel (slides down) */}
      {showVersionHistory && (
        <div className="border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900 max-h-64 overflow-y-auto">
          <div className="px-6 py-3">
            <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-2">
              Version History
            </h3>
            {isLoadingVersions ? (
              <p className="text-sm text-neutral-400 py-2">Loading...</p>
            ) : versions.length === 0 ? (
              <p className="text-sm text-neutral-400 py-2">No version history yet. Versions are created when AI edits are applied.</p>
            ) : (
              <div className="space-y-1">
                {versions.map((v) => (
                  <div
                    key={v.id}
                    className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 group"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-neutral-400">v{v.version}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          v.created_by === 'ai_task' ? 'bg-purple-100 text-purple-700' :
                          v.created_by === 'ai_suggestion' ? 'bg-blue-100 text-blue-700' :
                          v.created_by === 'restore' ? 'bg-amber-100 text-amber-700' :
                          'bg-neutral-100 text-neutral-600'
                        }`}>
                          {VERSION_LABELS[v.created_by] || v.created_by}
                        </span>
                        <span className="text-xs text-neutral-500 truncate">
                          {v.diff_summary || v.task_description}
                        </span>
                      </div>
                      <span className="text-xs text-neutral-400">
                        {new Date(v.created_at).toLocaleString()}
                      </span>
                    </div>
                    <button
                      onClick={() => handleRestoreVersion(v.id, v.version)}
                      disabled={isRestoring}
                      className="opacity-0 group-hover:opacity-100 text-xs px-2 py-1 rounded border border-neutral-300 text-neutral-600 hover:bg-white hover:border-neutral-400 transition-all disabled:opacity-50"
                    >
                      {isRestoring ? 'Restoring...' : 'Restore'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Toolbar */}
      <EditorToolbar editor={editor} />

      {/* Editor area with optional grounding gutter */}
      <div ref={editorContainerRef} className="flex-1 overflow-y-auto flex">
        {/* Grounding gutter — only renders when sections are provided */}
        {showGutter && (
          <SectionGroundingGutter
            sections={sections!}
            activeSectionId={activeSectionId ?? null}
            editorContainerRef={editorContainerRef}
            onSectionClick={(sectionId) => {
              onActiveSectionChange?.(sectionId);
              scrollToSection(sectionId);
            }}
          />
        )}

        {/* Editor content */}
        <div className="flex-1 min-w-0">
          <EditorContent editor={editor} />
        </div>
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

      {/* AI ghost text completions */}
      <InlineSuggestion
        editor={editor}
        documentId={document.id}
        enabled={inlineEnabled}
      />

      {/* Suggestion popover for inline marks */}
      {activeSuggestion && (
        <SuggestionPopover
          suggestion={activeSuggestion}
          position={popoverPosition}
          onAccept={(s, edited) => {
            onAcceptSuggestion?.(s, edited);
            setActiveSuggestion(null);
          }}
          onReject={(s) => {
            onRejectSuggestion?.(s);
            setActiveSuggestion(null);
          }}
          onClose={() => setActiveSuggestion(null)}
        />
      )}
    </div>
  );
}
