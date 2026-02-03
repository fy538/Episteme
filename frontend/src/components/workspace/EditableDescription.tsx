/**
 * Editable Description Component
 * Click to edit project description inline
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface EditableDescriptionProps {
  description: string;
  onSave: (description: string) => void;
  placeholder?: string;
}

export function EditableDescription({
  description,
  onSave,
  placeholder = 'Click to add description...',
}: EditableDescriptionProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(description);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.select();
    }
  }, [isEditing]);

  const handleSave = () => {
    onSave(value);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setValue(description);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      handleCancel();
    }
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSave();
    }
  };

  if (isEditing) {
    return (
      <div className="space-y-2">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          className="w-full px-3 py-2 text-sm border border-accent-500 rounded-md focus:outline-none focus:ring-2 focus:ring-accent-500 dark:bg-primary-800 dark:border-accent-600 dark:text-primary-50"
        />
        <div className="flex gap-2">
          <Button size="sm" onClick={handleSave}>
            Save
          </Button>
          <Button size="sm" variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <span className="text-xs text-neutral-500 dark:text-neutral-400 self-center ml-2">
            Cmd+Enter to save
          </span>
        </div>
      </div>
    );
  }

  return (
    <button
      onClick={() => setIsEditing(true)}
      className={cn(
        'text-left w-full text-sm py-1 px-2 rounded transition-colors',
        description
          ? 'text-primary-600 dark:text-primary-400 hover:bg-neutral-100 dark:hover:bg-primary-800'
          : 'text-neutral-400 dark:text-neutral-500 italic hover:bg-neutral-100 dark:hover:bg-primary-800'
      )}
    >
      {description || placeholder}
    </button>
  );
}
