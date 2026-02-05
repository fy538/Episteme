/**
 * Keyboard Shortcuts Help Modal
 * Shows all available shortcuts
 */

'use client';

import { useState, useEffect } from 'react';
import { Dialog } from '@/components/ui/dialog';
import { KeyboardShortcutsHelp } from '@/components/ui/keyboard-shortcut';
import { GLOBAL_SHORTCUTS } from '@/hooks/useGlobalKeyboard';

// Custom event name for triggering keyboard help
const SHOW_KEYBOARD_HELP_EVENT = 'show-keyboard-help';

export function KeyboardShortcutsModal() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    function handleShowHelp() {
      setIsOpen(true);
    }

    window.addEventListener(SHOW_KEYBOARD_HELP_EVENT, handleShowHelp);
    return () => window.removeEventListener(SHOW_KEYBOARD_HELP_EVENT, handleShowHelp);
  }, []);

  return (
    <Dialog
      isOpen={isOpen}
      onClose={() => setIsOpen(false)}
      title="Keyboard Shortcuts"
      description="Speed up your workflow with these shortcuts"
      size="lg"
    >
      <KeyboardShortcutsHelp shortcuts={GLOBAL_SHORTCUTS} />
    </Dialog>
  );
}
