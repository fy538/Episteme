/**
 * EvidenceIngestModal
 *
 * Unified evidence intake modal with three tabs:
 * 1. Paste Evidence — paste text from external research tools
 * 2. Fetch URL — fetch a web page and extract evidence
 * 3. Upload File — upload a document (reuses DocumentUpload)
 *
 * Triggered by Cmd+Shift+E or "+" button in the case workspace.
 */

'use client';

import { useState, useCallback } from 'react';
import { Dialog, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { useToast } from '@/components/ui/toast';
import { evidenceAPI } from '@/lib/api/evidence';
import { DocumentUpload } from '@/components/documents/DocumentUpload';
import { PasteEvidenceForm } from './PasteEvidenceForm';
import { FetchUrlForm } from './FetchUrlForm';

interface EvidenceIngestModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  projectId: string;
  onIngested?: () => void;
}

export function EvidenceIngestModal({
  isOpen,
  onClose,
  caseId,
  projectId,
  onIngested,
}: EvidenceIngestModalProps) {
  const { addToast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handlePasteSubmit = useCallback(async (data: {
    items: Array<{
      text: string;
      source_url?: string;
      source_title?: string;
    }>;
    source_label?: string;
  }) => {
    setIsSubmitting(true);
    try {
      const result = await evidenceAPI.ingestExternal({
        case_id: caseId,
        items: data.items,
        source_label: data.source_label,
      });

      addToast({
        title: 'Evidence ingested',
        description: `${data.items.length} item${data.items.length !== 1 ? 's' : ''} queued for processing`,
        variant: 'success',
      });
      onIngested?.();
      onClose();
    } catch (error) {
      addToast({
        title: 'Ingestion failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [caseId, addToast, onIngested, onClose]);

  const handleUrlSubmit = useCallback(async (url: string) => {
    setIsSubmitting(true);
    try {
      await evidenceAPI.fetchUrl({
        url,
        case_id: caseId,
      });

      addToast({
        title: 'URL queued',
        description: 'Content will be fetched and evidence extracted automatically',
        variant: 'success',
      });
      onIngested?.();
    } catch (error) {
      addToast({
        title: 'URL fetch failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [caseId, addToast, onIngested]);

  const handleDocumentUploaded = useCallback((documentId: string) => {
    addToast({
      title: 'Document uploaded',
      description: 'Evidence will be extracted automatically',
      variant: 'success',
    });
    onIngested?.();
    onClose();
  }, [addToast, onIngested, onClose]);

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Add Evidence"
      description="Import evidence from external sources into this case"
      size="lg"
    >
      <Tabs defaultValue="paste">
        <TabsList className="w-full mb-4">
          <TabsTrigger value="paste" className="flex-1">
            <span className="flex items-center gap-1.5">
              <ClipboardIcon className="w-3.5 h-3.5" />
              Paste
            </span>
          </TabsTrigger>
          <TabsTrigger value="url" className="flex-1">
            <span className="flex items-center gap-1.5">
              <LinkIcon className="w-3.5 h-3.5" />
              Fetch URL
            </span>
          </TabsTrigger>
          <TabsTrigger value="upload" className="flex-1">
            <span className="flex items-center gap-1.5">
              <UploadIcon className="w-3.5 h-3.5" />
              Upload
            </span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="paste">
          <PasteEvidenceForm
            onSubmit={handlePasteSubmit}
            isSubmitting={isSubmitting}
          />
        </TabsContent>

        <TabsContent value="url">
          <FetchUrlForm
            onSubmit={handleUrlSubmit}
            isSubmitting={isSubmitting}
          />
        </TabsContent>

        <TabsContent value="upload">
          <DocumentUpload
            caseId={caseId}
            projectId={projectId}
            onUploaded={handleDocumentUploaded}
          />
        </TabsContent>
      </Tabs>
    </Dialog>
  );
}

// ─── Icons ────────────────────────────────────────

function ClipboardIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="8" y="2" width="8" height="4" rx="1" ry="1" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LinkIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="17 8 12 3 7 8" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="12" y1="3" x2="12" y2="15" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
