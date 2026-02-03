/**
 * Project Dashboard Page
 * 
 * Shows overview of a project with its cases, documents, and recent activity
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import { projectsAPI } from '@/lib/api/projects';
import { casesAPI } from '@/lib/api/cases';
import { authAPI } from '@/lib/api/auth';
import type { Project } from '@/lib/types/project';
import type { Case } from '@/lib/types/case';

export default function ProjectDashboardPage({
  params,
}: {
  params: { projectId: string };
}) {
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
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

  // Load project data
  useEffect(() => {
    async function loadProject() {
      if (!authReady) return;

      try {
        const [projectData, casesData] = await Promise.all([
          projectsAPI.getProject(params.projectId),
          casesAPI.listCases(), // Will need to filter by project
        ]);

        setProject(projectData);
        
        // Filter cases by this project
        const projectCases = casesData.filter(c => c.project === params.projectId);
        setCases(projectCases);
      } catch (error) {
        console.error('Failed to load project:', error);
      } finally {
        setLoading(false);
      }
    }

    loadProject();
  }, [authReady, params.projectId]);

  async function handleCreateCase() {
    if (!project) return;
    
    try {
      const result = await casesAPI.createCase('New Case', project.id);
      
      router.push(`/workspace/cases/${result.case.id}`);
    } catch (error) {
      console.error('Failed to create case:', error);
    }
  }

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
        <div className="text-center">
          <p className="text-neutral-500 mb-4">Project not found</p>
          <Button onClick={() => router.push('/workspace')}>
            Back to Workspace
          </Button>
        </div>
      </div>
    );
  }

  const activeCases = cases.filter(c => c.status === 'active');
  const draftCases = cases.filter(c => c.status === 'draft');
  const archivedCases = cases.filter(c => c.status === 'archived');

  return (
    <div className="flex flex-col h-screen bg-neutral-50">
      <GlobalHeader
        breadcrumbs={[
          { label: 'Workspace', href: '/workspace' },
          { label: project.title },
        ]}
        showNav={true}
      />

      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Project Header */}
          <div>
            <h1 className="text-3xl tracking-tight font-bold text-primary-900 mb-2">
              {project.title}
            </h1>
            {project.description && (
              <p className="text-primary-600">
                {project.description}
              </p>
            )}
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-neutral-600">Total Cases</p>
                    <p className="text-3xl tracking-tight font-bold text-primary-900 mt-1">
                      {cases.length}
                    </p>
                  </div>
                  <svg className="w-10 h-10 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-neutral-600">Active</p>
                    <p className="text-3xl tracking-tight font-bold text-accent-600 mt-1">
                      {activeCases.length}
                    </p>
                  </div>
                  <svg className="w-10 h-10 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-neutral-600">Draft</p>
                    <p className="text-3xl tracking-tight font-bold text-warning-600 mt-1">
                      {draftCases.length}
                    </p>
                  </div>
                  <svg className="w-10 h-10 text-warning-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-neutral-600">Documents</p>
                    <p className="text-3xl tracking-tight font-bold text-neutral-900 mt-1">
                      {project.total_documents || 0}
                    </p>
                  </div>
                  <svg className="w-10 h-10 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Cases List */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Active Cases */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Active Cases</CardTitle>
                  <Button onClick={handleCreateCase}>
                    + New Case
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {activeCases.length === 0 ? (
                  <div className="text-center py-8 text-neutral-500">
                    <p>No active cases</p>
                    <Button onClick={handleCreateCase} className="mt-4">
                      Create Your First Case
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {activeCases.map(c => (
                      <Link
                        key={c.id}
                        href={`/workspace/cases/${c.id}`}
                        className="block p-4 rounded-lg border border-neutral-200 hover:border-accent-500 transition-colors group"
                      >
                        <h3 className="font-semibold text-primary-900 group-hover:text-accent-600 transition-colors">
                          {c.title}
                        </h3>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs px-2 py-1 bg-orange-100 text-orange-700 rounded">
                            {c.stakes} stakes
                          </span>
                          {c.confidence != null && (
                            <span className="text-xs text-neutral-600">
                              {Math.round(c.confidence * 100)}% confidence
                            </span>
                          )}
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Draft Cases */}
            <Card>
              <CardHeader>
                <CardTitle>Draft Cases</CardTitle>
              </CardHeader>
              <CardContent>
                {draftCases.length === 0 ? (
                  <div className="text-center py-8 text-neutral-500">
                    <p>No draft cases</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {draftCases.map(c => (
                      <Link
                        key={c.id}
                        href={`/workspace/cases/${c.id}`}
                        className="block p-4 rounded-lg border border-neutral-200 hover:border-accent-500 transition-colors group"
                      >
                        <h3 className="font-semibold text-primary-900 group-hover:text-accent-600 transition-colors">
                          {c.title}
                        </h3>
                        <p className="text-xs text-neutral-500 mt-1">
                          Created {new Date(c.created_at).toLocaleDateString()}
                        </p>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
