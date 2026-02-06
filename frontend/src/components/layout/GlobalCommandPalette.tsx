/**
 * Global Command Palette Provider - Cmd/Ctrl+K from anywhere
 *
 * Enhanced with unified semantic search:
 * - Empty state: Recent items + Quick actions
 * - With query: Semantic search across all content
 * - Context-aware grouping (current case vs other cases)
 */

'use client';

import { useState, useEffect } from 'react';
import { usePathname, useParams } from 'next/navigation';
import { SpotlightSearch } from '@/components/search/SpotlightSearch';

interface GlobalCommandPaletteProps {
  children: React.ReactNode;
}

export function GlobalCommandPalette({ children }: GlobalCommandPaletteProps) {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();
  const params = useParams();

  // Extract current case context from URL
  const contextCaseId = typeof params?.caseId === 'string' ? params.caseId : undefined;

  // Global keyboard shortcut (⌘K)
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      {children}
      <SpotlightSearch
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        contextCaseId={contextCaseId}
      />
    </>
  );
}
