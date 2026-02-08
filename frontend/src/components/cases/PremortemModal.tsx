'use client';

import { useState, useCallback, useEffect } from 'react';
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

        <textarea
          aria-label="Premortem: describe the most likely reason this decision could fail"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g., We underestimated the competitor's response, or the market timing was wrong..."
          className="w-full px-3 py-2 text-sm border border-neutral-200 dark:border-neutral-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-500 focus:border-transparent resize-none bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100"
          rows={4}
          autoFocus
        />

        {error && (
          <p className="text-xs text-red-500" role="alert">{error}</p>
        )}

        <p className="text-xs text-neutral-400 dark:text-neutral-500">
          This helps you identify risks you might be overlooking. Your answer will be shown alongside your brief.
        </p>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200"
          >
            Skip for now
          </button>
          <button
            onClick={handleSave}
            disabled={!text.trim() || isSaving}
            className="px-4 py-2 text-sm bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900 rounded-lg hover:bg-neutral-800 dark:hover:bg-neutral-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
