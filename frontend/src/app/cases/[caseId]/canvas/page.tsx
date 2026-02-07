/**
 * Canvas Case Workspace - Graph-first decision workspace
 *
 * A cleaner, simpler case view that:
 * - Shows the decision graph by default
 * - Brief slides in when needed
 * - Minimizes visual clutter
 * - Focuses on graph thinking
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { CaseCanvas } from '@/components/workspace/CaseCanvas';
import { InquiryWorkspaceView } from '@/components/workspace/InquiryWorkspaceView';
import { CommandPalette, useCommandPalette, type Command } from '@/components/ui/CommandPalette';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { documentsAPI } from '@/lib/api/documents';
import { signalsAPI } from '@/lib/api/signals';
import { chatAPI } from '@/lib/api/chat';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import type { Case, CaseDocument, Inquiry } from '@/lib/types/case';

type ViewMode = 'canvas' | 'inquiry' | 'edit-brief';

export default function CanvasCaseWorkspacePage({
  params,
}: {
  params: { caseId: string };
}) {
  const router = useRouter();

  // Data state
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [brief, setBrief] = useState<CaseDocument | null>(null);
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('canvas');
  const [activeInquiryId, setActiveInquiryId] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  // Command palette
  const { isOpen: commandPaletteOpen, setIsOpen: setCommandPaletteOpen } = useCommandPalette();

  // Load workspace data
  const loadWorkspace = useCallback(async () => {
    try {
      const [caseResp, inqs, docs] = await Promise.all([
        casesAPI.getCase(params.caseId),
        inquiriesAPI.getByCase(params.caseId),
        documentsAPI.getByCase(params.caseId),
      ]);

      setCaseData(caseResp);
      setInquiries(inqs);

      // Find main brief
      const mainBrief = docs.find(d => d.id === caseResp.main_brief);
      setBrief(mainBrief || null);

      // Load signals for the case
      try {
        const sigs = await signalsAPI.getByCase(params.caseId);
        setSignals(sigs);
      } catch (e) {
        console.error('Failed to load signals:', e);
      }

      // Get or create thread for this case (shared with classic workspace)
      try {
        if (caseResp.linked_thread) {
          setThreadId(caseResp.linked_thread);
        } else {
          const thread = await chatAPI.createThread(null, { title: `Chat: ${caseResp.title}` });
          setThreadId(thread.id);
          await chatAPI.updateThread(thread.id, { primary_case: caseResp.id });
          await casesAPI.updateCase(caseResp.id, { linked_thread: thread.id });
        }
      } catch (e) {
        console.error('Failed to resolve chat thread:', e);
      }
    } catch (error) {
      console.error('Failed to load workspace:', error);
    } finally {
      setLoading(false);
    }
  }, [params.caseId]);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  // Handlers
  const handleInquiryClick = useCallback((inquiryId: string) => {
    setActiveInquiryId(inquiryId);
    setViewMode('inquiry');
  }, []);

  const handleAddInquiry = useCallback(async () => {
    if (!caseData) return;

    try {
      const inquiry = await inquiriesAPI.create({
        case: caseData.id,
        title: 'New Inquiry',
        status: 'open',
      });

      await loadWorkspace();
      setActiveInquiryId(inquiry.id);
      setViewMode('inquiry');
    } catch (error) {
      console.error('Failed to create inquiry:', error);
    }
  }, [caseData, loadWorkspace]);

  const handleCreateInquiryFromText = useCallback(async (text: string) => {
    if (!caseData) return;

    try {
      // Generate title from text
      const { title } = await inquiriesAPI.generateTitle(text);

      // Create inquiry
      const inquiry = await inquiriesAPI.create({
        case: caseData.id,
        title,
        description: `Validate: "${text}"`,
        origin_text: text,
        origin_document: brief?.id,
        status: 'open',
      });

      await loadWorkspace();
      setActiveInquiryId(inquiry.id);
      setViewMode('inquiry');
    } catch (error) {
      console.error('Failed to create inquiry:', error);
    }
  }, [caseData, brief, loadWorkspace]);

  const handleBackToCanvas = useCallback(() => {
    setViewMode('canvas');
    setActiveInquiryId(null);
  }, []);

  const handleEditBrief = useCallback(() => {
    // For now, redirect to classic view for full editing
    router.push(`/cases/${params.caseId}`);
  }, [router, params.caseId]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K for command palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(true);
      }
      // B for brief (when not in input)
      if (e.key === 'b' && !isInputFocused()) {
        // Brief panel is handled by CaseCanvas
      }
      // N for new inquiry
      if (e.key === 'n' && !isInputFocused()) {
        e.preventDefault();
        handleAddInquiry();
      }
      // Escape to go back
      if (e.key === 'Escape' && viewMode === 'inquiry') {
        handleBackToCanvas();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [viewMode, handleAddInquiry, handleBackToCanvas, setCommandPaletteOpen]);

  // Commands
  const commands: Command[] = [
    {
      id: 'back-to-canvas',
      label: 'Back to canvas',
      category: 'navigation',
      keywords: ['back', 'canvas', 'graph'],
      action: handleBackToCanvas,
      shortcut: 'Esc',
    },
    {
      id: 'create-inquiry',
      label: 'Create new inquiry',
      category: 'actions',
      keywords: ['create', 'inquiry', 'new'],
      action: handleAddInquiry,
      shortcut: 'N',
    },
    {
      id: 'classic-view',
      label: 'Switch to classic view',
      category: 'navigation',
      keywords: ['classic', 'old', 'brief'],
      action: () => router.push(`/cases/${params.caseId}`),
    },
    {
      id: 'toggle-chat',
      label: 'Toggle chat panel',
      category: 'actions',
      keywords: ['chat', 'ai', 'talk', 'message'],
      action: () => setChatOpen(prev => !prev),
      shortcut: 'C',
    },
  ];

  // Loading state
  if (loading || !caseData) {
    return (
      <div className="flex items-center justify-center h-screen bg-neutral-50">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-neutral-500">Loading decision workspace...</p>
        </div>
      </div>
    );
  }

  // Get active inquiry
  const activeInquiry = activeInquiryId
    ? inquiries.find(i => i.id === activeInquiryId)
    : null;

  return (
    <ErrorBoundary>
    <div className="h-screen flex flex-col bg-neutral-50">
      {/* Minimal header */}
      <header className="h-12 border-b border-neutral-200 bg-white px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/')}
            className="text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          <span className="text-sm font-medium text-neutral-900 truncate max-w-xs">
            {caseData.title}
          </span>
          {viewMode === 'inquiry' && activeInquiry && (
            <>
              <span className="text-neutral-300">/</span>
              <span className="text-sm text-neutral-600 truncate max-w-xs">
                {activeInquiry.title}
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* View toggle */}
          <button
            onClick={() => router.push(`/cases/${params.caseId}`)}
            className="text-xs text-neutral-500 hover:text-neutral-700 px-2 py-1 rounded hover:bg-neutral-100"
          >
            Classic view
          </button>

          {/* Command palette trigger */}
          <button
            onClick={() => setCommandPaletteOpen(true)}
            className="flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-600 px-2 py-1 rounded hover:bg-neutral-100"
          >
            <span>⌘K</span>
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        {viewMode === 'canvas' && (
          <CaseCanvas
            caseData={caseData}
            brief={brief}
            inquiries={inquiries}
            signals={signals}
            threadId={threadId || undefined}
            chatOpen={chatOpen}
            onChatOpenChange={setChatOpen}
            onInquiryClick={handleInquiryClick}
            onAddInquiry={handleAddInquiry}
            onEditBrief={handleEditBrief}
            onCreateInquiryFromText={handleCreateInquiryFromText}
            onRefresh={loadWorkspace}
          />
        )}

        {viewMode === 'inquiry' && activeInquiry && (
          <InquiryWorkspaceView
            caseId={params.caseId}
            inquiry={activeInquiry}
            onBack={handleBackToCanvas}
            onRefresh={loadWorkspace}
            briefId={brief?.id}
            briefContent={brief?.content_markdown || ''}
          />
        )}
      </main>

      {/* Command palette */}
      <CommandPalette
        commands={commands}
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />
    </div>
    </ErrorBoundary>
  );
}

// Helper
function isInputFocused(): boolean {
  const el = document.activeElement;
  return (
    el instanceof HTMLInputElement ||
    el instanceof HTMLTextAreaElement ||
    el?.getAttribute('contenteditable') === 'true'
  );
}
