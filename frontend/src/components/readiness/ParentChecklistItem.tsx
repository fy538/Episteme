/**
 * ParentChecklistItem - Hierarchical checklist item with children
 */

'use client';

import { ChevronDownIcon, ChevronRightIcon } from '@/components/ui/icons';
import { Button } from '@/components/ui/button';
import { ChecklistItem } from './ChecklistItem';
import type { ReadinessChecklistItemData } from './ReadinessChecklist';

interface ParentChecklistItemProps {
  item: ReadinessChecklistItemData;
  isExpanded: boolean;
  isParentExpanded: boolean;
  onToggle: () => void;
  onExpand: () => void;
  onToggleParent: () => void;
  onDelete: () => void;
  onToggleChild: (childId: string, isComplete: boolean) => void;
  onDeleteChild: (childId: string) => void;
  expandedChildIds: Set<string>;
  onExpandChild: (childId: string) => void;
}

export function ParentChecklistItem({
  item,
  isExpanded,
  isParentExpanded,
  onToggle,
  onExpand,
  onToggleParent,
  onDelete,
  onToggleChild,
  onDeleteChild,
  expandedChildIds,
  onExpandChild,
}: ParentChecklistItemProps) {
  const hasChildren = item.children && item.children.length > 0;
  const completedChildren = hasChildren ? item.children.filter(c => c.is_complete).length : 0;
  const totalChildren = item.children?.length || 0;
  const allChildrenComplete = hasChildren && completedChildren === totalChildren;

  return (
    <div>
      {/* Parent item */}
      <div className="flex items-start gap-2">
        {/* Expand/collapse children */}
        {hasChildren && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleParent}
            className="mt-4 h-auto w-auto p-0.5 text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
          >
            {isParentExpanded ? (
              <ChevronDownIcon className="w-5 h-5" />
            ) : (
              <ChevronRightIcon className="w-5 h-5" />
            )}
          </Button>
        )}

        <div className={`flex-1 ${!hasChildren ? 'ml-7' : ''}`}>
          <ChecklistItem
            item={item}
            isExpanded={isExpanded}
            onToggle={onToggle}
            onExpand={onExpand}
            onDelete={onDelete}
            showProgress={hasChildren}
            progressText={hasChildren ? `${completedChildren}/${totalChildren} complete` : undefined}
          />
        </div>
      </div>

      {/* Children items */}
      {hasChildren && isParentExpanded && (
        <div className="ml-14 mt-2 space-y-2 border-l-2 border-neutral-200 dark:border-neutral-800 pl-4">
          {item.children.map(child => (
            <ChecklistItem
              key={child.id}
              item={child}
              isExpanded={expandedChildIds.has(child.id)}
              onToggle={() => onToggleChild(child.id, child.is_complete)}
              onExpand={() => onExpandChild(child.id)}
              onDelete={() => onDeleteChild(child.id)}
              isChild={true}
            />
          ))}
        </div>
      )}
    </div>
  );
}
