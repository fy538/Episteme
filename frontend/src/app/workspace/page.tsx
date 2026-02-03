/**
 * Workspace Dashboard - Central hub for all work
 * Project-centric layout with left sidebar and main area
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spinner } from '@/components/ui/spinner';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import { ProjectSidebar } from '@/components/workspace/ProjectSidebar';
import { DashboardOverview } from '@/components/workspace/DashboardOverview';
import { ProjectView } from '@/components/workspace/ProjectView';
import { ResponsiveLayout } from '@/components/layout/ResponsiveLayout';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { NetworkErrorBanner } from '@/components/ui/network-error-banner';
import { NoProjectsEmpty } from '@/components/ui/empty-state';
import { projectsAPI } from '@/lib/api/projects';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { chatAPI } from '@/lib/api/chat';
import { authAPI } from '@/lib/api/auth';
import { useKeyboardShortcut } from '@/components/ui/keyboard-shortcut';
import type { Project } from '@/lib/types/project';
import type { Case, Inquiry } from '@/lib/types/case';
import type { ChatThread } from '@/lib/types/chat';

export default function WorkspaceDashboard() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [cases, setCases] = useState<Case[]>([]);
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [authReady, setAuthReady] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [networkError, setNetworkError] = useState(false);

  // Keyboard shortcuts
  useKeyboardShortcut(['Cmd', 'N'], handleCreateProject);
  useKeyboardShortcut(['Cmd', 'Shift', 'N'], handleCreateCase);

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

  // Load dashboard data
  useEffect(() => {
    async function loadDashboard() {
      if (!authReady) return;

      try {
        // Load projects, cases, inquiries, and threads in parallel
        const [projectsResp, casesResp, threadsResp] = await Promise.all([
          projectsAPI.listProjects(),
          casesAPI.listCases(),
          chatAPI.listThreads(),
        ]);

        setProjects(projectsResp);
        
        // Sort cases by most recent
        const sortedCases = casesResp.sort((a, b) => 
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        );
        setCases(sortedCases);

        // Sort threads by most recent
        const sortedThreads = threadsResp.sort((a, b) => 
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        );
        setThreads(sortedThreads);

        // Load inquiries for active cases
        const allInquiries: Inquiry[] = [];
        for (const c of sortedCases.slice(0, 5)) {
          try {
            const caseInquiries = await inquiriesAPI.getByCase(c.id);
            allInquiries.push(...caseInquiries);
          } catch (err) {
            console.error('Failed to load inquiries for case', c.id);
          }
        }
        setInquiries(allInquiries);
      } catch (error) {
        console.error('Failed to load dashboard:', error);
        setNetworkError(true);
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, [authReady]);

  async function handleCreateProject() {
    setIsCreatingProject(true);
    try {
      const newProject = await projectsAPI.createProject({
        title: 'New Project',
      });
      setProjects([...projects, newProject]);
      setSelectedProjectId(newProject.id);
    } catch (error) {
      console.error('Failed to create project:', error);
    } finally {
      setIsCreatingProject(false);
    }
  }

  async function handleCreateCase() {
    if (!selectedProjectId) return;

    try {
      const result = await casesAPI.createCase('New Case', selectedProjectId);
      router.push(`/workspace/cases/${result.case.id}`);
    } catch (error) {
      console.error('Failed to create case:', error);
    }
  }

  async function handleCreateInquiry() {
    // TODO: Implement inquiry creation modal
    console.log('Create inquiry for project:', selectedProjectId);
    // For now, navigate to inquiries page
    router.push('/workspace/inquiries');
  }

  async function handleStartChat() {
    try {
      const newThread = await chatAPI.createThread(selectedProjectId);
      router.push(`/chat?thread=${newThread.id}`);
    } catch (error) {
      console.error('Failed to create chat thread:', error);
    }
  }

  function handleUploadDocument() {
    // TODO: Implement document upload modal
    console.log('Upload document for project:', selectedProjectId);
    alert('Document upload coming soon!');
  }

  async function handleUpdateProject(data: Partial<Project>) {
    if (!selectedProjectId) return;

    try {
      const updatedProject = await projectsAPI.updateProject(selectedProjectId, data);
      
      // Update projects list
      setProjects(projects.map(p => 
        p.id === selectedProjectId ? { ...p, ...updatedProject } : p
      ));
    } catch (error) {
      console.error('Failed to update project:', error);
    }
  }

  // Filter data for selected project
  const selectedProject = projects.find(p => p.id === selectedProjectId);
  const filteredCases = selectedProjectId
    ? cases.filter(c => c.project === selectedProjectId)
    : cases.slice(0, 10); // Top 10 for overview
  const filteredInquiries = selectedProjectId
    ? inquiries.filter(i => {
        const caseForInquiry = cases.find(c => c.id === i.case);
        return caseForInquiry?.project === selectedProjectId;
      })
    : inquiries.filter(i => i.status === 'open' || i.status === 'investigating').slice(0, 10);
  const filteredThreads = selectedProjectId
    ? threads.filter(t => t.project === selectedProjectId)
    : threads.slice(0, 10); // Top 10 for overview

  if (loading || !authReady) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-screen bg-neutral-50 dark:bg-primary-950">
        <NetworkErrorBanner
          isVisible={networkError}
          onRetry={async () => {
            setNetworkError(false);
            setLoading(true);
            window.location.reload();
          }}
        />

        <GlobalHeader
          breadcrumbs={[
            { label: 'Workspace' },
            ...(selectedProject ? [{ label: selectedProject.title }] : []),
          ]}
          showNav={true}
        />

        <ResponsiveLayout
          leftSidebar={
            <ProjectSidebar
              projects={projects}
              selectedProjectId={selectedProjectId}
              onSelectProject={setSelectedProjectId}
              onCreateProject={handleCreateProject}
              isCreatingProject={isCreatingProject}
            />
          }
        >
          <main className="flex-1 overflow-y-auto p-4 md:p-8">
            {projects.length === 0 && !loading ? (
              <NoProjectsEmpty onCreate={handleCreateProject} />
            ) : selectedProjectId && selectedProject ? (
              <ProjectView
                project={selectedProject}
                cases={filteredCases}
                inquiries={filteredInquiries}
                threads={filteredThreads}
                onCreateCase={handleCreateCase}
                onCreateInquiry={handleCreateInquiry}
                onStartChat={handleStartChat}
                onUploadDocument={handleUploadDocument}
                onUpdateProject={handleUpdateProject}
              />
            ) : (
              <DashboardOverview
                recentCases={filteredCases}
                pendingInquiries={filteredInquiries}
                recentThreads={filteredThreads}
              />
            )}
          </main>
        </ResponsiveLayout>
      </div>
    </ErrorBoundary>
  );
}
