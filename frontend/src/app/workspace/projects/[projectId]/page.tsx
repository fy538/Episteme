/**
 * Project Dashboard
 *
 * Project home page with hierarchical case view.
 * Shows project cases with readiness scores and activity.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Spinner } from '@/components/ui/spinner';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import { ProjectHomePage } from '@/components/workspace/project';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { NetworkErrorBanner } from '@/components/ui/network-error-banner';
import { authAPI } from '@/lib/api/auth';
import { projectsAPI } from '@/lib/api/projects';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { calculateReadinessScore } from '@/lib/utils/intelligence-transforms';
import { ScaffoldingChat } from '@/components/workspace/case/ScaffoldingChat';
import type { Project } from '@/lib/types/project';
import type { Case, Inquiry } from '@/lib/types/case';

interface CaseWithInquiries extends Case {
  inquiries: Inquiry[];
  readinessScore: number;
  tensionsCount: number;
  blindSpotsCount: number;
}

export default function ProjectDashboard() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;

  const [loading, setLoading] = useState(true);
  const [authReady, setAuthReady] = useState(false);
  const [project, setProject] = useState<Project | null>(null);
  const [cases, setCases] = useState<CaseWithInquiries[]>([]);
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
    if (!projectId) return;

    try {
      setLoading(true);
      setNetworkError(false);

      // Load project and cases in parallel
      const [projectResp, allCases] = await Promise.all([
        projectsAPI.getProject(projectId),
        casesAPI.listCases(),
      ]);

      setProject(projectResp);

      // Filter cases for this project
      const projectCases = allCases.filter((c) => c.project === projectId);

      // For each case, load inquiries and readiness data
      const casesWithData = await Promise.all(
        projectCases.map(async (caseItem) => {
          const [inquiries, landscape, gaps] = await Promise.all([
            inquiriesAPI.getByCase(caseItem.id).catch(() => []),
            casesAPI.getEvidenceLandscape(caseItem.id).catch(() => null),
            casesAPI.getBlindSpotPrompts(caseItem.id).catch(() => null),
          ]);

          // Calculate readiness score using shared utility
          const tensionsCount = gaps?.contradictions?.length || 0;
          const blindSpotsCount = gaps?.prompts?.length || 0;
          const inquiryStats = landscape?.inquiries || { total: 0, resolved: 0 };
          const readinessScore = calculateReadinessScore(
            inquiryStats,
            undefined, // No checklist data at this level
            tensionsCount,
            blindSpotsCount
          );

          return {
            ...caseItem,
            inquiries,
            readinessScore,
            tensionsCount,
            blindSpotsCount,
          };
        })
      );

      setCases(casesWithData);
    } catch (error) {
      console.error('Failed to load project data:', error);
      setNetworkError(true);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (authReady) {
      loadData();
    }
  }, [authReady, loadData]);

  // Scaffolding modal state
  const [showScaffolding, setShowScaffolding] = useState(false);

  // Handle create case — opens scaffolding chat modal
  const handleCreateCase = () => {
    setShowScaffolding(true);
  };

  // Handle case created from scaffolding
  const handleCaseCreated = (caseId: string) => {
    setShowScaffolding(false);
    router.push(`/workspace/cases/${caseId}/overview`);
  };

  // Handle start chat
  const handleStartChat = () => {
    router.push(`/chat?project=${projectId}`);
  };

  // Handle open settings (to be implemented)
  const handleOpenSettings = () => {
    console.log('Open project settings');
    // TODO: Open settings modal
  };

  if (loading || !authReady) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-neutral-500">Project not found</p>
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
            { label: project.title },
          ]}
          showNav={true}
        />

        {/* ProjectHomePage Component with real data */}
        <main className="flex-1">
          <ProjectHomePage
            project={project}
            cases={cases}
            onCreateCase={handleCreateCase}
            onStartChat={handleStartChat}
            onOpenSettings={handleOpenSettings}
          />
        </main>

        {/* Scaffolding Chat Modal */}
        {showScaffolding && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-2xl shadow-2xl w-full max-w-2xl mx-4 h-[70vh] overflow-hidden">
              <ScaffoldingChat
                projectId={projectId}
                onCaseCreated={handleCaseCreated}
                onCancel={() => setShowScaffolding(false)}
              />
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}
