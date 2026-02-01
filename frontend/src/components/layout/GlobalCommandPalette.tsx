/**
 * Global Command Palette Provider - Cmd/Ctrl+K from anywhere
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { CommandPalette, type Command } from '@/components/ui/CommandPalette';

interface GlobalCommandPaletteProps {
  children: React.ReactNode;
}

export function GlobalCommandPalette({ children }: GlobalCommandPaletteProps) {
  const [isOpen, setIsOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  // Global keyboard shortcut
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

  // Global navigation commands
  const commands: Command[] = [
    // Navigation
    {
      id: 'nav-chat',
      label: 'Go to Chat',
      category: 'navigation',
      keywords: ['chat', 'conversations', 'messages'],
      action: () => router.push('/chat'),
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      ),
      shortcut: '⌘G C',
    },
    {
      id: 'nav-workspace',
      label: 'Go to Workspace',
      category: 'navigation',
      keywords: ['workspace', 'cases', 'work'],
      action: () => router.push('/chat'),
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      shortcut: '⌘G W',
    },
    {
      id: 'nav-home',
      label: 'Go to Home',
      category: 'navigation',
      keywords: ['home', 'landing'],
      action: () => router.push('/'),
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
    },
    // Actions
    {
      id: 'action-new-case',
      label: 'Create New Case',
      category: 'actions',
      keywords: ['new', 'create', 'case'],
      action: () => {
        // Would trigger case creation modal
        console.log('Create case');
      },
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      ),
      shortcut: '⌘N',
    },
    {
      id: 'action-new-conversation',
      label: 'New Conversation',
      category: 'actions',
      keywords: ['new', 'chat', 'conversation', 'thread'],
      action: () => {
        if (pathname !== '/chat') {
          router.push('/chat');
        }
        // Would trigger new thread creation
      },
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      ),
    },
    // Search
    {
      id: 'search-cases',
      label: 'Search Cases',
      category: 'search',
      keywords: ['search', 'find', 'cases'],
      action: () => {
        // Would trigger case search
        console.log('Search cases');
      },
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      ),
      shortcut: '⌘F',
    },
    {
      id: 'search-conversations',
      label: 'Search Conversations',
      category: 'search',
      keywords: ['search', 'find', 'conversations', 'threads'],
      action: () => {
        router.push('/chat');
        // Focus search input
      },
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      ),
    },
  ];

  return (
    <>
      {children}
      <CommandPalette
        commands={commands}
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
      />
    </>
  );
}
