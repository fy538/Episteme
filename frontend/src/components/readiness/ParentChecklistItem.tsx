/**
 * ParentChecklistItem - Hierarchical checklist item with children
 */

'use client';

// Inline SVG icons to avoid lucide-react dependency
const ChevronDown = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const ChevronRight = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);
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
          <button
            onClick={onToggleParent}
            className="mt-4 text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 transition-colors"
          >
            {isParentExpanded ? (
              <ChevronDown className="w-5 h-5" />
            ) : (
              <ChevronRight className="w-5 h-5" />
            )}
          </button>
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
