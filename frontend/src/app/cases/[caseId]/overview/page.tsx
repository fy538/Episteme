/**
 * Case Overview Dashboard
 *
 * Shows case overview with inquiries, readiness, and quick actions.
 * Uses React Query for data loading (shared cache with workspace page).
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Spinner } from '@/components/ui/spinner';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import { CaseHomePage } from '@/components/workspace/case';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { NetworkErrorBanner } from '@/components/ui/network-error-banner';
import { authAPI } from '@/lib/api/auth';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { useCaseQuery } from '@/hooks/useCaseQuery';

export default function CaseOverviewDashboard() {
  const router = useRouter();
  const params = useParams();
  const caseId = params.caseId as string;

  const [authReady, setAuthReady] = useState(false);

  // Check auth
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

  // React Query — shared cache with case workspace
  const { data, isLoading, isError, refetch } = useCaseQuery(caseId, authReady);

  // Local state for inquiries (needs to be mutable for add)
  const [localInquiries, setLocalInquiries] = useState(data?.inquiries || []);
  useEffect(() => {
    if (data?.inquiries) {
      setLocalInquiries(data.inquiries);
    }
  }, [data?.inquiries]);

  // Handlers
  const handleStartChat = () => router.push(`/cases/${caseId}`);
  const handleOpenBrief = () => router.push(`/cases/${caseId}/brief`);
  const handleOpenSettings = () => console.log('Open case settings'); // TODO: Open settings modal
  const handleUploadSource = () => console.log('Upload source'); // TODO: Open upload modal
  const handleGenerateResearch = () => router.push(`/cases/${caseId}/research`);

  const handleDelete = async () => {
    await casesAPI.deleteCase(caseId);
    // Navigate back to project if available, otherwise home
    if (data?.project) {
      router.push(`/projects/${data.project.id}`);
    } else {
      router.push('/');
    }
  };

  const handleAddInquiry = async () => {
    try {
      const newInquiry = await inquiriesAPI.create({
        case: caseId,
        title: 'New Inquiry',
        status: 'open',
      });
      setLocalInquiries(prev => [...prev, newInquiry]);
    } catch (error) {
      console.error('Failed to create inquiry:', error);
    }
  };

  if (isLoading || !authReady) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  if (!data?.caseData) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-neutral-500">Case not found</p>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="flex flex-col min-h-screen bg-neutral-50 dark:bg-primary-950">
        <NetworkErrorBanner
          isVisible={isError}
          onRetry={() => refetch()}
        />

        <GlobalHeader
          breadcrumbs={[
            { label: 'Home', href: '/' },
            ...(data.project ? [{ label: data.project.title, href: `/projects/${data.project.id}` }] : []),
            { label: data.caseData.title },
          ]}
          showNav={true}
        />

        <main className="flex-1">
          <CaseHomePage
            caseData={data.caseData}
            inquiries={localInquiries}
            projectTitle={data.project?.title}
            onStartChat={handleStartChat}
            onOpenBrief={handleOpenBrief}
            onOpenSettings={handleOpenSettings}
            onUploadSource={handleUploadSource}
            onGenerateResearch={handleGenerateResearch}
            onAddInquiry={handleAddInquiry}
            onDelete={handleDelete}
          />
        </main>
      </div>
    </ErrorBoundary>
  );
}
