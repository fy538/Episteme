/**
 * Chat page with structure sidebar
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ConversationsSidebar } from '@/components/chat/ConversationsSidebar';
import { StructureSidebar } from '@/components/structure/StructureSidebar';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import { Button } from '@/components/ui/button';
import { chatAPI } from '@/lib/api/chat';
import { authAPI } from '@/lib/api/auth';
import type { ChatThread } from '@/lib/types/chat';
import { projectsAPI } from '@/lib/api/projects';
import type { Project } from '@/lib/types/project';

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
    try {
      const created = await chatAPI.createThread(threadProjectId);
      setThreads(prev => [created, ...prev]);
      setThreadId(created.id);
      setCaseId(created.primary_case || null);
      setThreadProjectId(created.project || null);
    } catch (err) {
      console.error('Failed to create thread:', err);
    }
  }

  async function handleDeleteThread(threadIdToDelete: string) {
    try {
      await chatAPI.deleteThread(threadIdToDelete);
      setThreads(prev => {
        const remaining = prev.filter(t => t.id !== threadIdToDelete);
        if (threadId === threadIdToDelete) {
          if (remaining.length > 0) {
            setThreadId(remaining[0].id);
          } else {
            void (async () => {
              const created = await chatAPI.createThread();
              setThreads([created]);
              setThreadId(created.id);
              setCaseId(created.primary_case || null);
            })();
          }
        }
        return remaining;
      });
    } catch (err) {
      console.error('Failed to delete thread:', err);
    }
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

  const filteredThreads = threads.filter(thread =>
    (thread.title || 'New Chat').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex flex-col h-screen">
      <GlobalHeader 
        breadcrumbs={[{ label: 'Chat' }]}
        showNav={true}
      />
      <div className="flex flex-1 overflow-hidden">
        {showConversations && (
          <ConversationsSidebar
            projects={projects}
            threads={filteredThreads}
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
        )}
        {/* Main chat area */}
        <div className="flex-1 flex flex-col">
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
        </div>
        
        {/* Structure sidebar */}
        {showStructure && (
          <StructureSidebar 
            threadId={threadId} 
            caseId={caseId || undefined}
            onCaseCreated={(newCaseId) => {
              setCaseId(newCaseId);
              // Transition to workspace view
              router.push(`/workspace/cases/${newCaseId}`);
            }}
          />
        )}
      </div>
    </div>
  );
}
