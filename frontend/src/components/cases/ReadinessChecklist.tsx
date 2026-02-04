/**
 * ReadinessChecklist - User-defined readiness criteria
 *
 * The user defines what "ready to decide" means for them.
 * No computed scores - just checkboxes they control.
 */

'use client';

import { useState, useCallback } from 'react';
import {
  CheckCircleIcon,
  PlusIcon,
  TrashIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';
import { useReadinessChecklist } from '@/hooks/useReadinessChecklist';
import { Button } from '@/components/ui/button';

interface ReadinessChecklistProps {
  caseId: string;
  onReadyClick?: () => void;
  onNotYetClick?: () => void;
  compact?: boolean;
}

export function ReadinessChecklist({
  caseId,
  onReadyClick,
  onNotYetClick,
  compact = false,
}: ReadinessChecklistProps) {
  const {
    items,
    progress,
    isLoading,
    error,
    addItem,
    toggleItem,
    deleteItem,
    initDefaults,
    allRequiredComplete,
  } = useReadinessChecklist({ caseId, autoInitDefaults: false });

  const [newItemText, setNewItemText] = useState('');
  const [isAddingItem, setIsAddingItem] = useState(false);

  const handleAddItem = useCallback(async () => {
    if (!newItemText.trim()) return;

    try {
      await addItem(newItemText.trim(), true);
      setNewItemText('');
      setIsAddingItem(false);
    } catch {
      // Error handled by hook
    }
  }, [newItemText, addItem]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleAddItem();
      } else if (e.key === 'Escape') {
        setIsAddingItem(false);
        setNewItemText('');
      }
    },
    [handleAddItem]
  );

  if (isLoading) {
    return <div className="animate-pulse bg-neutral-100 rounded-lg p-4 h-32" />;
  }

  if (error) {
    return (
      <div className="text-sm text-red-500 p-4">
        {error}
      </div>
    );
  }

  // Empty state - offer to initialize
  if (items.length === 0) {
    return (
      <div className="bg-white border border-neutral-200 rounded-lg p-6 text-center">
        <SparklesIcon className="w-8 h-8 text-neutral-300 mx-auto mb-3" />
        <h3 className="font-medium text-neutral-900 mb-2">Ready to decide?</h3>
        <p className="text-sm text-neutral-500 mb-4">
          Create a checklist of what needs to be true before you can decide.
        </p>
        <Button onClick={initDefaults} variant="outline" size="sm">
          Start with defaults
        </Button>
      </div>
    );
  }

  return (
    <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-neutral-100">
        <h3 className="font-medium text-neutral-900">Ready to decide?</h3>
        <p className="text-sm text-neutral-500 mt-1">
          {progress.requiredCompleted}/{progress.required} required
          {progress.total > progress.required && ` · ${progress.completed}/${progress.total} total`}
        </p>
      </div>

      {/* Checklist items */}
      <div className="divide-y divide-neutral-100">
        {items.map((item) => (
          <ChecklistItemRow
            key={item.id}
            item={item}
            onToggle={() => toggleItem(item.id)}
            onDelete={() => deleteItem(item.id)}
            compact={compact}
          />
        ))}
      </div>

      {/* Add new item */}
      <div className="p-3 border-t border-neutral-100">
        {isAddingItem ? (
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newItemText}
              onChange={(e) => setNewItemText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="What else needs to be true?"
              className="flex-1 px-3 py-1.5 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-500"
              autoFocus
            />
            <Button onClick={handleAddItem} size="sm" disabled={!newItemText.trim()}>
              Add
            </Button>
            <Button
              onClick={() => {
                setIsAddingItem(false);
                setNewItemText('');
              }}
              size="sm"
              variant="ghost"
            >
              Cancel
            </Button>
          </div>
        ) : (
          <button
            onClick={() => setIsAddingItem(true)}
            className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-700"
          >
            <PlusIcon className="w-4 h-4" />
            Add criterion
          </button>
        )}
      </div>

      {/* Ready/Not Yet buttons */}
      {!compact && (
        <div className="p-4 border-t border-neutral-100 bg-neutral-50 flex items-center gap-3">
          <Button
            onClick={onReadyClick}
            className="flex-1"
            disabled={!allRequiredComplete}
          >
            {allRequiredComplete ? "I'm ready to decide" : 'Complete required items'}
          </Button>
          <Button onClick={onNotYetClick} variant="outline" className="flex-1">
            Not yet
          </Button>
        </div>
      )}
    </div>
  );
}

interface ChecklistItemRowProps {
  item: {
    id: string;
    description: string;
    is_required: boolean;
    is_complete: boolean;
  };
  onToggle: () => void;
  onDelete: () => void;
  compact?: boolean;
}

function ChecklistItemRow({ item, onToggle, onDelete, compact }: ChecklistItemRowProps) {
  const [showDelete, setShowDelete] = useState(false);

  return (
    <div
      className="flex items-center gap-3 px-4 py-3 hover:bg-neutral-50 transition-colors"
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
    >
      {/* Checkbox */}
      <button
        onClick={onToggle}
        className={`flex-shrink-0 w-5 h-5 rounded ${
          item.is_complete
            ? 'text-green-500'
            : 'text-neutral-300 hover:text-neutral-400'
        }`}
      >
        {item.is_complete ? (
          <CheckCircleSolidIcon className="w-5 h-5" />
        ) : (
          <div className="w-5 h-5 border-2 border-current rounded" />
        )}
      </button>

      {/* Description */}
      <span
        className={`flex-1 text-sm ${
          item.is_complete ? 'text-neutral-400 line-through' : 'text-neutral-700'
        }`}
      >
        {item.description}
      </span>

      {/* Required badge */}
      {!item.is_required && (
        <span className="text-xs text-neutral-400">(optional)</span>
      )}

      {/* Delete button */}
      {showDelete && !compact && (
        <button
          onClick={onDelete}
          className="p-1 text-neutral-300 hover:text-red-500 transition-colors"
        >
          <TrashIcon className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

/**
 * Compact progress indicator
 */
export function ReadinessProgress({
  caseId,
}: {
  caseId: string;
}) {
  const { progress, isLoading, allRequiredComplete } = useReadinessChecklist({
    caseId,
    autoInitDefaults: false,
  });

  if (isLoading) {
    return <div className="w-20 h-5 bg-neutral-100 rounded animate-pulse" />;
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      <CheckCircleIcon
        className={`w-4 h-4 ${allRequiredComplete ? 'text-green-500' : 'text-neutral-300'}`}
      />
      <span className={allRequiredComplete ? 'text-green-600' : 'text-neutral-600'}>
        {progress.requiredCompleted}/{progress.required}
      </span>
    </div>
  );
}
