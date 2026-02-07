/**
 * Brief Editor Page
 *
 * Full-page markdown editor for the case brief document.
 * Loads the case's main_brief CaseDocument and renders
 * the BriefEditor with auto-save, citation autocomplete,
 * and floating action menu.
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import dynamic from 'next/dynamic';

const BriefEditor = dynamic(
  () => import('@/components/editor/BriefEditor').then(mod => mod.BriefEditor),
  { ssr: false, loading: () => <div className="p-8 text-neutral-400 animate-pulse">Loading editor...</div> }
);
import { Spinner } from '@/components/ui/spinner';
import { Button } from '@/components/ui/button';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { casesAPI } from '@/lib/api/cases';
import { documentsAPI } from '@/lib/api/documents';
import { authAPI } from '@/lib/api/auth';
import type { Case, CaseDocument } from '@/lib/types/case';

export default function BriefEditorPage() {
  const router = useRouter();
  const params = useParams();
  const caseId = params.caseId as string;

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [briefDoc, setBriefDoc] = useState<CaseDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const loadData = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      // Ensure auth
      const isDevMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
      if (!isDevMode) {
        const ok = await authAPI.ensureAuthenticated();
        if (!ok) {
          router.push('/login');
          return;
        }
      }

      if (signal?.aborted) return;

      // Load case
      const c = await casesAPI.getCase(caseId);
      if (signal?.aborted) return;
      setCaseData(c);

      // Load main brief document
      if (!c.main_brief) {
        setError('This case has no brief document yet. Create one from the case overview.');
        setLoading(false);
        return;
      }

      const doc = await documentsAPI.getDocument(c.main_brief);
      if (signal?.aborted) return;
      setBriefDoc(doc);
    } catch (err: any) {
      // Ignore abort errors (component unmounted)
      if (err?.name === 'AbortError' || signal?.aborted) return;
      setError(err.message || 'Failed to load brief');
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, [caseId, router]);

  useEffect(() => {
    const controller = new AbortController();
    abortControllerRef.current = controller;
    loadData(controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadData]);

  // ── Handlers ────────────────────────────────────────────────

  const handleSave = useCallback(async (content: string) => {
    if (!briefDoc) return;
    try {
      await documentsAPI.updateDocument(briefDoc.id, content);
    } catch (err: any) {
      console.error('Failed to save brief:', err);
    }
  }, [briefDoc]);

  const handleCreateInquiry = useCallback((selectedText: string) => {
    // Navigate to case overview with inquiry creation context
    router.push(`/cases/${caseId}/overview?createInquiry=${encodeURIComponent(selectedText)}`);
  }, [caseId, router]);

  const handleMarkAssumption = useCallback((selectedText: string) => {
    // TODO: Create a signal of type 'Assumption' from the selected text
    console.log('Mark assumption:', selectedText);
  }, []);

  // ── Loading ──────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen bg-neutral-50 dark:bg-primary-950">
        <GlobalHeader
          breadcrumbs={[
            { label: 'Cases', href: '/cases' },
            { label: '...' },
            { label: 'Brief' },
          ]}
          showNav={true}
        />
        <div className="flex-1 flex items-center justify-center">
          <Spinner />
        </div>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────

  if (error || !briefDoc) {
    return (
      <div className="flex flex-col min-h-screen bg-neutral-50 dark:bg-primary-950">
        <GlobalHeader
          breadcrumbs={[
            { label: 'Cases', href: '/cases' },
            { label: caseData?.title || 'Case', href: `/cases/${caseId}/overview` },
            { label: 'Brief' },
          ]}
          showNav={true}
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
              {error || 'Brief document not found'}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/cases/${caseId}/overview`)}
            >
              Back to Case Overview
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // ── Main Render ──────────────────────────────────────────────

  return (
    <ErrorBoundary>
    <div className="flex flex-col min-h-screen bg-white dark:bg-primary-950">
      <GlobalHeader
        breadcrumbs={[
          { label: 'Cases', href: '/cases' },
          { label: caseData?.title || 'Case', href: `/cases/${caseId}/overview` },
          { label: 'Edit Brief' },
        ]}
        showNav={true}
      />

      {/* Editor header with back button */}
      <div className="border-b border-neutral-200 dark:border-neutral-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => router.push(`/cases/${caseId}/overview`)}
          >
            <BackIcon className="w-3.5 h-3.5 mr-1" />
            Back to Brief
          </Button>
          <span className="text-xs text-neutral-400 dark:text-neutral-500">
            Editing: {briefDoc.title}
          </span>
        </div>
      </div>

      {/* Editor */}
      <main className="flex-1 max-w-4xl mx-auto w-full">
        <BriefEditor
          document={briefDoc}
          onSave={handleSave}
          onCreateInquiry={handleCreateInquiry}
          onMarkAssumption={handleMarkAssumption}
        />
      </main>
    </div>
    </ErrorBoundary>
  );
}

// ── Icons ────────────────────────────────────────────────────────

function BackIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
