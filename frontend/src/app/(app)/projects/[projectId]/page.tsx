/**
 * Project Home — The Concierge
 *
 * Route: /projects/[projectId]
 *
 * A minimal, opinionated home page that tells you what matters most.
 * Three elements: project title, centered chat launcher, 1-3 smart cards.
 *
 * The page accepts drag-and-drop file uploads anywhere.
 */

'use client';

import { useState, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { MessageInput } from '@/components/chat/MessageInput';
import { ConciergeCard } from '@/components/workspace/project/ConciergeCard';
import { DocumentUpload } from '@/components/documents/DocumentUpload';
import { Spinner } from '@/components/ui/spinner';
import { useConciergeCards } from '@/hooks/useConciergeCards';
import { projectsAPI } from '@/lib/api/projects';
import { chatAPI } from '@/lib/api/chat';
import { cn } from '@/lib/utils';

export default function ProjectHomePage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const queryClient = useQueryClient();

  // ─── Project data ───
  const { data: project, isLoading: isProjectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsAPI.getProject(projectId),
    staleTime: 60_000,
  });

  // ─── Concierge cards ───
  const { cards, isLoading: isCardsLoading } = useConciergeCards(projectId);

  // ─── Chat launcher ───
  const [isSending, setIsSending] = useState(false);

  const handleChatSend = useCallback(
    async (content: string) => {
      if (!content.trim() || isSending) return;
      try {
        setIsSending(true);
        const thread = await chatAPI.createThread(projectId);
        if (typeof window !== 'undefined') {
          sessionStorage.setItem(
            'episteme_initial_message',
            JSON.stringify({ threadId: thread.id, content })
          );
        }
        router.push(`/projects/${projectId}/chat?thread=${thread.id}`);
      } catch (err) {
        console.error('Failed to create thread:', err);
        setIsSending(false);
      }
    },
    [projectId, router, isSending]
  );

  // ─── Drag and drop upload ───
  const [isDragOver, setIsDragOver] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const dragCounter = useRef(0);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current += 1;
    if (e.dataTransfer.types.includes('Files')) {
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current -= 1;
    if (dragCounter.current <= 0) {
      dragCounter.current = 0;
      setIsDragOver(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current = 0;
    setIsDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      setShowUpload(true);
    }
  }, []);

  const handleCardClick = useCallback(
    (card: (typeof cards)[0]) => {
      if (card.href === '#upload') {
        setShowUpload(true);
      } else {
        router.push(card.href);
      }
    },
    [router]
  );

  // ─── Loading state ───
  if (isProjectLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  return (
    <div
      className="relative flex flex-col h-full"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Main content — vertically centered */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        {/* Project title */}
        <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-8 text-center">
          {project?.title || 'Project'}
        </h1>

        {/* Chat launcher */}
        <div className="w-full max-w-lg mb-10">
          <MessageInput
            variant="hero"
            placeholder={`Talk to ${project?.title || 'this project'}...`}
            onSend={handleChatSend}
            disabled={isSending}
          />
        </div>

        {/* Concierge cards */}
        <div className="w-full max-w-2xl">
          {isCardsLoading ? (
            <div className="flex justify-center gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="flex-1 h-24 rounded-lg border border-neutral-200 dark:border-neutral-700 animate-pulse bg-neutral-50 dark:bg-neutral-900"
                />
              ))}
            </div>
          ) : cards.length > 0 ? (
            <div
              className={cn(
                'grid gap-3',
                cards.length === 1 && 'grid-cols-1 max-w-sm mx-auto',
                cards.length === 2 && 'grid-cols-2',
                cards.length >= 3 && 'grid-cols-3'
              )}
            >
              {cards.map((card, idx) => (
                <ConciergeCard
                  key={`${card.type}-${card.caseId || idx}`}
                  card={card}
                  onClick={() => handleCardClick(card)}
                />
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {/* Drag-and-drop overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-accent-50/80 dark:bg-accent-950/80 border-2 border-dashed border-accent-300 dark:border-accent-700 rounded-lg pointer-events-none">
          <div className="text-center">
            <UploadCloudIcon className="w-10 h-10 text-accent-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-accent-700 dark:text-accent-300">
              Drop files to upload
            </p>
          </div>
        </div>
      )}

      {/* Upload modal */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/20 backdrop-blur-[2px]"
            onClick={() => setShowUpload(false)}
          />
          <div className="relative z-10 w-full max-w-lg mx-4 bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-700 shadow-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Upload Documents
              </h3>
              <button
                onClick={() => setShowUpload(false)}
                className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
              >
                <CloseIcon className="w-4 h-4" />
              </button>
            </div>
            <DocumentUpload
              projectId={projectId}
              caseId=""
              onAllComplete={() => {
                queryClient.invalidateQueries({ queryKey: ['project-concierge', projectId] });
                setShowUpload(false);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Icons ──────────────────────────────────────────

function UploadCloudIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
