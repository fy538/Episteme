/**
 * Keyboard Shortcuts Help Modal
 * Shows all available shortcuts
 */

'use client';

import { useState, useEffect } from 'react';
import { Dialog } from '@/components/ui/dialog';
import { KeyboardShortcutsHelp } from '@/components/ui/keyboard-shortcut';
import { GLOBAL_SHORTCUTS } from '@/hooks/useGlobalKeyboard';

export function KeyboardShortcutsModal() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    function handleShowHelp() {
      setIsOpen(true);
    }

    window.addEventListener('show-keyboard-help' as any, handleShowHelp);
    return () => window.removeEventListener('show-keyboard-help' as any, handleShowHelp);
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
