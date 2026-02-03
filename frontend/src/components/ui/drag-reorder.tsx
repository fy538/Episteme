/**
 * Drag to Reorder Component
 * Allows reordering lists with smooth animations
 */

'use client';

import { Reorder } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface DragReorderProps<T> {
  items: T[];
  onReorder: (newOrder: T[]) => void;
  renderItem: (item: T, index: number) => React.ReactNode;
  keyExtractor: (item: T) => string;
  className?: string;
}

export function DragReorder<T>({
  items,
  onReorder,
  renderItem,
  keyExtractor,
  className,
}: DragReorderProps<T>) {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    // Fallback to regular list without drag
    return (
      <div className={className}>
        {items.map((item, index) => (
          <div key={keyExtractor(item)}>{renderItem(item, index)}</div>
        ))}
      </div>
    );
  }

  return (
    <Reorder.Group
      axis="y"
      values={items}
      onReorder={onReorder}
      className={className}
    >
      {items.map((item, index) => (
        <Reorder.Item
          key={keyExtractor(item)}
          value={item}
          className="cursor-grab active:cursor-grabbing"
          whileDrag={{
            scale: 1.03,
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.2)',
            zIndex: 50,
          }}
          transition={{
            type: 'spring',
            stiffness: 300,
            damping: 30,
          }}
        >
          {renderItem(item, index)}
        </Reorder.Item>
      ))}
    </Reorder.Group>
  );
}
