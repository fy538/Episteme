/**
 * Confirm Dialog
 *
 * Lightweight confirmation prompt for destructive actions (archive, delete).
 * Built on top of the existing Dialog component.
 */

'use client';

import { useState } from 'react';
import { Dialog, DialogFooter } from './dialog';
import { Button } from './button';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'default';
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
}: ConfirmDialogProps) {
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title={title} size="sm" showClose={false}>
      <p className="text-sm text-neutral-600 dark:text-neutral-400">
        {description}
      </p>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={loading}>
          {cancelLabel}
        </Button>
        <Button
          variant={variant === 'danger' ? 'destructive' : 'default'}
          onClick={handleConfirm}
          disabled={loading}
        >
          {loading ? 'Archiving...' : confirmLabel}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
