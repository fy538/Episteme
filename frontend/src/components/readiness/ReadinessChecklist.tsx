/**
 * ReadinessChecklist - Smart checklist for decision readiness
 *
 * Shows what the user needs to complete before deciding with confidence.
 * Supports AI generation, manual editing, and auto-completion.
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ChecklistItem } from './ChecklistItem';
import { ParentChecklistItem } from './ParentChecklistItem';

export interface ReadinessChecklistItemData {
  id: string;
  description: string;
  is_required: boolean;
  is_complete: boolean;
  completed_at: string | null;
  why_important: string;
  created_by_ai: boolean;
  completion_note: string;
  linked_inquiry: string | null;
  linked_assumption_signal: string | null;
  order: number;
  // Phase 2: Hierarchical fields
  parent: string | null;
  item_type: 'validation' | 'investigation' | 'analysis' | 'stakeholder' | 'alternative' | 'criteria' | 'custom';
  children: ReadinessChecklistItemData[];
  blocked_by_ids: string[];
  // Timestamps
  created_at: string;
  updated_at: string;
}

export interface ChecklistProgress {
  completed: number;
  required: number;
  required_completed: number;
  total: number;
}

interface ReadinessChecklistProps {
  caseId: string;
  items: ReadinessChecklistItemData[];
  progress: ChecklistProgress;
  onRefresh: () => void;
}

export function ReadinessChecklist({
  caseId,
  items,
  progress,
  onRefresh,
}: ReadinessChecklistProps) {
  const [generating, setGenerating] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [expandedParents, setExpandedParents] = useState<Set<string>>(new Set());

  // Filter for top-level items only (items without a parent)
  const topLevelItems = items.filter(i => !i.parent);

  // Separate by required/recommended at parent level
  const requiredItems = topLevelItems.filter(i => i.is_required);
  const recommendedItems = topLevelItems.filter(i => !i.is_required);

  const allRequiredComplete = progress.required > 0 && progress.required_completed === progress.required;

  async function handleGenerate() {
    setGenerating(true);
    try {
      const response = await fetch(`/api/cases/${caseId}/readiness-checklist/generate/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to generate checklist');
      }

      onRefresh();
    } catch (error) {
      console.error('Failed to generate checklist:', error);
      alert('Failed to generate checklist. Please try again.');
    } finally {
      setGenerating(false);
    }
  }

  async function handleToggleComplete(itemId: string, isComplete: boolean) {
    try {
      const response = await fetch(`/api/cases/${caseId}/readiness-checklist/${itemId}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_complete: !isComplete }),
      });

      if (!response.ok) {
        throw new Error('Failed to toggle item');
      }

      onRefresh();
    } catch (error) {
      console.error('Failed to toggle item:', error);
    }
  }

  async function handleDelete(itemId: string) {
    if (!confirm('Delete this checklist item?')) {
      return;
    }

    try {
      const response = await fetch(`/api/cases/${caseId}/readiness-checklist/${itemId}/`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete item');
      }

      onRefresh();
    } catch (error) {
      console.error('Failed to delete item:', error);
    }
  }

  function toggleExpanded(itemId: string) {
    const next = new Set(expandedItems);
    if (next.has(itemId)) {
      next.delete(itemId);
    } else {
      next.add(itemId);
    }
    setExpandedItems(next);
  }

  function toggleParentExpanded(itemId: string) {
    const next = new Set(expandedParents);
    if (next.has(itemId)) {
      next.delete(itemId);
    } else {
      next.add(itemId);
    }
    setExpandedParents(next);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            Decision Readiness
          </h3>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            {allRequiredComplete ? (
              <span className="text-green-600 dark:text-green-400 font-medium">
                ✓ All critical items complete
              </span>
            ) : (
              <>
                {progress.required_completed}/{progress.required} critical items complete
                {progress.required - progress.required_completed > 0 && (
                  <span className="text-neutral-500 ml-1">
                    · {progress.required - progress.required_completed} remaining
                  </span>
                )}
              </>
            )}
          </p>
        </div>

        {items.length === 0 && (
          <Button onClick={handleGenerate} disabled={generating}>
            {generating ? 'Generating...' : '✨ Generate Checklist'}
          </Button>
        )}

        {items.length > 0 && (
          <Button onClick={handleGenerate} disabled={generating} variant="outline" size="sm">
            {generating ? 'Adding items...' : '+ Add AI suggestions'}
          </Button>
        )}
      </div>

      {items.length === 0 && !generating && (
        <div className="text-center py-12 bg-neutral-50 dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800">
          <p className="text-neutral-600 dark:text-neutral-400 mb-4">
            No checklist items yet
          </p>
          <p className="text-sm text-neutral-500 dark:text-neutral-500 mb-6">
            Generate a smart checklist based on your case context
          </p>
          <Button onClick={handleGenerate}>
            ✨ Generate Checklist
          </Button>
        </div>
      )}

      {/* Critical Items */}
      {requiredItems.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
            Critical (Must complete)
          </h4>
          <div className="space-y-2">
            {requiredItems.map(item =>
              item.children && item.children.length > 0 ? (
                <ParentChecklistItem
                  key={item.id}
                  item={item}
                  isExpanded={expandedItems.has(item.id)}
                  isParentExpanded={expandedParents.has(item.id)}
                  onToggle={() => handleToggleComplete(item.id, item.is_complete)}
                  onExpand={() => toggleExpanded(item.id)}
                  onToggleParent={() => toggleParentExpanded(item.id)}
                  onDelete={() => handleDelete(item.id)}
                  onToggleChild={handleToggleComplete}
                  onDeleteChild={handleDelete}
                  expandedChildIds={expandedItems}
                  onExpandChild={toggleExpanded}
                />
              ) : (
                <ChecklistItem
                  key={item.id}
                  item={item}
                  isExpanded={expandedItems.has(item.id)}
                  onToggle={() => handleToggleComplete(item.id, item.is_complete)}
                  onExpand={() => toggleExpanded(item.id)}
                  onDelete={() => handleDelete(item.id)}
                />
              )
            )}
          </div>
        </div>
      )}

      {/* Recommended Items */}
      {recommendedItems.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
            Recommended
          </h4>
          <div className="space-y-2">
            {recommendedItems.map(item =>
              item.children && item.children.length > 0 ? (
                <ParentChecklistItem
                  key={item.id}
                  item={item}
                  isExpanded={expandedItems.has(item.id)}
                  isParentExpanded={expandedParents.has(item.id)}
                  onToggle={() => handleToggleComplete(item.id, item.is_complete)}
                  onExpand={() => toggleExpanded(item.id)}
                  onToggleParent={() => toggleParentExpanded(item.id)}
                  onDelete={() => handleDelete(item.id)}
                  onToggleChild={handleToggleComplete}
                  onDeleteChild={handleDelete}
                  expandedChildIds={expandedItems}
                  onExpandChild={toggleExpanded}
                />
              ) : (
                <ChecklistItem
                  key={item.id}
                  item={item}
                  isExpanded={expandedItems.has(item.id)}
                  onToggle={() => handleToggleComplete(item.id, item.is_complete)}
                  onExpand={() => toggleExpanded(item.id)}
                  onDelete={() => handleDelete(item.id)}
                />
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}
