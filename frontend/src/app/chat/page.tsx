/**
 * Chat page with structure sidebar and mode-aware companion
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ConversationsSidebar } from '@/components/chat/ConversationsSidebar';
import { ReasoningCompanion } from '@/components/chat/ReasoningCompanion';
import { ChatModeHeader } from '@/components/chat/ChatModeHeader';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import { Button } from '@/components/ui/button';
import { ResponsiveLayout } from '@/components/layout/ResponsiveLayout';
import { NetworkErrorBanner } from '@/components/ui/network-error-banner';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { chatAPI } from '@/lib/api/chat';
import { authAPI } from '@/lib/api/auth';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import type { ChatThread, InlineActionCard, ActionHint } from '@/lib/types/chat';
import { projectsAPI } from '@/lib/api/projects';
import type { Project } from '@/lib/types/project';
import type { EvidenceLandscape } from '@/lib/types/case';
import type { Signal } from '@/lib/types/signal';
import type {
  CompanionState,
  SessionReceipt,
  BackgroundWorkItem,
} from '@/lib/types/companion';
import { useOptimisticUpdate } from '@/hooks/useOptimisticUpdate';
import { useKeyboardShortcut } from '@/components/ui/keyboard-shortcut';
import { useIsMobile } from '@/hooks/useResponsive';
import { useChatMode } from '@/hooks/useChatMode';
import type { InlineCardActions } from '@/components/chat/cards/InlineActionCardRenderer';

export default function ChatPage() {
  const router = useRouter();
  const [threadId, setThreadId] = useState<string | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);
  const [showConversations, setShowConversations] = useState(true);
  const [showStructure, setShowStructure] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [threadProjectId, setThreadProjectId] = useState<string | null>(null);
  const { execute: executeOptimistic } = useOptimisticUpdate();
  const [networkError, setNetworkError] = useState(false);
  const isMobile = useIsMobile();

  // Companion panel state
  const [reflection, setReflection] = useState('');
  const [isReflectionStreaming, setIsReflectionStreaming] = useState(false);
  const [signals, setSignals] = useState<Signal[]>([]);

  // Mode system
  const {
    mode,
    transitionToCase,
    focusOnInquiry,
    exitFocus,
    exitCase,
  } = useChatMode({
    threadId,
    initialCaseId: caseId,
    initialCaseName: threads.find(t => t.id === threadId)?.title,
  });

  // Inline action cards
  const [inlineCards, setInlineCards] = useState<InlineActionCard[]>([]);

  // Session receipts (loaded from backend)
  const [sessionReceipts, setSessionReceipts] = useState<SessionReceipt[]>([]);

  // Background work tracking
  const [backgroundWork, setBackgroundWork] = useState<{
    inProgress: BackgroundWorkItem[];
    justCompleted: BackgroundWorkItem[];
  }>({ inProgress: [], justCompleted: [] });

  // Track last assistant message ID for inline cards
  const [lastAssistantMessageId, setLastAssistantMessageId] = useState<string | null>(null);

  // Case evidence landscape for real CaseState data
  const [evidenceLandscape, setEvidenceLandscape] = useState<EvidenceLandscape | null>(null);

  // Build full companion state (always defined)
  const companionState: CompanionState = {
    mode,
    thinking: {
      content: reflection,
      isStreaming: isReflectionStreaming,
    },
    status: backgroundWork,
    sessionReceipts,
    caseState: caseId ? {
      caseId,
      caseName: mode.caseName || 'Untitled Case',
      inquiries: {
        open: evidenceLandscape?.inquiries.open ?? 0,
        resolved: evidenceLandscape?.inquiries.resolved ?? 0,
      },
      assumptions: {
        validated: evidenceLandscape?.assumptions.validated ?? 0,
        unvalidated: evidenceLandscape?.assumptions.untested ?? 0,
      },
      evidenceGaps: evidenceLandscape?.unlinked_claims.length ?? 0,
    } : undefined,
  };

  // Keyboard shortcuts
  useKeyboardShortcut(['Cmd', 'N'], handleCreateThread);
  useKeyboardShortcut(['Cmd', 'B'], () => setShowConversations(prev => !prev));

  // Track assistant response count for auto-title generation
  const [assistantResponseCount, setAssistantResponseCount] = useState(0);
  const [streamingTitleThreadId, setStreamingTitleThreadId] = useState<string | null>(null);

  // Reset companion state when thread changes
  useEffect(() => {
    setReflection('');
    setSignals([]);
    setAssistantResponseCount(0);
    setInlineCards([]);
    setSessionReceipts([]);
    setBackgroundWork({ inProgress: [], justCompleted: [] });
    setLastAssistantMessageId(null);
    setEvidenceLandscape(null);
  }, [threadId]);

  // Fetch evidence landscape when case is selected
  useEffect(() => {
    async function loadEvidenceLandscape() {
      if (!caseId) {
        setEvidenceLandscape(null);
        return;
      }

      try {
        const landscape = await casesAPI.getEvidenceLandscape(caseId);
        setEvidenceLandscape(landscape);
      } catch (err) {
        console.error('[Chat] Failed to load evidence landscape:', err);
      }
    }

    loadEvidenceLandscape();
  }, [caseId]);

  // Fetch session receipts when thread changes
  useEffect(() => {
    async function loadSessionReceipts() {
      if (!threadId) return;

      try {
        const receipts = await chatAPI.getSessionReceipts(threadId);
        setSessionReceipts(receipts.map(r => ({
          id: r.id,
          type: r.type as SessionReceipt['type'],
          title: r.title,
          detail: r.detail,
          timestamp: r.timestamp,
          relatedCaseId: r.relatedCaseId,
        })));
      } catch (err) {
        console.error('[Chat] Failed to load session receipts:', err);
      }
    }

    loadSessionReceipts();
  }, [threadId]);

  // Generate title after 2nd assistant response (streaming)
  const handleTitleGeneration = useCallback(async () => {
    if (!threadId) return;

    // Check if thread already has a custom title
    const thread = threads.find(t => t.id === threadId);
    if (thread?.title && thread.title !== 'New Chat' && !thread.title.startsWith('Chat ')) {
      return; // Already has a custom title
    }

    // Mark as streaming
    setStreamingTitleThreadId(threadId);

    try {
      await chatAPI.streamTitle(threadId, {
        onChunk: (delta) => {
          // Update title incrementally as it streams
          setThreads(prev =>
            prev.map(t => {
              if (t.id === threadId) {
                const currentTitle = t.title === 'New Chat' ? '' : (t.title || '');
                return { ...t, title: currentTitle + delta };
              }
              return t;
            })
          );
        },
        onComplete: (title, generated) => {
          setStreamingTitleThreadId(null);
          if (generated && title) {
            // Ensure final title is set
            setThreads(prev =>
              prev.map(t => t.id === threadId ? { ...t, title } : t)
            );
            // Title generated successfully
          }
        },
        onError: (error) => {
          setStreamingTitleThreadId(null);
          console.error('[Chat] Failed to generate title:', error);
        },
      });
    } catch (err) {
      setStreamingTitleThreadId(null);
      console.error('[Chat] Failed to generate title:', err);
    }
  }, [threadId, threads]);

  // Inline card handlers (must be defined before unifiedStreamCallbacks)
  const addInlineCard = useCallback((card: Omit<InlineActionCard, 'id' | 'createdAt'>) => {
    const newCard: InlineActionCard = {
      ...card,
      id: `card-${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
    setInlineCards(prev => [...prev, newCard]);
  }, []);

  const dismissInlineCard = useCallback((cardId: string) => {
    setInlineCards(prev =>
      prev.map(c => c.id === cardId ? { ...c, dismissed: true } : c)
    );
  }, []);

  // Handle AI action hints - convert to inline cards
  const handleActionHints = useCallback((hints: ActionHint[]) => {
    if (!hints || hints.length === 0 || !lastAssistantMessageId) return;

    for (const hint of hints) {
      // Map action hint types to inline card types
      let cardType: InlineActionCard['type'] | null = null;
      let cardData: Record<string, unknown> = {};

      switch (hint.type) {
        case 'suggest_case':
          // Only suggest case in casual mode
          if (mode.mode !== 'casual') continue;
          // Check if we already have a case creation prompt
          if (inlineCards.some(c => c.type === 'case_creation_prompt' && !c.dismissed)) continue;

          cardType = 'case_creation_prompt';
          cardData = {
            signalCount: (hint.data.signal_count as number) || signals.length,
            suggestedTitle: hint.data.suggested_title as string,
            aiReason: hint.reason,
          };
          break;

        case 'suggest_inquiry':
          cardType = 'inquiry_focus_prompt';
          cardData = {
            inquiryId: '', // Will be created if user accepts
            inquiryTitle: (hint.data.question as string) || '',
            matchedTopic: (hint.data.topic as string) || '',
            aiReason: hint.reason,
          };
          break;

        case 'suggest_evidence':
          // Only in case mode
          if (mode.mode === 'casual') continue;
          cardType = 'evidence_suggestion';
          cardData = {
            evidenceText: hint.data.text as string,
            direction: (hint.data.direction as string) || 'neutral',
            suggestedInquiryId: hint.data.inquiry_id as string,
            aiReason: hint.reason,
          };
          break;

        case 'suggest_resolution':
          // Only if we have an inquiry
          if (!hint.data.inquiry_id) continue;
          cardType = 'inquiry_resolution';
          cardData = {
            inquiryId: hint.data.inquiry_id as string,
            inquiryTitle: (hint.data.inquiry_title as string) || 'Inquiry',
            suggestedConclusion: hint.data.suggested_conclusion as string,
            aiReason: hint.reason,
          };
          break;
      }

      if (cardType) {
        addInlineCard({
          type: cardType,
          afterMessageId: lastAssistantMessageId,
          data: cardData,
        });
      }
    }
  }, [mode.mode, signals.length, lastAssistantMessageId, inlineCards, addInlineCard]);

  // Unified stream callbacks for ChatInterface
  const unifiedStreamCallbacks = {
    onReflectionChunk: useCallback((delta: string) => {
      setIsReflectionStreaming(true);
      setReflection(prev => prev + delta);
    }, []),
    onReflectionComplete: useCallback((content: string) => {
      setReflection(content);
      setIsReflectionStreaming(false);
    }, []),
    onSignals: useCallback((newSignals: Signal[]) => {
      setSignals(prev => {
        // Merge new signals, avoiding duplicates
        const existingIds = new Set(prev.map(s => s.id));
        const unique = newSignals.filter(s => !existingIds.has(s.id));
        return [...prev, ...unique];
      });
    }, []),
    onActionHints: handleActionHints,
    onMessageComplete: useCallback((messageId?: string) => {
      // Track the last assistant message ID for inline cards
      if (messageId) {
        setLastAssistantMessageId(messageId);
      }

      setAssistantResponseCount(prev => {
        const newCount = prev + 1;
        // Trigger title generation after 2nd response
        if (newCount === 2) {
          handleTitleGeneration();
        }
        return newCount;
      });
    }, [handleTitleGeneration]),
  };

  // Handle case creation from inline card
  const handleCreateCaseFromCard = useCallback(async (suggestedTitle?: string) => {
    if (!threadId) return;

    try {
      const title = suggestedTitle || 'New Decision';

      // Create case via API
      const { case: newCase } = await casesAPI.createCase(title, threadProjectId || undefined);

      // Update thread to link to this case
      await chatAPI.updateThread(threadId, { primary_case: newCase.id });

      // Update local state
      setCaseId(newCase.id);

      // Transition to case mode
      transitionToCase(newCase.id, newCase.title);

      // Add session receipt
      setSessionReceipts(prev => [{
        id: `receipt-${Date.now()}`,
        type: 'case_created',
        title: `Case created: ${newCase.title}`,
        timestamp: new Date().toISOString(),
        relatedCaseId: newCase.id,
      }, ...prev]);

      // Dismiss the case creation card
      const caseCard = inlineCards.find(c => c.type === 'case_creation_prompt' && !c.dismissed);
      if (caseCard) {
        dismissInlineCard(caseCard.id);
      }
    } catch (err) {
      console.error('Failed to create case:', err);
    }
  }, [threadId, threadProjectId, transitionToCase, inlineCards, dismissInlineCard]);

  // Handle inquiry focus from inline card
  const handleFocusInquiry = useCallback((inquiryId: string, inquiryTitle?: string) => {
    focusOnInquiry(inquiryId, inquiryTitle || 'Inquiry');
  }, [focusOnInquiry]);

  // Handle resolving an inquiry
  const handleResolveInquiry = useCallback(async (inquiryId: string, conclusion?: string) => {
    if (!conclusion) {
      console.warn('[Chat] No conclusion provided for inquiry resolution');
      return;
    }

    try {
      // Pass threadId for backend receipt recording
      const resolvedInquiry = await inquiriesAPI.resolve(inquiryId, conclusion, threadId || undefined);

      // Add local session receipt for immediate UI feedback
      setSessionReceipts(prev => [{
        id: `receipt-${Date.now()}`,
        type: 'inquiry_resolved',
        title: `Resolved: ${resolvedInquiry.title || 'Inquiry'}`,
        detail: conclusion.slice(0, 100),
        timestamp: new Date().toISOString(),
        relatedCaseId: caseId || undefined,
      }, ...prev]);

      // Refresh evidence landscape to update counts
      if (caseId) {
        const landscape = await casesAPI.getEvidenceLandscape(caseId);
        setEvidenceLandscape(landscape);
      }

      // Dismiss the resolution card
      const resolutionCard = inlineCards.find(
        c => c.type === 'inquiry_resolution' &&
        (c.data as { inquiryId?: string })?.inquiryId === inquiryId &&
        !c.dismissed
      );
      if (resolutionCard) {
        dismissInlineCard(resolutionCard.id);
      }
    } catch (err) {
      console.error('Failed to resolve inquiry:', err);
    }
  }, [threadId, caseId, inlineCards, dismissInlineCard]);

  // Handle adding more evidence to an inquiry
  const handleAddMoreEvidence = useCallback((inquiryId: string) => {
    // Navigate to the inquiry detail page for adding evidence
    if (caseId) {
      router.push(`/workspace/cases/${caseId}?inquiry=${inquiryId}&action=add-evidence`);
    }
  }, [caseId, router]);

  // Handle viewing research results
  const handleViewResearchResults = useCallback((researchId: string) => {
    // Navigate to research results - future feature
    // router.push(`/research/${researchId}`);
  }, []);

  // Handle adding research to case
  const handleAddResearchToCase = useCallback(async (researchId: string) => {
    // Will be implemented with research feature
  }, []);

  // Handle adding evidence from chat
  const handleAddEvidence = useCallback((inquiryId?: string, direction?: string) => {
    if (!inquiryId) {
      console.warn('[Chat] No inquiry ID for evidence');
      return;
    }
    // Navigate to inquiry with evidence context
    if (caseId) {
      router.push(`/workspace/cases/${caseId}?inquiry=${inquiryId}&action=add-evidence&direction=${direction || 'neutral'}`);
    }
  }, [caseId, router]);

  // Inline card actions object
  const inlineCardActions: InlineCardActions = {
    onCreateCase: handleCreateCaseFromCard,
    onFocusInquiry: handleFocusInquiry,
    onDismissCard: dismissInlineCard,
    onAddEvidence: handleAddEvidence,
    onResolveInquiry: handleResolveInquiry,
    onAddMoreEvidence: handleAddMoreEvidence,
    onViewResearchResults: handleViewResearchResults,
    onAddResearchToCase: handleAddResearchToCase,
  };

  // Companion panel handlers
  const handleViewCase = useCallback(() => {
    if (caseId) {
      router.push(`/cases/${caseId}`);
    }
  }, [caseId, router]);

  const handleViewInquiries = useCallback(() => {
    if (caseId) {
      router.push(`/cases/${caseId}?tab=inquiries`);
    }
  }, [caseId, router]);

  const handleReceiptClick = useCallback((receipt: SessionReceipt) => {
    if (receipt.relatedCaseId) {
      router.push(`/cases/${receipt.relatedCaseId}`);
    }
  }, [router]);

  const handleDismissCompleted = useCallback((id: string) => {
    setBackgroundWork(prev => ({
      ...prev,
      justCompleted: prev.justCompleted.filter(w => w.id !== id),
    }));
  }, []);

  // Check auth before loading
  useEffect(() => {
    async function checkAuth() {
      const isDevMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
      if (isDevMode) {
        setAuthReady(true);
        return;
      }

      const ok = await authAPI.ensureAuthenticated();
      if (!ok) {
        router.push('/login');
        return;
      }
      setAuthReady(true);
    }

    checkAuth();
  }, [router]);

  // Load threads on mount
  useEffect(() => {
    async function initThread() {
      if (!authReady) return;
      try {
        setIsLoadingThreads(true);
        const list = await chatAPI.listThreads({ archived: showArchived ? 'all' : 'false' });
        setThreads(list);

        if (list.length === 0) {
          const created = await chatAPI.createThread();
          setThreads([created]);
          setThreadId(created.id);
          setCaseId(created.primary_case || null);
          setThreadProjectId(created.project || null);
        } else {
          setThreadId(list[0].id);
        }
      } catch (err) {
        console.error('Failed to create thread:', err);
        setError(err instanceof Error ? err.message : 'Failed to connect to API');
        setNetworkError(true);
      } finally {
        setIsLoadingThreads(false);
        setIsLoading(false);
      }
    }
    initThread();
  }, [authReady, showArchived]);

  useEffect(() => {
    async function loadProjects() {
      if (!authReady) return;
      try {
        const list = await projectsAPI.listProjects();
        setProjects(list.filter(p => !p.is_archived));
      } catch (err) {
        console.error('Failed to load projects:', err);
      }
    }
    loadProjects();
  }, [authReady]);

  // Load thread details when selection changes
  useEffect(() => {
    async function loadThread() {
      if (!threadId) return;
      try {
        const thread = await chatAPI.getThread(threadId);
        setCaseId(thread.primary_case || null);
        setThreadProjectId(thread.project || null);
      } catch (err) {
        console.error('Failed to load thread details:', err);
      }
    }
    loadThread();
  }, [threadId]);

  async function handleCreateThread() {
    // Create optimistic thread with temporary ID
    const optimisticThread: ChatThread = {
      id: `temp-${Date.now()}`,
      title: 'New Chat',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      user: 'current-user', // Placeholder
      project: threadProjectId || undefined,
      archived: false,
    };

    await executeOptimistic(
      // Optimistic update - add immediately
      () => {
        setThreads(prev => [optimisticThread, ...prev]);
        setThreadId(optimisticThread.id);
      },
      // API call
      async () => {
        const created = await chatAPI.createThread(threadProjectId);
        // Update with real thread
        setThreads(prev => prev.map(t => t.id === optimisticThread.id ? created : t));
        setThreadId(created.id);
        setCaseId(created.primary_case || null);
        setThreadProjectId(created.project || null);
        return created;
      },
      // Rollback on error
      () => {
        setThreads(prev => prev.filter(t => t.id !== optimisticThread.id));
        setThreadId(threads.length > 0 ? threads[0].id : null);
      },
      {
        errorMessage: 'Failed to create conversation',
      }
    );
  }

  async function handleDeleteThread(threadIdToDelete: string) {
    const deletedThread = threads.find(t => t.id === threadIdToDelete);
    if (!deletedThread) return;

    await executeOptimistic(
      // Optimistic update - remove immediately
      () => {
        setThreads(prev => {
          const remaining = prev.filter(t => t.id !== threadIdToDelete);
          if (threadId === threadIdToDelete && remaining.length > 0) {
            setThreadId(remaining[0].id);
          }
          return remaining;
        });
      },
      // API call
      async () => {
        await chatAPI.deleteThread(threadIdToDelete);
        // If was last thread, create new one
        if (threads.length === 1) {
          const created = await chatAPI.createThread();
          setThreads([created]);
          setThreadId(created.id);
          setCaseId(created.primary_case || null);
        }
      },
      // Rollback on error
      () => {
        setThreads(prev => [...prev, deletedThread].sort((a, b) => 
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        ));
        setThreadId(threadIdToDelete);
      },
      {
        successMessage: 'Conversation deleted',
        errorMessage: 'Failed to delete conversation',
      }
    );
  }

  async function handleRenameThread(threadIdToRename: string, title: string) {
    try {
      const updated = await chatAPI.updateThread(threadIdToRename, { title });
      setThreads(prev =>
        prev.map(t => (t.id === updated.id ? updated : t))
      );
    } catch (err) {
      console.error('Failed to rename thread:', err);
    }
  }

  async function handleArchiveThread(threadIdToArchive: string, archived: boolean) {
    try {
      const updated = await chatAPI.updateThread(threadIdToArchive, { archived });
      setThreads(prev => {
        const next = prev.map(t => (t.id === updated.id ? updated : t));
        if (!showArchived) {
          return next.filter(t => !t.archived);
        }
        return next;
      });
      if (archived && !showArchived && threadId === threadIdToArchive) {
        const remaining = threads.filter(t => t.id !== threadIdToArchive && !t.archived);
        if (remaining.length > 0) {
          setThreadId(remaining[0].id);
        } else {
          const created = await chatAPI.createThread();
          setThreads([created]);
          setThreadId(created.id);
          setCaseId(created.primary_case || null);
        }
      }
    } catch (err) {
      console.error('Failed to archive thread:', err);
    }
  }

  async function handleChangeThreadProject(nextProjectId: string | null) {
    if (!threadId) return;
    try {
      const updated = await chatAPI.updateThread(threadId, { project: nextProjectId });
      setThreadProjectId(updated.project || null);
      setThreads(prev =>
        prev.map(t => (t.id === updated.id ? updated : t))
      );
    } catch (err) {
      console.error('Failed to update thread project:', err);
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-neutral-500">Connecting to backend...</p>
          <p className="text-xs text-neutral-400 mt-2">Make sure Django is running on localhost:8000</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center max-w-md">
          <p className="text-error-600 font-semibold mb-2">Connection Error</p>
          <p className="text-sm text-neutral-600 mb-4">{error}</p>
          <div className="text-left bg-neutral-50 p-4 rounded border border-neutral-200">
            <p className="text-xs font-semibold text-neutral-700 mb-2">Troubleshooting:</p>
            <ol className="text-xs text-neutral-600 space-y-1 list-decimal list-inside">
              <li>Ensure Django is running: <code className="bg-neutral-200 px-1">python manage.py runserver</code></li>
              <li>Check backend is on localhost:8000</li>
              <li>Check CORS settings in Django</li>
              <li>Check browser console for details</li>
            </ol>
          </div>
          <Button 
            onClick={() => window.location.reload()}
            className="mt-4"
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  if (!threadId) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-neutral-500">Initializing...</p>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-screen">
        <NetworkErrorBanner
          isVisible={networkError}
          onRetry={() => {
            setNetworkError(false);
            window.location.reload();
          }}
        />

        <GlobalHeader
          breadcrumbs={[
            { label: 'Chat' },
          ]}
          showNav={true}
        />

        <div className="flex-1 min-h-0 overflow-hidden">
          <ResponsiveLayout
            leftSidebar={
              <ConversationsSidebar
                projects={projects}
                threads={threads}
                selectedThreadId={threadId}
                streamingTitleThreadId={streamingTitleThreadId}
                isLoading={isLoadingThreads}
                onSelect={(id) => setThreadId(id)}
                onCreate={handleCreateThread}
                onRename={handleRenameThread}
                onDelete={handleDeleteThread}
                onArchive={handleArchiveThread}
                searchTerm={searchTerm}
                onSearchChange={setSearchTerm}
                showArchived={showArchived}
                onToggleArchived={() => setShowArchived(prev => !prev)}
              />
            }
            rightSidebar={
              <ReasoningCompanion
                threadId={threadId}
                caseId={caseId}
                companionState={companionState}
                onViewCase={handleViewCase}
                onViewInquiries={handleViewInquiries}
                onReceiptClick={handleReceiptClick}
                onDismissCompleted={handleDismissCompleted}
              />
            }
            showLeftSidebar={showConversations}
            showRightSidebar={showStructure}
          >
            <div className="flex flex-col h-full">
              {/* Mode Header - shows current context */}
              {mode.mode !== 'casual' && (
                <ChatModeHeader
                  mode={mode}
                  threadTitle={threads.find(t => t.id === threadId)?.title}
                  onExitFocus={exitFocus}
                  onExitCase={exitCase}
                  onViewCase={handleViewCase}
                />
              )}

              <ChatInterface
                threadId={threadId}
                onToggleLeft={() => setShowConversations(prev => !prev)}
                onToggleRight={() => setShowStructure(prev => !prev)}
                leftCollapsed={!showConversations}
                rightCollapsed={!showStructure}
                projects={projects}
                projectId={threadProjectId}
                onProjectChange={handleChangeThreadProject}
                unifiedStreamCallbacks={unifiedStreamCallbacks}
                inlineCards={inlineCards}
                inlineCardActions={inlineCardActions}
              />
            </div>
          </ResponsiveLayout>
        </div>
      </div>
    </ErrorBoundary>
  );
}
