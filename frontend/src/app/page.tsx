/**
 * Home page — input-first with rotating suggestions
 *
 * Uses React Query for project/case data loading (automatic caching, dedup).
 * Intelligence data is fetched internally by Home component.
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spinner } from '@/components/ui/spinner';
import { Home } from '@/components/workspace/Home';
import { authAPI } from '@/lib/api/auth';
import { projectsAPI } from '@/lib/api/projects';
import { useProjectsQuery } from '@/hooks/useProjectsQuery';

export default function HomePage() {
  const router = useRouter();
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

  // React Query — replaces manual useState + useEffect + fetch pattern
  const { data: projects = [], isLoading } = useProjectsQuery(authReady);

  // Handle create project
  const handleCreateProject = async () => {
    try {
      const newProject = await projectsAPI.createProject({
        title: 'New Project',
      });
      router.push(`/projects/${newProject.id}`);
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  };

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
      isLoading={isLoading}
      onCreateProject={handleCreateProject}
    />
  );
}
