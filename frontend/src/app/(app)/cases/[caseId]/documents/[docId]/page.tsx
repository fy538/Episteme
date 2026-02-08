/**
 * Document detail page - edit or view based on permissions
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { BriefEditor } from '@/components/editor/BriefEditor';
import { AIDocumentViewer } from '@/components/editor/AIDocumentViewer';
import { documentsAPI } from '@/lib/api/documents';
import { casesAPI } from '@/lib/api/cases';
import type { CaseDocument, Case } from '@/lib/types/case';

export default function DocumentPage({
  params,
}: {
  params: { caseId: string; docId: string };
}) {
  const router = useRouter();
  const [document, setDocument] = useState<CaseDocument | null>(null);
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDocument() {
      try {
        setLoading(true);
        const [doc, caseResp] = await Promise.all([
          documentsAPI.getDocument(params.docId),
          casesAPI.getCase(params.caseId)
        ]);
        setDocument(doc);
        setCaseData(caseResp);
      } catch (err) {
        console.error('Failed to load document:', err);
        setError('Failed to load document');
      } finally {
        setLoading(false);
      }
    }
    loadDocument();
  }, [params.docId, params.caseId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-neutral-500">Loading document...</p>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-error-600">{error || 'Document not found'}</p>
      </div>
    );
  }

  const breadcrumbItems = [
    { label: 'Home', href: '/' },
    ...(caseData ? [{ label: caseData.title, href: `/cases/${params.caseId}` }] : []),
    { label: document.title }
  ];

  // Determine which component to render based on edit friction and permissions
  const canEdit = document.edit_friction === 'low' && document.can_edit;

  return (
    <div className="h-full flex flex-col">
      {/* Header with breadcrumbs and navigation */}
      <div className="border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-4 py-3">
        <div className="flex items-center justify-between">
          <Breadcrumbs items={breadcrumbItems} />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/cases/${params.caseId}`)}
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Case
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {canEdit ? (
          <BriefEditor 
            document={document}
            onSave={(content) => {
              setDocument(prev => prev ? { ...prev, content_markdown: content } : null);
            }}
          />
        ) : (
          <AIDocumentViewer document={document} />
        )}
      </div>
    </div>
  );
}
