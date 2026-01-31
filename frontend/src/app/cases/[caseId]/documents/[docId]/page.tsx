/**
 * Document detail page - edit or view based on permissions
 */

'use client';

import { useState, useEffect } from 'react';
import { BriefEditor } from '@/components/editor/BriefEditor';
import { AIDocumentViewer } from '@/components/editor/AIDocumentViewer';
import { documentsAPI } from '@/lib/api/documents';
import type { CaseDocument } from '@/lib/types/case';

export default function DocumentPage({
  params,
}: {
  params: { caseId: string; docId: string };
}) {
  const [document, setDocument] = useState<CaseDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDocument() {
      try {
        setLoading(true);
        const doc = await documentsAPI.getDocument(params.docId);
        setDocument(doc);
      } catch (err) {
        console.error('Failed to load document:', err);
        setError('Failed to load document');
      } finally {
        setLoading(false);
      }
    }
    loadDocument();
  }, [params.docId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-500">Loading document...</p>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-red-600">{error || 'Document not found'}</p>
      </div>
    );
  }

  // Determine which component to render based on edit friction and permissions
  const canEdit = document.edit_friction === 'low' && document.can_edit;

  if (canEdit) {
    return (
      <BriefEditor 
        document={document}
        onSave={(content) => {
          // Update local state
          setDocument(prev => prev ? { ...prev, content_markdown: content } : null);
        }}
      />
    );
  } else {
    return <AIDocumentViewer document={document} />;
  }
}
