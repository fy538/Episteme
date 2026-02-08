/**
 * NavigationProvider
 *
 * React context that provides unified navigation state to all children.
 * Wraps the app at the layout level, below data providers but above page content.
 */

'use client';

import { createContext, useContext, type ReactNode } from 'react';
import { useNavigationState, type UseNavigationStateReturn } from '@/hooks/useNavigationState';

const NavigationContext = createContext<UseNavigationStateReturn | null>(null);

interface NavigationProviderProps {
  children: ReactNode;
}

export function NavigationProvider({ children }: NavigationProviderProps) {
  const nav = useNavigationState();

  return (
    <NavigationContext.Provider value={nav}>
      {children}
    </NavigationContext.Provider>
  );
}

/**
 * Hook to access navigation state from any component within the app shell.
 * Must be used within a NavigationProvider.
 */
export function useNavigation(): UseNavigationStateReturn {
  const ctx = useContext(NavigationContext);
  if (!ctx) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return ctx;
}
