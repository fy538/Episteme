/**
 * Workspace Dashboard
 *
 * Main workspace home with:
 * - Collapsible sidebar (exhaustive navigation)
 * - Main content (focused actions, activity, recent cases)
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Spinner } from '@/components/ui/spinner';
import { Home } from '@/components/workspace/Home';
import { authAPI } from '@/lib/api/auth';
import { projectsAPI } from '@/lib/api/projects';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { useIntelligence } from '@/hooks/useIntelligence';
import { calculateReadinessScore } from '@/lib/utils/intelligence-transforms';
import type { Project } from '@/lib/types/project';
import type { Case, Inquiry } from '@/lib/types/case';

// Extended types for the dashboard
interface CaseWithInquiries extends Case {
  inquiries: Inquiry[];
  readinessScore: number;
  tensionsCount: number;
  blindSpotsCount: number;
}

interface ProjectWithCases extends Project {
  cases: CaseWithInquiries[];
}

export default function WorkspaceDashboard() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [authReady, setAuthReady] = useState(false);
  const [projects, setProjects] = useState<ProjectWithCases[]>([]);
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
    try {
      setLoading(true);
      setNetworkError(false);

      // Load projects and cases in parallel
      const [projectsResp, casesResp] = await Promise.all([
        projectsAPI.listProjects(),
        casesAPI.listCases(),
      ]);

      // For each case, load inquiries and readiness data
      const casesWithData = await Promise.all(
        casesResp.map(async (caseItem) => {
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

      // Group cases by project
      const projectsWithCases: ProjectWithCases[] = projectsResp.map((project) => ({
        ...project,
        cases: casesWithData.filter((c) => c.project === project.id),
      }));

      // Add cases without projects to a "No Project" group (optional)
      const orphanCases = casesWithData.filter((c) => !c.project);
      if (orphanCases.length > 0) {
        projectsWithCases.push({
          id: 'no-project',
          title: 'Ungrouped Cases',
          description: 'Cases not assigned to a project',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          cases: orphanCases,
        });
      }

      setProjects(projectsWithCases);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      setNetworkError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authReady) {
      loadData();
    }
  }, [authReady, loadData]);

  // Handle create project
  const handleCreateProject = async () => {
    try {
      const newProject = await projectsAPI.createProject({
        title: 'New Project',
      });
      // Navigate to the new project page
      router.push(`/workspace/projects/${newProject.id}`);
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  };

  // Get intelligence data for home scope
  const { topAction, activity, continueState } = useIntelligence({ scope: 'home' });

  if (!authReady) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  return (
    <Home
      projects={projects}
      isLoading={loading}
      onCreateProject={handleCreateProject}
      topAction={topAction}
      activity={activity}
      continueState={continueState}
    />
  );
}
