/**
 * QuickCaseModal - Manual case creation without going through chat analysis
 *
 * Allows users to create a case directly from the project dashboard with
 * just a title, optional decision question, and stakes level.
 * Follows the PremortemModal pattern for modal structure.
 */

'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { casesAPI } from '@/lib/api/cases';
import type { Case } from '@/lib/types/case';

interface QuickCaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (caseData: Case) => void;
  projectId: string;
}

const STAKES_OPTIONS = [
  { value: 'low', label: 'Low', description: 'Easily reversible, low impact' },
  { value: 'medium', label: 'Medium', description: 'Moderate impact, some reversibility' },
  { value: 'high', label: 'High', description: 'Hard to reverse, significant impact' },
] as const;

export function QuickCaseModal({ isOpen, onClose, onCreated, projectId }: QuickCaseModalProps) {
  const [title, setTitle] = useState('');
  const [decisionQuestion, setDecisionQuestion] = useState('');
  const [stakes, setStakes] = useState<'low' | 'medium' | 'high'>('medium');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');
  const titleInputRef = useRef<HTMLInputElement>(null);

  // Focus title input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => titleInputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, onClose]);

  // Reset form on close
  useEffect(() => {
    if (!isOpen) {
      setTitle('');
      setDecisionQuestion('');
      setStakes('medium');
      setError('');
    }
  }, [isOpen]);

  const handleCreate = useCallback(async () => {
    const trimmedTitle = title.trim();
    if (!trimmedTitle) return;

    setIsCreating(true);
    setError('');

    try {
      const result = await casesAPI.createCase(trimmedTitle, projectId, {
        decision_question: decisionQuestion.trim(),
        stakes,
      });
      onCreated(result.case);
      onClose();
    } catch (err) {
      setError('Failed to create case. Please try again.');
    } finally {
      setIsCreating(false);
    }
  }, [title, decisionQuestion, stakes, projectId, onCreated, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="quick-case-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-xl w-full max-w-lg mx-4 p-6 space-y-4">
        {/* Header */}
        <div>
          <h2 id="quick-case-title" className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            Create a New Case
          </h2>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            Start a case directly. You can refine it later with AI analysis.
          </p>
        </div>

        {/* Title */}
        <div>
          <label htmlFor="case-title" className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
            Title <span className="text-error-500">*</span>
          </label>
          <input
            ref={titleInputRef}
            id="case-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && title.trim()) handleCreate();
            }}
            placeholder="e.g., Should we expand into the European market?"
            className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent"
            maxLength={500}
          />
        </div>

        {/* Decision question */}
        <div>
          <label htmlFor="decision-question" className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
            Decision question <span className="text-neutral-400 dark:text-neutral-500 font-normal">(optional)</span>
          </label>
          <Textarea
            id="decision-question"
            value={decisionQuestion}
            onChange={(e) => setDecisionQuestion(e.target.value)}
            placeholder="What are you trying to decide?"
            className="resize-none"
            rows={2}
          />
        </div>

        {/* Stakes */}
        <div>
          <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-2">
            Stakes
          </label>
          <div className="flex gap-2">
            {STAKES_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setStakes(option.value)}
                className={`flex-1 rounded-lg border px-3 py-2 text-left transition-colors ${
                  stakes === option.value
                    ? 'border-accent-400 bg-accent-50 dark:bg-accent-900/20 text-accent-700 dark:text-accent-300'
                    : 'border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400 hover:border-neutral-300 dark:hover:border-neutral-600'
                }`}
              >
                <div className="text-xs font-medium">{option.label}</div>
                <div className="text-[10px] mt-0.5 opacity-70">{option.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <p className="text-xs text-error-500" role="alert">{error}</p>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isCreating}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleCreate}
            disabled={!title.trim() || isCreating}
          >
            {isCreating ? 'Creating...' : 'Create Case'}
          </Button>
        </div>
      </div>
    </div>
  );
}
