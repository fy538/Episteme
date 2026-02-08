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
import { ProjectHomePage } from '@/components/workspace/project';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { NetworkErrorBanner } from '@/components/ui/network-error-banner';
import { projectsAPI } from '@/lib/api/projects';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { ScaffoldingChat } from '@/components/workspace/case/ScaffoldingChat';
import type { Project } from '@/lib/types/project';
import type { CaseWithInquiries } from '@/hooks/useProjectsQuery';

export default function ProjectDashboard() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;

  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<Project | null>(null);
  const [cases, setCases] = useState<CaseWithInquiries[]>([]);
  const [networkError, setNetworkError] = useState(false);

  // Load data — auth is handled by the (app) layout
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
          const [inquiries, gaps] = await Promise.all([
            inquiriesAPI.getByCase(caseItem.id).catch(() => []),
            casesAPI.getBlindSpotPrompts(caseItem.id).catch(() => null),
          ]);

          const tensionsCount = gaps?.contradictions?.length || 0;
          const blindSpotsCount = gaps?.prompts?.length || 0;

          return {
            ...caseItem,
            inquiries,
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
    loadData();
  }, [loadData]);

  // Scaffolding modal state
  const [showScaffolding, setShowScaffolding] = useState(false);

  // Handle create case — opens scaffolding chat modal
  const handleCreateCase = () => {
    setShowScaffolding(true);
  };

  // Handle case created from scaffolding
  const handleCaseCreated = (caseId: string) => {
    setShowScaffolding(false);
    router.push(`/cases/${caseId}/overview`);
  };

  // Handle start chat
  const handleStartChat = () => {
    router.push(`/?project=${projectId}`);
  };

  // Handle open settings (to be implemented)
  const handleOpenSettings = () => {
    console.log('Open project settings');
    // TODO: Open settings modal
  };

  // Handle delete (soft delete — archives)
  const handleDelete = async () => {
    await projectsAPI.deleteProject(projectId);
    router.push('/');
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-neutral-500">Project not found</p>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-full bg-neutral-50 dark:bg-primary-950">
        <NetworkErrorBanner
          isVisible={networkError}
          onRetry={loadData}
        />

        {/* ProjectHomePage Component with real data */}
        <main className="flex-1 overflow-y-auto">
          <ProjectHomePage
            project={project}
            cases={cases}
            onCreateCase={handleCreateCase}
            onStartChat={handleStartChat}
            onOpenSettings={handleOpenSettings}
            onDelete={handleDelete}
          />
        </main>

        {/* Scaffolding Chat Modal */}
        {showScaffolding && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="bg-white dark:bg-neutral-900 border border-neutral-200/80 dark:border-neutral-700/80 rounded-lg shadow-lg w-full max-w-2xl mx-4 h-[70vh] overflow-hidden">
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
