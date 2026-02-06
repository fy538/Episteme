/**
 * Case Overview Dashboard
 *
 * Shows case overview with inquiries, readiness, and quick actions.
 * Separate from the full case workspace (chat, brief, canvas).
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Spinner } from '@/components/ui/spinner';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import { CaseHomePage } from '@/components/workspace/case';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { NetworkErrorBanner } from '@/components/ui/network-error-banner';
import { authAPI } from '@/lib/api/auth';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { projectsAPI } from '@/lib/api/projects';
import type { Case, Inquiry } from '@/lib/types/case';
import type { Project } from '@/lib/types/project';

export default function CaseOverviewDashboard() {
  const router = useRouter();
  const params = useParams();
  const caseId = params.caseId as string;

  const [loading, setLoading] = useState(true);
  const [authReady, setAuthReady] = useState(false);
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [networkError, setNetworkError] = useState(false);

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

  // Load data
  const loadData = useCallback(async () => {
    if (!caseId) return;

    try {
      setLoading(true);
      setNetworkError(false);

      // Load case and inquiries in parallel
      const [caseResp, inquiriesResp] = await Promise.all([
        casesAPI.getCase(caseId),
        inquiriesAPI.getByCase(caseId),
      ]);

      setCaseData(caseResp);
      setInquiries(inquiriesResp);

      // Load project if case belongs to one
      if (caseResp.project) {
        try {
          const projectResp = await projectsAPI.getProject(caseResp.project);
          setProject(projectResp);
        } catch (e) {
          // Project may not exist or user may not have access
          console.error('Failed to load project:', e);
        }
      }
    } catch (error) {
      console.error('Failed to load case data:', error);
      setNetworkError(true);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    if (authReady) {
      loadData();
    }
  }, [authReady, loadData]);

  // Handle start chat - opens the full case workspace
  const handleStartChat = () => {
    router.push(`/workspace/cases/${caseId}`);
  };

  // Handle open brief
  const handleOpenBrief = () => {
    router.push(`/workspace/cases/${caseId}/brief`);
  };

  // Handle open settings
  const handleOpenSettings = () => {
    console.log('Open case settings');
    // TODO: Open settings modal
  };

  // Handle upload source
  const handleUploadSource = () => {
    console.log('Upload source');
    // TODO: Open upload modal
  };

  // Handle generate research
  const handleGenerateResearch = () => {
    router.push(`/workspace/cases/${caseId}/research`);
  };

  // Handle add inquiry
  const handleAddInquiry = async () => {
    try {
      const newInquiry = await inquiriesAPI.create({
        case: caseId,
        title: 'New Inquiry',
        status: 'open',
      });
      setInquiries([...inquiries, newInquiry]);
    } catch (error) {
      console.error('Failed to create inquiry:', error);
    }
  };

  if (loading || !authReady) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  if (!caseData) {
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
          isVisible={networkError}
          onRetry={loadData}
        />

        <GlobalHeader
          breadcrumbs={[
            { label: 'Workspace', href: '/workspace' },
            ...(project ? [{ label: project.title, href: `/workspace/projects/${project.id}` }] : []),
            { label: caseData.title },
          ]}
          showNav={true}
        />

        {/* CaseHomePage Component with real data */}
        <main className="flex-1">
          <CaseHomePage
            caseData={caseData}
            inquiries={inquiries}
            projectTitle={project?.title}
            onStartChat={handleStartChat}
            onOpenBrief={handleOpenBrief}
            onOpenSettings={handleOpenSettings}
            onUploadSource={handleUploadSource}
            onGenerateResearch={handleGenerateResearch}
            onAddInquiry={handleAddInquiry}
          />
        </main>
      </div>
    </ErrorBoundary>
  );
}
