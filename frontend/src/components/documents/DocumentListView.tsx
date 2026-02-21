/**
 * DocumentListView
 *
 * Full document management view for the 'document' ViewMode.
 * Shows uploaded source documents with status, inline upload zone,
 * and per-document actions (delete, reprocess).
 */

'use client';

import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { useToast } from '@/components/ui/toast';
import { documentsAPI } from '@/lib/api/documents';
import { DocumentUpload } from './DocumentUpload';
import { DocumentProcessingStream } from './DocumentProcessingStream';
import type { UploadedDocument } from '@/lib/types/document';
import { getDocumentPipelineStatus, type DocumentPipelineStatus } from '@/lib/types/document';

interface DocumentListViewProps {
  caseId: string;
  projectId: string;
  documents: UploadedDocument[];
  onRefresh: () => void;
}

// ─── File type icons ──────────────────────────────────────────────────────

function FileTypeIcon({ fileType }: { fileType: string }) {
  const type = fileType?.toLowerCase() || '';

  if (type === 'pdf') {
    return (
      <div className="h-8 w-8 rounded-md bg-error-50 dark:bg-error-950/30 flex items-center justify-center flex-shrink-0">
        <span className="text-xs font-bold text-error-600 dark:text-error-400 uppercase">PDF</span>
      </div>
    );
  }
  if (type === 'docx' || type === 'doc') {
    return (
      <div className="h-8 w-8 rounded-md bg-info-50 dark:bg-info-950/30 flex items-center justify-center flex-shrink-0">
        <span className="text-xs font-bold text-info-600 dark:text-info-400 uppercase">DOC</span>
      </div>
    );
  }
  if (type === 'txt' || type === 'md') {
    return (
      <div className="h-8 w-8 rounded-md bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center flex-shrink-0">
        <span className="text-xs font-bold text-neutral-500 dark:text-neutral-400 uppercase">{type}</span>
      </div>
    );
  }
  // Text source (pasted)
  return (
    <div className="h-8 w-8 rounded-md bg-accent-50 dark:bg-accent-950/30 flex items-center justify-center flex-shrink-0">
      <svg className="h-4 w-4 text-accent-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
    </div>
  );
}

// ─── Status badge ─────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: DocumentPipelineStatus }) {
  const config: Record<DocumentPipelineStatus, { label: string; className: string }> = {
    pending: {
      label: 'Pending',
      className: 'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400',
    },
    processing: {
      label: 'Processing',
      className: 'bg-info-100 text-info-700 dark:bg-info-950/40 dark:text-info-400 animate-pulse',
    },
    extracting: {
      label: 'Extracting',
      className: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-400 animate-pulse',
    },
    completed: {
      label: 'Indexed',
      className: 'bg-success-100 text-success-700 dark:bg-success-950/40 dark:text-success-400',
    },
    failed: {
      label: 'Failed',
      className: 'bg-error-100 text-error-700 dark:bg-error-950/40 dark:text-error-400',
    },
  };

  const c = config[status];

  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${c.className}`}>
      {c.label}
    </span>
  );
}

// ─── Time formatting ──────────────────────────────────────────────────────

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return date.toLocaleDateString();
}

function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ─── Document card ────────────────────────────────────────────────────────

function DocumentCard({
  doc,
  onDelete,
  onReprocess,
}: {
  doc: UploadedDocument;
  onDelete: (id: string) => void;
  onReprocess: (id: string) => void;
}) {
  const pipelineStatus = getDocumentPipelineStatus(doc);
  const isActive = pipelineStatus === 'processing' || pipelineStatus === 'extracting';

  return (
    <div className="group flex items-start gap-3 p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700 transition-colors bg-white dark:bg-neutral-900">
      <FileTypeIcon fileType={doc.source_type === 'text' ? '' : doc.file_type} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
            {doc.title}
          </h4>
          <StatusBadge status={pipelineStatus} />
        </div>

        <div className="flex items-center gap-2 mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">
          {doc.file_size && (
            <span>{formatBytes(doc.file_size)}</span>
          )}
          {doc.chunk_count > 0 && (
            <>
              <span className="text-neutral-300 dark:text-neutral-600">&middot;</span>
              <span>{doc.chunk_count} chunks</span>
            </>
          )}
          <span className="text-neutral-300 dark:text-neutral-600">&middot;</span>
          <span>{timeAgo(doc.created_at)}</span>
        </div>

        {/* Show active processing stream inline */}
        {isActive && (
          <DocumentProcessingStream documentId={doc.id} />
        )}

        {/* Show error details */}
        {pipelineStatus === 'failed' && doc.extraction_error && (
          <p className="text-xs text-error-500 dark:text-error-400 mt-1 line-clamp-2">
            {doc.extraction_error}
          </p>
        )}
      </div>

      {/* Actions — visible on hover */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {pipelineStatus === 'failed' && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onReprocess(doc.id)}
            title="Retry processing"
            className="h-7 w-7 text-neutral-400 hover:text-info-600 dark:hover:text-info-400 hover:bg-info-50 dark:hover:bg-info-950/30"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
            </svg>
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onDelete(doc.id)}
          title="Delete document"
          className="h-7 w-7 text-neutral-400 hover:text-error-600 dark:hover:text-error-400 hover:bg-error-50 dark:hover:bg-error-950/30"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
          </svg>
        </Button>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────

export function DocumentListView({
  caseId,
  projectId,
  documents,
  onRefresh,
}: DocumentListViewProps) {
  const { addToast } = useToast();
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await documentsAPI.deleteUploadedDocument(deleteTarget);
      addToast({ title: 'Document deleted', variant: 'default' });
      setDeleteTarget(null);
      onRefresh();
    } catch (error) {
      addToast({
        title: 'Delete failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      });
    }
  }, [deleteTarget, addToast, onRefresh]);

  const handleReprocess = useCallback(async (docId: string) => {
    try {
      await documentsAPI.reprocessDocument(docId);
      addToast({ title: 'Reprocessing started', variant: 'default' });
      onRefresh();
    } catch (error) {
      addToast({
        title: 'Reprocess failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      });
    }
  }, [addToast, onRefresh]);

  // Stats
  const indexed = documents.filter(d => getDocumentPipelineStatus(d) === 'completed').length;
  const processing = documents.filter(d => {
    const s = getDocumentPipelineStatus(d);
    return s === 'processing' || s === 'extracting';
  }).length;
  const failed = documents.filter(d => getDocumentPipelineStatus(d) === 'failed').length;

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            Documents
          </h2>
          {documents.length > 0 && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
              {indexed} indexed
              {processing > 0 && ` \u00b7 ${processing} processing`}
              {failed > 0 && ` \u00b7 ${failed} failed`}
            </p>
          )}
        </div>
        <Button
          variant="default"
          size="sm"
          onClick={() => setShowUpload(!showUpload)}
          className="inline-flex items-center gap-1.5"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Upload
        </Button>
      </div>

      {/* Upload zone (collapsible) */}
      {showUpload && (
        <div className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-4 bg-white dark:bg-neutral-900">
          <DocumentUpload
            caseId={caseId}
            projectId={projectId}
            onUploaded={() => {
              onRefresh();
            }}
            onAllComplete={() => {
              onRefresh();
              setShowUpload(false);
            }}
            compact
          />
        </div>
      )}

      {/* Document list */}
      {documents.length === 0 && !showUpload ? (
        <EmptyState
          icon={
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          }
          title="No documents yet"
          description="Upload a PDF, DOCX, or text file to feed the chunking and extraction pipeline."
          action={{
            label: 'Upload Document',
            onClick: () => setShowUpload(true),
          }}
          compact
        />
      ) : (
        <div className="space-y-2">
          {documents.map(doc => (
            <DocumentCard
              key={doc.id}
              doc={doc}
              onDelete={setDeleteTarget}
              onReprocess={handleReprocess}
            />
          ))}
        </div>
      )}

      {/* Delete confirmation */}
      <ConfirmDialog
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Delete Document"
        description="This will permanently delete the document and all its chunks. This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
      />
    </div>
  );
}
