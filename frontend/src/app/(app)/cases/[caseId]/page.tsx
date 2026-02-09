/**
 * Case workspace page — two-column layout
 *
 * Layout (with AppShell providing SidebarPanel with tabs):
 *   [Main Content flex-1] [Chat + Companion ~380px]
 *
 * The case structure nav (plan, inquiries, assumptions) is now rendered
 * inside the SidebarPanel via CaseStructurePanelContent (drill-down pattern).
 *
 * The main content area defaults to CaseHome and switches between:
 *   - CaseHome (plan-driven dashboard)
 *   - UnifiedBriefView
 *   - InquiryWorkspaceView
 *   - InquiryDashboard
 *   - ReadinessChecklist
 *
 * Chat is always visible in the right column.
 * State management shared via CaseWorkspaceProvider context.
 */

'use client';

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { CaseHome } from '@/components/workspace/case/CaseHome';
import { UnifiedBriefView } from '@/components/workspace/UnifiedBriefView';
import { InquiryWorkspaceView } from '@/components/workspace/InquiryWorkspaceView';
import { InquiryDashboard } from '@/components/inquiries/InquiryDashboard';
import { ChatPanel } from '@/components/workspace/ChatPanel';
import { CompanionPanel } from '@/components/companion';
import { SettingsModal } from '@/components/settings/SettingsModal';
import { ExportDialog } from '@/components/workspace/ExportDialog';
import { CommandPalette, useCommandPalette, type Command } from '@/components/ui/CommandPalette';
import { DiffViewer } from '@/components/ui/DiffViewer';
import { Button } from '@/components/ui/button';
import { ReadinessChecklist } from '@/components/readiness';
import { DocumentListView } from '@/components/documents/DocumentListView';
import { useQueryClient } from '@tanstack/react-query';
import { documentsAPI } from '@/lib/api/documents';
import { plansAPI } from '@/lib/api/plans';
import { casesAPI } from '@/lib/api/cases';
import { useRequiredCaseWorkspace } from '@/components/workspace/CaseWorkspaceProvider';
import { useNavigation } from '@/components/navigation/NavigationProvider';
import { Skeleton, WorkspaceContentSkeleton } from '@/components/ui/skeleton';
import { Tooltip } from '@/components/ui/tooltip';
import { KeyboardShortcut, useKeyboardShortcut } from '@/components/ui/keyboard-shortcut';
import { motion, AnimatePresence } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { transitionDurations, easingCurves } from '@/lib/motion-config';
import type { ViewMode } from '@/hooks/useCaseWorkspace';
import type { ChatThread } from '@/lib/types/chat';
import { ChatBubbleIcon } from '@/components/ui/icons';

export default function CaseWorkspacePage({
  params,
}: {
  params: { caseId: string };
}) {
  const ws = useRequiredCaseWorkspace();
  const nav = useNavigation();
  const queryClient = useQueryClient();
  const { isOpen: commandPaletteOpen, setIsOpen: setCommandPaletteOpen } = useCommandPalette();
  const [chatPrefill, setChatPrefill] = useState<string | null>(null);
  const [chatSource, setChatSource] = useState<{ source_type: string; source_id: string } | null>(null);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const researchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up research timer on unmount
  useEffect(() => {
    return () => {
      if (researchTimerRef.current) {
        clearTimeout(researchTimerRef.current);
      }
    };
  }, []);

  // Merge title update handler into stream callbacks (memoized to avoid re-renders)
  const streamCallbacksWithTitle = useMemo(() => ({
    ...ws.streamCallbacks,
    onTitleUpdate: (title: string) => {
      queryClient.setQueryData(['thread', ws.threadId], (old: ChatThread | undefined) =>
        old ? { ...old, title } : old
      );
      queryClient.invalidateQueries({ queryKey: ['threads'] });
    },
  }), [ws.streamCallbacks, ws.threadId, queryClient]);

  // Handle generating a plan for planless cases
  const handleGeneratePlan = useCallback(async () => {
    try {
      await plansAPI.generatePlan(params.caseId);
      queryClient.invalidateQueries({ queryKey: ['case-home', params.caseId] });
      await ws.loadWorkspace();
    } catch (error) {
      console.error('Failed to generate plan:', error);
    }
  }, [params.caseId, queryClient, ws]);

  // Handle accepting a plan diff from inline card
  // Rethrows errors so the PlanDiffProposalCard can display them
  const handleAcceptPlanDiff = useCallback(async (
    proposedContent: Record<string, unknown>,
    diffSummary: string,
    diffData: Record<string, unknown>,
  ) => {
    try {
      await plansAPI.acceptDiff(params.caseId, proposedContent, diffSummary, diffData);
      queryClient.invalidateQueries({ queryKey: ['case-home', params.caseId] });
      ws.loadWorkspace(); // Refresh plan in sidebar
    } catch (error) {
      console.error('Failed to accept plan diff:', error);
      throw error; // Rethrow so card can show error UI
    }
  }, [params.caseId, queryClient, ws]);

  // Reduced motion preference (used for view transitions)
  const prefersReducedMotion = useReducedMotion();

  // View transition animation props
  const viewTransition = prefersReducedMotion
    ? {}
    : {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: -8 },
        transition: { duration: transitionDurations.fast, ease: easingCurves.easeOutCubic },
      };

  // Focus mode: collapse both global sidebar panel and chat panel
  const toggleFocusMode = useCallback(() => {
    const enterFocus = !nav.isPanelCollapsed || !ws.isChatCollapsed;
    nav.setPanelCollapsed(enterFocus);
    if (enterFocus && !ws.isChatCollapsed) ws.toggleChat();
    if (!enterFocus && ws.isChatCollapsed) ws.toggleChat();
  }, [nav, ws]);

  // Keyboard shortcuts for chat panel and focus mode
  useKeyboardShortcut(['Cmd', '/'], () => ws.toggleChat(), { enabled: !ws.loading });
  useKeyboardShortcut(['Cmd', '\\'], () => toggleFocusMode(), { enabled: !ws.loading });

  if (ws.loading || !ws.caseData) {
    return (
      <div className="flex flex-col h-full">
        {/* Skeleton breadcrumb */}
        <div className="flex items-center gap-1.5 px-4 py-2 border-b border-neutral-200/60 dark:border-neutral-800/60 bg-white dark:bg-neutral-950 shrink-0">
          <Skeleton className="h-3 w-10" />
          <Skeleton className="h-3 w-3 rounded-sm" />
          <Skeleton className="h-3 w-32" />
        </div>
        <div className="flex flex-1 min-h-0">
          {/* Skeleton main content */}
          <main className="flex-1 p-8">
            <WorkspaceContentSkeleton />
          </main>
          {/* Skeleton chat */}
          <aside className="w-[380px] border-l border-neutral-200/60 dark:border-neutral-800/60 shrink-0 p-4 space-y-3">
            <Skeleton className="h-6 w-20" />
            <div className="space-y-3 mt-4">
              {[1, 2, 3].map(i => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}
            </div>
            <div className="mt-auto pt-8">
              <Skeleton className="h-10 w-full rounded-lg" />
            </div>
          </aside>
        </div>
      </div>
    );
  }

  // Find project name for breadcrumbs
  const projectName = ws.caseData.project
    ? ws.projects.find(p => p.id === ws.caseData!.project)?.title
    : undefined;

  // Define commands for palette
  const commands: Command[] = [
    {
      id: 'go-to-home',
      label: 'Go to case home',
      category: 'navigation',
      keywords: ['home', 'dashboard', 'overview'],
      action: () => ws.handleViewHome(),
    },
    {
      id: 'go-to-brief',
      label: 'Go to case brief',
      category: 'navigation',
      keywords: ['back', 'brief', 'case'],
      action: () => ws.handleViewBrief(),
      shortcut: 'Esc',
    },
    {
      id: 'view-readiness',
      label: 'View decision readiness',
      category: 'navigation',
      keywords: ['readiness', 'checklist', 'ready', 'complete'],
      action: () => ws.setViewMode('readiness'),
      shortcut: 'Cmd+R',
    },
    {
      id: 'view-documents',
      label: 'View documents',
      category: 'navigation',
      keywords: ['documents', 'upload', 'files', 'pdf'],
      action: () => ws.setViewMode('document'),
    },
    {
      id: 'view-research',
      label: 'View research dashboard',
      category: 'navigation',
      keywords: ['research', 'inquiries', 'dashboard'],
      action: () => ws.setViewMode('inquiry-dashboard'),
    },
    {
      id: 'create-inquiry',
      label: 'Start new inquiry',
      category: 'actions',
      keywords: ['create', 'inquiry', 'question', 'new'],
      action: () => ws.handleStartInquiry(),
      shortcut: 'Cmd+I',
    },
    {
      id: 'create-case',
      label: 'Create new case',
      category: 'actions',
      keywords: ['create', 'case', 'new'],
      action: () => ws.handleCreateCase(),
      shortcut: 'Cmd+N',
    },
    {
      id: 'settings',
      label: 'Open settings',
      category: 'actions',
      keywords: ['settings', 'preferences', 'config'],
      action: () => ws.setSettingsOpen(true),
    },
    {
      id: 'detect-assumptions',
      label: 'Detect assumptions in brief',
      category: 'ai',
      keywords: ['assumptions', 'detect', 'analyze', 'ai'],
      action: async () => {
        if (ws.brief) {
          try {
            await documentsAPI.detectAssumptions(ws.brief.id);
            ws.loadWorkspace();
          } catch (error) {
            console.error('Failed to detect assumptions:', error);
          }
        }
      },
    },
    {
      id: 'generate-research',
      label: 'Generate research',
      category: 'ai',
      keywords: ['research', 'generate', 'ai'],
      action: async () => {
        // If viewing an inquiry, research that topic. Otherwise use case title.
        const topic = ws.activeInquiry?.title ?? ws.caseData?.title ?? 'General research';
        const workId = `research-cmd-${Date.now()}`;
        ws.addBackgroundWork({
          id: workId,
          type: 'research',
          title: `Researching: ${topic}`,
          status: 'running',
          startedAt: new Date().toISOString(),
        });
        try {
          await documentsAPI.generateResearch(params.caseId, topic);
          // Research runs async on backend — mark complete after a delay
          // (companion will show "running" until completed)
          researchTimerRef.current = setTimeout(() => {
            researchTimerRef.current = null;
            ws.completeBackgroundWork(workId);
            ws.addReceipt({
              id: `receipt-research-${Date.now()}`,
              type: 'research_completed',
              title: `Research completed: ${topic}`,
              timestamp: new Date().toISOString(),
              relatedCaseId: params.caseId,
            });
            ws.loadWorkspace();
          }, 60_000); // Approximate — backend research takes ~30-120s
        } catch (error) {
          console.error('Failed to start research:', error);
          ws.completeBackgroundWork(workId);
        }
      },
    },
    {
      id: 'toggle-outline',
      label: 'Toggle brief outline',
      category: 'navigation',
      keywords: ['outline', 'sidebar', 'toggle', 'brief'],
      action: () => {
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'o', metaKey: true, shiftKey: true }));
      },
      shortcut: 'Cmd+Shift+O',
    },
    {
      id: 'toggle-chat',
      label: 'Toggle chat panel',
      category: 'navigation',
      keywords: ['chat', 'panel', 'toggle', 'collapse'],
      action: () => ws.toggleChat(),
      shortcut: 'Cmd+/',
    },
    {
      id: 'focus-mode',
      label: 'Toggle focus mode',
      category: 'navigation',
      keywords: ['focus', 'fullscreen', 'zen', 'distraction'],
      action: () => toggleFocusMode(),
      shortcut: 'Cmd+\\',
    },
    {
      id: 'next-section',
      label: 'Jump to next section',
      category: 'navigation',
      keywords: ['next', 'section', 'jump', 'down'],
      action: () => {
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', metaKey: true }));
      },
      shortcut: 'Cmd+J',
    },
    {
      id: 'prev-section',
      label: 'Jump to previous section',
      category: 'navigation',
      keywords: ['previous', 'section', 'jump', 'up'],
      action: () => {
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', metaKey: true, shiftKey: true }));
      },
      shortcut: 'Cmd+Shift+J',
    },
    {
      id: 'export-brief',
      label: 'Export brief',
      category: 'actions',
      keywords: ['export', 'share', 'markdown', 'download', 'brief', 'json'],
      action: () => {
        setShowExportDialog(true);
      },
    },
    {
      id: 'copy-share-link',
      label: 'Copy share link',
      category: 'actions',
      keywords: ['share', 'copy', 'link', 'url'],
      action: () => {
        const url = `${window.location.origin}/cases/${params.caseId}`;
        navigator.clipboard.writeText(url).catch(() => {});
      },
    },
  ];

  // View label map for breadcrumb
  const VIEW_LABELS: Record<ViewMode, string> = {
    home: '',
    brief: 'Brief',
    inquiry: ws.activeInquiry?.title ?? 'Inquiry',
    'inquiry-dashboard': 'Research',
    readiness: 'Readiness',
    document: 'Documents',
  };
  const currentViewLabel = VIEW_LABELS[ws.viewMode];

  // Render the main content area based on viewMode
  const renderMainContent = () => {
    switch (ws.viewMode) {
      case 'home':
        return (
          <motion.div key="home" className="h-full" {...viewTransition}>
            <CaseHome
              caseId={params.caseId}
              onViewInquiry={ws.handleOpenInquiry}
              onViewAll={() => ws.setViewMode('inquiry-dashboard')}
              onChatAbout={(payload) => {
                setChatPrefill(payload.text);
                setChatSource({ source_type: payload.source_type, source_id: payload.source_id });
              }}
              onGeneratePlan={handleGeneratePlan}
            />
          </motion.div>
        );

      case 'brief':
        return (
          <motion.div key="brief" className="h-full" {...viewTransition}>
            <UnifiedBriefView
              caseData={ws.caseData!}
              brief={ws.brief}
              inquiries={ws.inquiries}
              onStartInquiry={ws.handleStartInquiry}
              onOpenInquiry={ws.handleOpenInquiry}
              onRefresh={ws.loadWorkspace}
            />
          </motion.div>
        );

      case 'readiness':
        return (
          <motion.div key="readiness" className="max-w-4xl mx-auto p-8" {...viewTransition}>
            <div className="mb-6">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl tracking-tight font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                    Decision Readiness
                  </h1>
                  <p className="text-neutral-600 dark:text-neutral-400">
                    Complete these items before deciding with confidence
                  </p>
                </div>
                <Button variant="outline" onClick={() => ws.handleViewHome()}>
                  Back to Home
                </Button>
              </div>
            </div>
            <ReadinessChecklist
              caseId={params.caseId}
              items={ws.checklistItems}
              progress={ws.checklistProgress}
              onRefresh={ws.loadChecklist}
            />
          </motion.div>
        );

      case 'inquiry-dashboard':
        return (
          <motion.div key="inquiry-dashboard" className="max-w-4xl mx-auto p-8" {...viewTransition}>
            <div className="mb-6">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl tracking-tight font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                    Investigation Dashboard
                  </h1>
                  <p className="text-neutral-600 dark:text-neutral-400">
                    Overview of all inquiries and investigation progress
                  </p>
                </div>
                <Button variant="outline" onClick={() => ws.handleViewHome()}>
                  Back to Home
                </Button>
              </div>
            </div>
            <InquiryDashboard
              caseId={params.caseId}
              onStartInquiry={(inquiryId) => ws.handleOpenInquiry(inquiryId)}
              onViewInquiry={(inquiryId) => ws.handleOpenInquiry(inquiryId)}
            />
          </motion.div>
        );

      case 'document':
        return (
          <motion.div key="document" className="h-full" {...viewTransition}>
            <DocumentListView
              caseId={params.caseId}
              projectId={ws.caseData!.project ?? ''}
              documents={ws.documents}
              onRefresh={ws.loadWorkspace}
            />
          </motion.div>
        );

      case 'inquiry':
        return ws.activeInquiry ? (
          <motion.div key={`inquiry-${ws.activeInquiry.id}`} {...viewTransition}>
            <InquiryWorkspaceView
              caseId={params.caseId}
              inquiry={ws.activeInquiry}
              onBack={() => ws.handleViewHome()}
              onRefresh={ws.loadWorkspace}
              briefId={ws.brief?.id}
              briefContent={ws.brief?.content_markdown || ''}
            />
          </motion.div>
        ) : null;

      default:
        return null;
    }
  };

  // Shared companion panel props
  const companionPanelProps = {
    thinking: ws.companionState.thinking,
    mode: ws.chatMode.mode.mode,
    actionHints: ws.actionHints,
    status: ws.companionState.status,
    sessionReceipts: ws.companionState.sessionReceipts,
    caseState: ws.companionState.caseState,
    rankedSections: ws.rankedSections,
    pinnedSection: ws.pinnedSection,
    onPinSection: ws.setPinnedSection,
    onActionHint: (hint: any) => {
      switch (hint.type) {
        case 'suggest_inquiry':
          ws.handleStartInquiry();
          break;
        case 'suggest_resolution':
          if (hint.data?.inquiryId) {
            ws.handleOpenInquiry(hint.data.inquiryId as string);
          }
          break;
      }
    },
    onDismissCompleted: ws.dismissCompleted,
    onViewCase: ws.handleViewBrief,
    onViewInquiries: () => ws.setViewMode('inquiry-dashboard'),
    onTogglePosition: ws.toggleCompanion,
    onClose: () => ws.setCompanionPosition('hidden'),
  };

  return (
    <>
      <div className="flex flex-col h-full">
        {/* Thin breadcrumb bar */}
        <div className="flex items-center gap-1.5 px-4 py-2 border-b border-neutral-200/60 dark:border-neutral-800/60 bg-white dark:bg-neutral-950 shrink-0">
          <Link
            href="/"
            className="text-xs text-neutral-400 hover:text-neutral-600 dark:text-neutral-500 dark:hover:text-neutral-300 transition-colors"
          >
            Home
          </Link>
          <ChevronRight />
          {projectName && (
            <>
              <span className="text-xs text-neutral-400 dark:text-neutral-500">{projectName}</span>
              <ChevronRight />
            </>
          )}
          {/* Case title — clickable to navigate back to case home */}
          <button
            onClick={ws.handleViewHome}
            className={cn(
              'text-xs truncate max-w-[240px] transition-colors',
              ws.viewMode === 'home'
                ? 'font-medium text-neutral-700 dark:text-neutral-200'
                : 'text-neutral-400 hover:text-neutral-600 dark:text-neutral-500 dark:hover:text-neutral-300'
            )}
          >
            {ws.caseData.title}
          </button>

          {/* Animated view label */}
          <AnimatePresence mode="wait">
            {currentViewLabel && (
              <motion.div
                key={ws.viewMode}
                className="flex items-center gap-1.5"
                initial={prefersReducedMotion ? { opacity: 1 } : { opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, x: 4 }}
                transition={{ duration: transitionDurations.fast, ease: easingCurves.easeOutCubic }}
              >
                <ChevronRight />
                <span className="text-xs font-medium text-neutral-700 dark:text-neutral-200 truncate max-w-[200px]">
                  {currentViewLabel}
                </span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Chat toggle button (shown when collapsed) */}
          {ws.isChatCollapsed && (
            <Tooltip content={<span className="flex items-center gap-2">Show chat <KeyboardShortcut keys={['⌘', '/']} /></span>} side="bottom">
              <button
                onClick={ws.toggleChat}
                className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
              >
                <ChatBubbleIcon className="w-3.5 h-3.5" />
              </button>
            </Tooltip>
          )}

          {/* Help button */}
          <Tooltip content={<span className="flex items-center gap-2">Shortcuts <KeyboardShortcut keys={['⌘', '⇧', '?']} /></span>} side="bottom">
            <button
              onClick={() => window.dispatchEvent(new CustomEvent('show-keyboard-help'))}
              className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
            >
              <QuestionMarkIcon className="w-3.5 h-3.5" />
            </button>
          </Tooltip>
        </div>

        {/* Two-column workspace (structure nav is in the SidebarPanel drill-down) */}
        <div className="flex flex-1 min-h-0">
          {/* Main Content */}
          <main className={cn(
            'flex-1 min-h-0',
            ws.viewMode === 'brief' ? 'overflow-hidden' : 'overflow-y-auto',
          )}>
            <AnimatePresence mode="wait" initial={false}>
              {renderMainContent()}
            </AnimatePresence>
          </main>

          {/* Right: Chat + Companion — collapsible */}
          {ws.isChatCollapsed ? (
            <aside className="w-10 border-l border-neutral-200/60 dark:border-neutral-800/60 shrink-0 flex flex-col items-center pt-3">
              <Tooltip content={<span className="flex items-center gap-2">Open chat <KeyboardShortcut keys={['⌘', '/']} /></span>} side="left">
                <button
                  onClick={ws.toggleChat}
                  className="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
                >
                  <ChatBubbleIcon className="w-4 h-4" />
                </button>
              </Tooltip>
            </aside>
          ) : (
            <aside className="w-[380px] border-l border-neutral-200/60 dark:border-neutral-800/60 shrink-0 flex flex-col h-full overflow-hidden">
              {/* Companion panel — collapsible, stacked above chat */}
              {ws.companionPosition === 'sidebar' && (
                <CompanionPanel
                  position="sidebar"
                  {...companionPanelProps}
                />
              )}
              {/* Chat panel — always visible */}
              <div className="flex-1 min-h-0">
                <ChatPanel
                  threadId={ws.threadId}
                  contextLabel={`Chat about: ${ws.caseData.title}`}
                  briefId={ws.brief?.id}
                  onIntegrationPreview={ws.setIntegrationPreview}
                  streamCallbacks={streamCallbacksWithTitle}
                  mode={ws.chatMode.mode}
                  onExitFocus={ws.chatMode.exitFocus}
                  prefillMessage={chatPrefill}
                  onPrefillConsumed={() => { setChatPrefill(null); setChatSource(null); }}
                  chatSource={chatSource}
                  onAcceptPlanDiff={handleAcceptPlanDiff}
                />
              </div>
            </aside>
          )}
        </div>
      </div>

      <SettingsModal isOpen={ws.settingsOpen} onClose={() => ws.setSettingsOpen(false)} />

      <ExportDialog
        caseId={params.caseId}
        caseTitle={ws.caseData?.title ?? 'Brief'}
        isOpen={showExportDialog}
        onClose={() => setShowExportDialog(false)}
      />

      <CommandPalette
        commands={commands}
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />

      {/* Integration Preview Modal */}
      {ws.integrationPreview && ws.brief && (
        <DiffViewer
          original={ws.brief.content_markdown || ''}
          proposed={ws.integrationPreview.updated_content as string}
          title="Add to Brief"
          onAccept={async (content) => {
            await documentsAPI.update(ws.brief!.id, { content_markdown: content });
            ws.setIntegrationPreview(null);
            ws.loadWorkspace();
          }}
          onReject={() => ws.setIntegrationPreview(null)}
          onClose={() => ws.setIntegrationPreview(null)}
        />
      )}
    </>
  );
}

// ─── Small icons ────────────────────────────────────

function ChevronRight() {
  return (
    <svg className="w-3 h-3 text-neutral-300 dark:text-neutral-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="9 18 15 12 9 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function QuestionMarkIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="12" y1="17" x2="12.01" y2="17" strokeLinecap="round" />
    </svg>
  );
}
