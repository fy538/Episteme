/**
 * Swipeable Item Component
 * Mobile-style swipe to delete/archive
 */

'use client';

import { useState, useRef } from 'react';
import { motion, PanInfo, useMotionValue, useTransform } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface SwipeableItemProps {
  children: React.ReactNode;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  leftAction?: {
    icon: React.ReactNode;
    color: string;
    label: string;
  };
  rightAction?: {
    icon: React.ReactNode;
    color: string;
    label: string;
  };
  threshold?: number; // Distance to trigger action
}

export function SwipeableItem({
  children,
  onSwipeLeft,
  onSwipeRight,
  leftAction,
  rightAction,
  threshold = 100,
}: SwipeableItemProps) {
  const [isDragging, setIsDragging] = useState(false);
  const x = useMotionValue(0);
  const prefersReducedMotion = useReducedMotion();

  const leftActionOpacity = useTransform(x, [-threshold, 0], [1, 0]);
  const rightActionOpacity = useTransform(x, [0, threshold], [0, 1]);

  const handleDragEnd = (_: any, info: PanInfo) => {
    setIsDragging(false);
    
    if (info.offset.x < -threshold && onSwipeLeft) {
      onSwipeLeft();
    } else if (info.offset.x > threshold && onSwipeRight) {
      onSwipeRight();
    }
  };

  if (prefersReducedMotion) {
    return <div>{children}</div>;
  }

  return (
    <div className="relative overflow-hidden">
      {/* Left action (swipe right to reveal) */}
      {leftAction && (
        <motion.div
          className="absolute inset-y-0 left-0 flex items-center justify-start px-4"
          style={{
            backgroundColor: leftAction.color,
            opacity: leftActionOpacity,
          }}
        >
          <div className="flex items-center gap-2 text-white">
            {leftAction.icon}
            <span className="text-sm font-medium">{leftAction.label}</span>
          </div>
        </motion.div>
      )}

      {/* Right action (swipe left to reveal) */}
      {rightAction && (
        <motion.div
          className="absolute inset-y-0 right-0 flex items-center justify-end px-4"
          style={{
            backgroundColor: rightAction.color,
            opacity: rightActionOpacity,
          }}
        >
          <div className="flex items-center gap-2 text-white">
            <span className="text-sm font-medium">{rightAction.label}</span>
            {rightAction.icon}
          </div>
        </motion.div>
      )}

      {/* Swipeable content */}
      <motion.div
        drag="x"
        dragConstraints={{ left: onSwipeLeft ? -200 : 0, right: onSwipeRight ? 200 : 0 }}
        dragElastic={0.2}
        onDragStart={() => setIsDragging(true)}
        onDragEnd={handleDragEnd}
        style={{ x }}
        className={`relative z-10 ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
      >
        {children}
      </motion.div>
    </div>
  );
}
