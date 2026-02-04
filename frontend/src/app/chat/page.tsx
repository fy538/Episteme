/**
 * Chat page with structure sidebar
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ConversationsSidebar } from '@/components/chat/ConversationsSidebar';
import { CompanionPanel } from '@/components/companion';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import { Button } from '@/components/ui/button';
import { ResponsiveLayout } from '@/components/layout/ResponsiveLayout';
import { NetworkErrorBanner } from '@/components/ui/network-error-banner';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { chatAPI } from '@/lib/api/chat';
import { authAPI } from '@/lib/api/auth';
import type { ChatThread } from '@/lib/types/chat';
import { projectsAPI } from '@/lib/api/projects';
import type { Project } from '@/lib/types/project';
import type { Signal } from '@/lib/types/signal';
import type { CompanionSignal, ActiveAction, SuggestedAction } from '@/lib/types/companion';
import { useOptimisticUpdate } from '@/hooks/useOptimisticUpdate';
import { useKeyboardShortcut } from '@/components/ui/keyboard-shortcut';
import { useIsMobile } from '@/hooks/useResponsive';

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
  const [activeAction, setActiveAction] = useState<ActiveAction | null>(null);

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
    setActiveAction(null);
    setAssistantResponseCount(0);
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
            console.log('[Chat] Auto-generated title:', title);
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
    onMessageComplete: useCallback(() => {
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

  // Companion action handlers
  const handleValidateSignal = useCallback(async (signal: CompanionSignal) => {
    console.log('[Chat] Validate signal:', signal);
    // TODO: Implement single signal validation
    setActiveAction({
      id: `action-${Date.now()}`,
      type: 'research_assumption',
      status: 'running',
      target: signal.text,
      targetIds: [signal.id],
      progress: 0,
      steps: [
        { id: '1', label: 'Searching for evidence...', status: 'running' },
        { id: '2', label: 'Analyzing sources', status: 'pending' },
        { id: '3', label: 'Forming conclusion', status: 'pending' },
      ],
      startedAt: new Date().toISOString(),
    });

    // Simulate progress for demo
    setTimeout(() => {
      setActiveAction(prev => prev ? {
        ...prev,
        progress: 50,
        steps: prev.steps.map((s, i) =>
          i === 0 ? { ...s, status: 'complete' as const } :
          i === 1 ? { ...s, status: 'running' as const } : s
        ),
      } : null);
    }, 1500);

    setTimeout(() => {
      setActiveAction(prev => prev ? {
        ...prev,
        status: 'complete',
        progress: 100,
        steps: prev.steps.map(s => ({ ...s, status: 'complete' as const })),
        result: {
          verdict: 'partial',
          summary: 'This assumption is partially supported. While there is evidence for the general claim, specific conditions may vary.',
          sources: [
            { title: 'Industry Report 2024' },
            { title: 'Stack Overflow Survey' },
          ],
        },
      } : null);
    }, 3000);
  }, []);

  const handleValidateSignals = useCallback(async (signals: CompanionSignal[]) => {
    console.log('[Chat] Validate multiple signals:', signals);
    // TODO: Implement batch validation
    if (signals.length > 0) {
      handleValidateSignal(signals[0]);
    }
  }, [handleValidateSignal]);

  const handleDismissSignal = useCallback(async (signal: CompanionSignal) => {
    console.log('[Chat] Dismiss signal:', signal);
    // TODO: Call API to dismiss signal
    setSignals(prev => prev.filter(s => s.id !== signal.id));
  }, []);

  const handleSuggestionAction = useCallback(async (action: SuggestedAction) => {
    console.log('[Chat] Suggestion action:', action);
    // TODO: Implement action handling based on action.type
    if (action.type === 'validate_assumptions' && action.targetIds) {
      const targetSignals = signals
        .filter(s => action.targetIds?.includes(s.id))
        .map(s => ({
          id: s.id,
          type: s.type,
          text: s.text || s.content || '',
          confidence: s.confidence,
          validationStatus: 'pending' as const,
          createdAt: s.created_at,
        }));
      if (targetSignals.length > 0) {
        handleValidateSignals(targetSignals);
      }
    }
  }, [signals, handleValidateSignals]);

  const handleDismissSuggestion = useCallback((action: SuggestedAction) => {
    console.log('[Chat] Dismiss suggestion:', action);
    // Handled locally in CompanionPanel
  }, []);

  const handleStopAction = useCallback(() => {
    setActiveAction(null);
  }, []);

  const handleDismissActionResult = useCallback(() => {
    setActiveAction(null);
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
              <CompanionPanel
                threadId={threadId}
                caseId={caseId}
                reflection={reflection}
                isReflectionStreaming={isReflectionStreaming}
                signals={signals}
                activeAction={activeAction}
                onStopAction={handleStopAction}
                onDismissActionResult={handleDismissActionResult}
                onValidateSignal={handleValidateSignal}
                onValidateSignals={handleValidateSignals}
                onDismissSignal={handleDismissSignal}
                onSuggestionAction={handleSuggestionAction}
                onDismissSuggestion={handleDismissSuggestion}
              />
            }
            showLeftSidebar={showConversations}
            showRightSidebar={showStructure}
          >
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
            />
          </ResponsiveLayout>
        </div>
      </div>
    </ErrorBoundary>
  );
}
