/**
 * Document Upload Component
 *
 * Drag-and-drop zone for uploading files (PDF, DOCX, TXT, MD) or pasting text.
 * Supports multi-file upload with individual progress tracking.
 * After upload, streams real-time processing progress via SSE.
 */

'use client';

import { useState, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/toast';
import { documentsAPI } from '@/lib/api/documents';
import { DocumentProcessingStream } from './DocumentProcessingStream';
import type { UploadedDocument } from '@/lib/types/document';

const ACCEPTED_TYPES = ['.pdf', '.docx', '.txt', '.md'];
const ACCEPTED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

interface DocumentUploadProps {
  caseId: string;
  projectId: string;
  onUploaded?: (doc: UploadedDocument) => void;
  onAllComplete?: () => void;
  compact?: boolean;
}

interface UploadItem {
  id: string;
  file?: File;
  title: string;
  status: 'queued' | 'uploading' | 'processing' | 'complete' | 'error';
  documentId?: string;
  error?: string;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function validateFile(file: File): string | null {
  if (file.size > MAX_FILE_SIZE) {
    return `File too large (${formatFileSize(file.size)}). Maximum is ${formatFileSize(MAX_FILE_SIZE)}.`;
  }
  const ext = '.' + file.name.split('.').pop()?.toLowerCase();
  if (!ACCEPTED_TYPES.includes(ext) && !ACCEPTED_MIME_TYPES.includes(file.type)) {
    return `Unsupported file type. Accepted: ${ACCEPTED_TYPES.join(', ')}`;
  }
  return null;
}

export function DocumentUpload({
  caseId,
  projectId,
  onUploaded,
  onAllComplete,
  compact = false,
}: DocumentUploadProps) {
  const { addToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [pasteMode, setPasteMode] = useState(false);
  const [pastedText, setPastedText] = useState('');
  const [pasteTitle, setPasteTitle] = useState('');
  const [uploadQueue, setUploadQueue] = useState<UploadItem[]>([]);

  // ─── Drag & Drop ─────────────────────────────────────────────────────────

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.items?.length) {
      setDragActive(true);
    }
  }, []);

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const uploadSingleFile = useCallback(async (item: UploadItem) => {
    if (!item.file) return;

    setUploadQueue(prev =>
      prev.map(q => q.id === item.id ? { ...q, status: 'uploading' as const } : q)
    );

    try {
      const doc = await documentsAPI.upload({
        file: item.file,
        title: item.title,
        project_id: projectId,
        case_id: caseId,
      });

      setUploadQueue(prev =>
        prev.map(q => q.id === item.id
          ? { ...q, status: 'processing' as const, documentId: doc.id }
          : q
        )
      );
      onUploaded?.(doc);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed';
      setUploadQueue(prev =>
        prev.map(q => q.id === item.id
          ? { ...q, status: 'error' as const, error: message }
          : q
        )
      );
    }
  }, [caseId, projectId, onUploaded]);

  const queueFiles = useCallback((files: File[]) => {
    const newItems: UploadItem[] = [];

    for (const file of files) {
      const error = validateFile(file);
      if (error) {
        addToast({ title: file.name, description: error, variant: 'error' });
        continue;
      }

      newItems.push({
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        file,
        title: file.name,
        status: 'queued',
      });
    }

    if (newItems.length > 0) {
      setUploadQueue(prev => [...prev, ...newItems]);
      // Start uploading each item
      for (const item of newItems) {
        uploadSingleFile(item);
      }
    }
  }, [addToast, uploadSingleFile]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      queueFiles(files);
    }
  }, [queueFiles]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      queueFiles(files);
    }
    // Reset input so the same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, [queueFiles]);

  // ─── Paste text ──────────────────────────────────────────────────────────

  const handlePaste = useCallback(async () => {
    if (!pastedText.trim() || !pasteTitle.trim()) {
      addToast({ title: 'Missing fields', description: 'Please provide both title and content', variant: 'warning' });
      return;
    }

    const itemId = `${Date.now()}-paste`;
    setUploadQueue(prev => [...prev, {
      id: itemId,
      title: pasteTitle,
      status: 'uploading' as const,
    }]);

    try {
      const doc = await documentsAPI.create({
        title: pasteTitle,
        source_type: 'text',
        content_text: pastedText,
        project_id: projectId,
        case_id: caseId,
      });

      setUploadQueue(prev =>
        prev.map(q => q.id === itemId
          ? { ...q, status: 'processing' as const, documentId: doc.id }
          : q
        )
      );
      setPastedText('');
      setPasteTitle('');
      setPasteMode(false);
      onUploaded?.(doc);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed';
      setUploadQueue(prev =>
        prev.map(q => q.id === itemId
          ? { ...q, status: 'error' as const, error: message }
          : q
        )
      );
    }
  }, [pastedText, pasteTitle, caseId, projectId, addToast, onUploaded]);

  // ─── Queue management ───────────────────────────────────────────────────

  const handleProcessingComplete = useCallback((itemId: string) => {
    setUploadQueue(prev => {
      const updated = prev.map(q =>
        q.id === itemId ? { ...q, status: 'complete' as const } : q
      );
      // Check if all items are done
      const allDone = updated.every(q => q.status === 'complete' || q.status === 'error');
      if (allDone && onAllComplete) {
        setTimeout(onAllComplete, 500);
      }
      return updated;
    });
  }, [onAllComplete]);

  const dismissItem = useCallback((itemId: string) => {
    setUploadQueue(prev => prev.filter(q => q.id !== itemId));
  }, []);

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="space-y-3">
      {/* Mode toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setPasteMode(false)}
          className={`text-xs px-2.5 py-1 rounded-md transition-colors ${
            !pasteMode
              ? 'bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900'
              : 'text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200'
          }`}
        >
          Upload File
        </button>
        <button
          onClick={() => setPasteMode(true)}
          className={`text-xs px-2.5 py-1 rounded-md transition-colors ${
            pasteMode
              ? 'bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900'
              : 'text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200'
          }`}
        >
          Paste Text
        </button>
      </div>

      {!pasteMode ? (
        /* ─── Drop Zone ──────────────────────────────────────────────── */
        <div
          onDragEnter={handleDragIn}
          onDragLeave={handleDragOut}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`
            relative cursor-pointer rounded-lg border-2 border-dashed transition-all duration-200
            ${compact ? 'p-4' : 'p-8'}
            ${dragActive
              ? 'border-blue-400 bg-blue-50/50 dark:bg-blue-950/20 dark:border-blue-500'
              : 'border-neutral-300 dark:border-neutral-700 hover:border-neutral-400 dark:hover:border-neutral-600 bg-neutral-50/50 dark:bg-neutral-900/50'
            }
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES.join(',')}
            multiple
            onChange={handleFileInput}
            className="hidden"
            aria-label="Select document files"
          />

          <div className="flex flex-col items-center gap-2 text-center">
            <div className={`rounded-full p-2.5 ${
              dragActive
                ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-500'
                : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400'
            }`}>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>

            {dragActive ? (
              <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
                Drop files here
              </p>
            ) : (
              <>
                <p className="text-sm text-neutral-600 dark:text-neutral-300">
                  <span className="font-medium text-neutral-900 dark:text-neutral-100">
                    Click to upload
                  </span>
                  {' '}or drag and drop
                </p>
                <p className="text-xs text-neutral-400 dark:text-neutral-500">
                  PDF, DOCX, TXT, MD up to 10MB
                </p>
              </>
            )}
          </div>
        </div>
      ) : (
        /* ─── Paste Text Mode ──────────────────────────────────────── */
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="doc-title-paste">Title</Label>
            <Input
              id="doc-title-paste"
              type="text"
              value={pasteTitle}
              onChange={(e) => setPasteTitle(e.target.value)}
              placeholder="Document title..."
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="doc-content">Content</Label>
            <Textarea
              id="doc-content"
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder="Paste document content here..."
              rows={compact ? 4 : 6}
            />
          </div>
          <Button
            onClick={handlePaste}
            disabled={!pasteTitle.trim() || !pastedText.trim()}
            size="sm"
            className="w-full"
          >
            Upload Text
          </Button>
        </div>
      )}

      {/* ─── Upload Queue ──────────────────────────────────────────── */}
      {uploadQueue.length > 0 && (
        <div className="space-y-2">
          {uploadQueue.map(item => (
            <div key={item.id}>
              {item.status === 'uploading' && (
                <div className="flex items-center gap-2 p-2 bg-neutral-50 dark:bg-neutral-800/50 rounded-md border border-neutral-200 dark:border-neutral-700">
                  <div className="h-3.5 w-3.5 rounded-full border-2 border-blue-400 border-t-transparent animate-spin flex-shrink-0" />
                  <span className="text-xs text-neutral-600 dark:text-neutral-300 truncate flex-1">
                    Uploading {item.title}...
                  </span>
                </div>
              )}

              {item.status === 'queued' && (
                <div className="flex items-center gap-2 p-2 bg-neutral-50 dark:bg-neutral-800/50 rounded-md border border-neutral-200 dark:border-neutral-700">
                  <div className="h-3.5 w-3.5 rounded-full bg-neutral-300 dark:bg-neutral-600 flex-shrink-0" />
                  <span className="text-xs text-neutral-500 dark:text-neutral-400 truncate flex-1">
                    Queued: {item.title}
                  </span>
                </div>
              )}

              {item.status === 'processing' && item.documentId && (
                <DocumentProcessingStream
                  documentId={item.documentId}
                  onComplete={() => handleProcessingComplete(item.id)}
                />
              )}

              {item.status === 'error' && (
                <div className="flex items-center gap-2 p-2 bg-red-50 dark:bg-red-950/20 rounded-md border border-red-200 dark:border-red-800">
                  <svg className="h-3.5 w-3.5 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  <span className="text-xs text-red-600 dark:text-red-400 truncate flex-1">
                    {item.title}: {item.error}
                  </span>
                  <button
                    onClick={() => dismissItem(item.id)}
                    className="text-xs text-red-500 hover:text-red-700 dark:hover:text-red-300 flex-shrink-0"
                  >
                    Dismiss
                  </button>
                </div>
              )}

              {item.status === 'complete' && (
                <div className="flex items-center gap-2 p-2 bg-green-50 dark:bg-green-950/20 rounded-md border border-green-200 dark:border-green-800">
                  <svg className="h-3.5 w-3.5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-xs text-green-600 dark:text-green-400 truncate flex-1">
                    {item.title}
                  </span>
                  <button
                    onClick={() => dismissItem(item.id)}
                    className="text-xs text-green-500 hover:text-green-700 dark:hover:text-green-300 flex-shrink-0"
                  >
                    Dismiss
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
