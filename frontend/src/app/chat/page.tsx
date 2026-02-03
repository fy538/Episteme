/**
 * Chat page with structure sidebar
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ConversationsSidebar } from '@/components/chat/ConversationsSidebar';
import { ReasoningCompanion } from '@/components/chat/ReasoningCompanion';
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

  // Keyboard shortcuts
  useKeyboardShortcut(['Cmd', 'N'], handleCreateThread);
  useKeyboardShortcut(['Cmd', 'B'], () => setShowConversations(prev => !prev));

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
        
        {/* Role Clarity Banner - Hide on mobile */}
        <div className="hidden md:block px-6 py-2 bg-accent-50 dark:bg-accent-900/10 border-b border-accent-100 dark:border-accent-800/30">
          <p className="text-sm text-accent-700 dark:text-accent-300 text-center">
            Explore ideas, ask questions, think freely — organize into projects when ready
          </p>
        </div>
        
        <ResponsiveLayout
          leftSidebar={
            <ConversationsSidebar
              projects={projects}
              threads={threads}
              selectedThreadId={threadId}
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
          />
        </ResponsiveLayout>
      </div>
    </ErrorBoundary>
  );
}
