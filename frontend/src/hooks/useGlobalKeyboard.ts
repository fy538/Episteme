/**
 * Global Keyboard Shortcuts Hook
 * Centralized keyboard shortcut management
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useKeyboardShortcut } from '@/components/ui/keyboard-shortcut';

export function useGlobalKeyboardShortcuts() {
  const router = useRouter();

  // Navigation shortcuts
  useKeyboardShortcut(['Cmd', 'Shift', 'W'], () => {
    router.push('/workspace');
  });

  useKeyboardShortcut(['Cmd', 'Shift', 'C'], () => {
    router.push('/chat');
  });

  useKeyboardShortcut(['Cmd', 'Shift', 'I'], () => {
    router.push('/workspace/inquiries');
  });

  // Help shortcut
  useKeyboardShortcut(['Cmd', 'Shift', '?'], () => {
    // Open keyboard shortcuts help modal
    const event = new CustomEvent('show-keyboard-help');
    window.dispatchEvent(event);
  });
}

// Available shortcuts for display
export const GLOBAL_SHORTCUTS = [
  {
    keys: ['⌘', 'K'],
    description: 'Command palette',
    category: 'Navigation',
  },
  {
    keys: ['⌘', 'P'],
    description: 'Quick switch case',
    category: 'Navigation',
  },
  {
    keys: ['⌘', '⇧', 'W'],
    description: 'Go to workspace',
    category: 'Navigation',
  },
  {
    keys: ['⌘', '⇧', 'C'],
    description: 'Go to chat',
    category: 'Navigation',
  },
  {
    keys: ['⌘', '⇧', 'I'],
    description: 'Go to inquiries',
    category: 'Navigation',
  },
  {
    keys: ['⌘', 'N'],
    description: 'New conversation',
    category: 'Actions',
  },
  {
    keys: ['⌘', 'Enter'],
    description: 'Send message',
    category: 'Chat',
  },
  {
    keys: ['⌘', 'B'],
    description: 'Toggle sidebar',
    category: 'View',
  },
  {
    keys: ['⌘', '⇧', '?'],
    description: 'Show keyboard shortcuts',
    category: 'Help',
  },
  {
    keys: ['Esc'],
    description: 'Close modal/cancel',
    category: 'General',
  },
];
