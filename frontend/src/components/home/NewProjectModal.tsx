/**
 * NewProjectModal — simple creation dialog for projects.
 *
 * Follows the PremortemModal pattern: centered overlay with blur backdrop,
 * keyboard handling (Escape to close), inline error state.
 */

'use client';

import { useState, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { projectsAPI } from '@/lib/api/projects';
import type { Project } from '@/lib/types/project';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (project: Project) => void;
}

export function NewProjectModal({ isOpen, onClose, onCreated }: NewProjectModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setTitle('');
      setDescription('');
      setError('');
    }
  }, [isOpen]);

  const handleCreate = useCallback(async () => {
    if (!title.trim()) return;
    setIsCreating(true);
    setError('');
    try {
      const project = await projectsAPI.createProject({
        title: title.trim(),
        description: description.trim() || undefined,
      });
      onCreated(project);
    } catch (err) {
      setError('Failed to create project. Please try again.');
    } finally {
      setIsCreating(false);
    }
  }, [title, description, onCreated]);

  // Keyboard: Escape to close, Cmd+Enter to submit
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && title.trim()) {
        e.preventDefault();
        handleCreate();
      }
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, onClose, handleCreate, title]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-project-title"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-neutral-900 rounded-xl shadow-xl w-full max-w-lg mx-4 p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <h2
            id="new-project-title"
            className="text-lg font-semibold text-neutral-900 dark:text-neutral-100"
          >
            New Project
          </h2>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            Create a project to organize related documents and investigations.
          </p>
        </div>

        {/* Title */}
        <div>
          <label
            htmlFor="project-title"
            className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
          >
            Title
          </label>
          <Input
            id="project-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Q3 Market Entry Analysis"
            maxLength={500}
            autoFocus
          />
        </div>

        {/* Description */}
        <div>
          <label
            htmlFor="project-description"
            className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
          >
            Description <span className="text-neutral-400 font-normal">(optional)</span>
          </label>
          <Textarea
            id="project-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief context for this project..."
            rows={3}
            className="resize-none"
          />
        </div>

        {error && (
          <p className="text-xs text-error-500" role="alert">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-3">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleCreate}
            disabled={!title.trim() || isCreating}
            isLoading={isCreating}
          >
            {isCreating ? 'Creating...' : 'Create Project'}
          </Button>
        </div>
      </div>
    </div>
  );
}
