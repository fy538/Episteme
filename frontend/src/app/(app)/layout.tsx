/**
 * Authenticated App Layout
 *
 * Wraps all authenticated routes with the unified navigation shell.
 * Provider stack: NavigationProvider → ProjectWorkspaceProvider →
 * CaseWorkspaceProvider → AppShell → ErrorBoundary → auth gate.
 *
 * The shell renders immediately (zero data deps). Children render only
 * after auth is confirmed — a spinner shows in the content area meanwhile.
 *
 * Routes outside this group (login, demo) don't get the shell.
 */

'use client';

import { NavigationProvider } from '@/components/navigation/NavigationProvider';
import { ProjectWorkspaceProvider } from '@/components/workspace/ProjectWorkspaceProvider';
import { CaseWorkspaceProvider } from '@/components/workspace/CaseWorkspaceProvider';
import { AppShell } from '@/components/navigation/AppShell';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { useAuth } from '@/hooks/useAuth';
import { Spinner } from '@/components/ui/spinner';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isReady } = useAuth();

  return (
    <NavigationProvider>
      <ProjectWorkspaceProvider>
        <CaseWorkspaceProvider>
          <AppShell>
            {isReady ? (
              <ErrorBoundary>{children}</ErrorBoundary>
            ) : (
              <div className="flex h-full items-center justify-center">
                <Spinner size="lg" className="text-accent-600" />
              </div>
            )}
          </AppShell>
        </CaseWorkspaceProvider>
      </ProjectWorkspaceProvider>
    </NavigationProvider>
  );
}
