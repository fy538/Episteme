/**
 * Chat page with structure sidebar
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ConversationsSidebar } from '@/components/chat/ConversationsSidebar';
import { StructureSidebar } from '@/components/structure/StructureSidebar';
import { chatAPI } from '@/lib/api/chat';
import { authAPI } from '@/lib/api/auth';
import type { ChatThread } from '@/lib/types/chat';

export default function ChatPage() {
  const router = useRouter();
  const [threadId, setThreadId] = useState<string | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);

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
        const list = await chatAPI.listThreads();
        setThreads(list);

        if (list.length === 0) {
          const created = await chatAPI.createThread();
          setThreads([created]);
          setThreadId(created.id);
          setCaseId(created.primary_case || null);
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
  }, [authReady]);

  // Load thread details when selection changes
  useEffect(() => {
    async function loadThread() {
      if (!threadId) return;
      try {
        const thread = await chatAPI.getThread(threadId);
        setCaseId(thread.primary_case || null);
      } catch (err) {
        console.error('Failed to load thread details:', err);
      }
    }
    loadThread();
  }, [threadId]);

  async function handleCreateThread() {
    try {
      const created = await chatAPI.createThread();
      setThreads(prev => [created, ...prev]);
      setThreadId(created.id);
      setCaseId(created.primary_case || null);
    } catch (err) {
      console.error('Failed to create thread:', err);
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

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500">Connecting to backend...</p>
          <p className="text-xs text-gray-400 mt-2">Make sure Django is running on localhost:8000</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center max-w-md">
          <p className="text-red-600 font-semibold mb-2">Connection Error</p>
          <p className="text-sm text-gray-600 mb-4">{error}</p>
          <div className="text-left bg-gray-50 p-4 rounded border border-gray-200">
            <p className="text-xs font-semibold text-gray-700 mb-2">Troubleshooting:</p>
            <ol className="text-xs text-gray-600 space-y-1 list-decimal list-inside">
              <li>Ensure Django is running: <code className="bg-gray-200 px-1">python manage.py runserver</code></li>
              <li>Check backend is on localhost:8000</li>
              <li>Check CORS settings in Django</li>
              <li>Check browser console for details</li>
            </ol>
          </div>
          <button 
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!threadId) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-gray-500">Initializing...</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <ConversationsSidebar
        threads={threads}
        selectedThreadId={threadId}
        isLoading={isLoadingThreads}
        onSelect={(id) => setThreadId(id)}
        onCreate={handleCreateThread}
        onRename={handleRenameThread}
      />
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        <ChatInterface threadId={threadId} />
      </div>
      
      {/* Structure sidebar */}
      <StructureSidebar 
        threadId={threadId} 
        caseId={caseId || undefined}
        onCaseCreated={(newCaseId) => setCaseId(newCaseId)}
      />
    </div>
  );
}
