/**
 * Global Keyboard Shortcuts Hook
 * Centralized keyboard shortcut management
 *
 * Shortcuts:
 *   Cmd+B → Toggle sidebar panel
 *   Cmd+Shift+? → Show keyboard help
 */

'use client';

import { useKeyboardShortcut } from '@/components/ui/keyboard-shortcut';

interface UseGlobalKeyboardOptions {
  onTogglePanel?: () => void;
}

export function useGlobalKeyboardShortcuts(options?: UseGlobalKeyboardOptions) {
  // Toggle sidebar panel
  useKeyboardShortcut(['Cmd', 'B'], () => {
    options?.onTogglePanel?.();
  });

  // Help shortcut
  useKeyboardShortcut(['Cmd', 'Shift', '?'], () => {
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
    keys: ['⌘', 'B'],
    description: 'Toggle sidebar panel',
    category: 'View',
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
    keys: ['⌘', '⇧', '?'],
    description: 'Show keyboard shortcuts',
    category: 'Help',
  },
  {
    keys: ['Esc'],
    description: 'Close modal/cancel',
    category: 'General',
  },
  {
    keys: ['⌘', '/'],
    description: 'Toggle chat panel',
    category: 'Workspace',
  },
  {
    keys: ['⌘', '\\'],
    description: 'Toggle focus mode',
    category: 'Workspace',
  },
];
