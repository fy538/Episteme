/**
 * Brief Page — Full-page focused brief editing experience.
 *
 * Uses UnifiedBriefView in "focused" variant (full-width, no chat panel assumed).
 * Loads case, brief document, and inquiries independently.
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { UnifiedBriefView } from '@/components/workspace/UnifiedBriefView';
import { Spinner } from '@/components/ui/spinner';
import { Button } from '@/components/ui/button';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { casesAPI } from '@/lib/api/cases';
import { documentsAPI } from '@/lib/api/documents';
import { inquiriesAPI } from '@/lib/api/inquiries';
import type { Case, CaseDocument, Inquiry } from '@/lib/types/case';

export default function BriefPage() {
  const router = useRouter();
  const params = useParams();
  const caseId = params.caseId as string;

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [briefDoc, setBriefDoc] = useState<CaseDocument | null>(null);
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Auth is handled by the (app) layout — no per-page auth check needed.
  const loadData = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      if (signal?.aborted) return;

      const c = await casesAPI.getCase(caseId);
      if (signal?.aborted) return;
      setCaseData(c);

      if (!c.main_brief) {
        setError('This case has no brief document yet. Create one from the case overview.');
        setLoading(false);
        return;
      }

      const [doc, inqs] = await Promise.all([
        documentsAPI.getDocument(c.main_brief),
        inquiriesAPI.getByCase(caseId),
      ]);
      if (signal?.aborted) return;
      setBriefDoc(doc);
      setInquiries(inqs);
    } catch (err: any) {
      if (err?.name === 'AbortError' || signal?.aborted) return;
      setError(err.message || 'Failed to load brief');
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, [caseId]);

  useEffect(() => {
    const controller = new AbortController();
    abortControllerRef.current = controller;
    loadData(controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadData]);

  const handleStartInquiry = useCallback(() => {
    router.push(`/cases/${caseId}?tab=inquiry-dashboard`);
  }, [caseId, router]);

  const handleOpenInquiry = useCallback((inquiryId: string) => {
    router.push(`/cases/${caseId}?inquiry=${inquiryId}`);
  }, [caseId, router]);

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-neutral-50 dark:bg-primary-950">
        <div className="flex-1 flex items-center justify-center">
          <Spinner />
        </div>
      </div>
    );
  }

  if (error || !caseData || !briefDoc) {
    return (
      <div className="flex flex-col h-full bg-neutral-50 dark:bg-primary-950">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
              {error || 'Brief document not found'}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/cases/${caseId}`)}
            >
              Back to Case
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-full">
        <UnifiedBriefView
          caseData={caseData}
          brief={briefDoc}
          inquiries={inquiries}
          onStartInquiry={handleStartInquiry}
          onOpenInquiry={handleOpenInquiry}
          onRefresh={() => loadData()}
          variant="focused"
        />
      </div>
    </ErrorBoundary>
  );
}
