'use client';

import { useState, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { casesAPI } from '@/lib/api/cases';

interface PremortemModalProps {
  caseId: string;
  isOpen: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

export function PremortemModal({ caseId, isOpen, onClose, onSaved }: PremortemModalProps) {
  const [text, setText] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSave = useCallback(async () => {
    if (!text.trim()) return;
    setIsSaving(true);
    setError('');
    try {
      await casesAPI.savePremortem(caseId, text.trim());
      onSaved?.();
      onClose();
    } catch (err) {
      setError('Failed to save. Please try again.');
    } finally {
      setIsSaving(false);
    }
  }, [caseId, text, onClose, onSaved]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true" aria-labelledby="premortem-title">
      <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-xl w-full max-w-lg mx-4 p-6 space-y-4">
        <div>
          <h2 id="premortem-title" className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            Before you synthesize...
          </h2>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            Imagine this decision failed. What&apos;s the most likely reason?
          </p>
        </div>

        <Textarea
          aria-label="Premortem: describe the most likely reason this decision could fail"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g., We underestimated the competitor's response, or the market timing was wrong..."
          className="resize-none"
          rows={4}
          autoFocus
        />

        {error && (
          <p className="text-xs text-error-500" role="alert">{error}</p>
        )}

        <p className="text-xs text-neutral-400 dark:text-neutral-500">
          This helps you identify risks you might be overlooking. Your answer will be shown alongside your brief.
        </p>

        <div className="flex justify-end gap-3">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Skip for now
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!text.trim() || isSaving}
            isLoading={isSaving}
          >
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>
    </div>
  );
}
