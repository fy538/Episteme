/**
 * CaseWorkspaceProvider
 *
 * Shared context that lifts useCaseWorkspace to the layout level so both
 * the SidebarPanel (drill-down case structure) and the case page can
 * consume the same workspace data without duplicate fetches.
 *
 * When no case is active (activeCaseId is null), the hook runs with null
 * caseId (no API calls) and the context value is null.
 */

'use client';

import { createContext, useContext, type ReactNode } from 'react';
import { useNavigation } from '@/components/navigation/NavigationProvider';
import { useCaseWorkspace } from '@/hooks/useCaseWorkspace';

type CaseWorkspaceState = ReturnType<typeof useCaseWorkspace>;

const CaseWorkspaceContext = createContext<CaseWorkspaceState | null>(null);

export function CaseWorkspaceProvider({ children }: { children: ReactNode }) {
  const { activeCaseId } = useNavigation();
  const workspace = useCaseWorkspace({ caseId: activeCaseId ?? null });

  return (
    <CaseWorkspaceContext.Provider value={activeCaseId ? workspace : null}>
      {children}
    </CaseWorkspaceContext.Provider>
  );
}

/** Returns workspace state or null when no case is active. */
export function useCaseWorkspaceContext(): CaseWorkspaceState | null {
  return useContext(CaseWorkspaceContext);
}

/** Strict version — throws if not inside a CaseWorkspaceProvider with an active case. */
export function useRequiredCaseWorkspace(): CaseWorkspaceState {
  const ctx = useContext(CaseWorkspaceContext);
  if (!ctx) {
    throw new Error('useRequiredCaseWorkspace must be used within a CaseWorkspaceProvider with an active case');
  }
  return ctx;
}
