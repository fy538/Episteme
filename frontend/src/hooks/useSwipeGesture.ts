/**
 * Swipe gesture hook
 * Detects swipe gestures for mobile-style interactions
 */

'use client';

import { useRef, useCallback, TouchEvent, MouseEvent } from 'react';

interface SwipeHandlers {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
}

interface SwipeConfig {
  threshold?: number; // Minimum distance for swipe (px)
  velocityThreshold?: number; // Minimum velocity
}

export function useSwipeGesture(
  handlers: SwipeHandlers,
  config: SwipeConfig = {}
) {
  const { threshold = 50, velocityThreshold = 0.3 } = config;
  
  const touchStart = useRef<{ x: number; y: number; time: number } | null>(null);
  const isSwiping = useRef(false);

  const handleStart = useCallback((x: number, y: number) => {
    touchStart.current = { x, y, time: Date.now() };
    isSwiping.current = false;
  }, []);

  const handleMove = useCallback((x: number, y: number) => {
    if (!touchStart.current) return;
    
    const deltaX = Math.abs(x - touchStart.current.x);
    const deltaY = Math.abs(y - touchStart.current.y);
    
    // Determine if this is a swipe gesture
    if (deltaX > 10 || deltaY > 10) {
      isSwiping.current = true;
    }
  }, []);

  const handleEnd = useCallback((x: number, y: number) => {
    if (!touchStart.current || !isSwiping.current) {
      touchStart.current = null;
      return;
    }

    const deltaX = x - touchStart.current.x;
    const deltaY = y - touchStart.current.y;
    const deltaTime = Date.now() - touchStart.current.time;
    
    const velocityX = Math.abs(deltaX) / deltaTime;
    const velocityY = Math.abs(deltaY) / deltaTime;

    // Check horizontal swipe
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      if (Math.abs(deltaX) > threshold && velocityX > velocityThreshold) {
        if (deltaX > 0) {
          handlers.onSwipeRight?.();
        } else {
          handlers.onSwipeLeft?.();
        }
      }
    } 
    // Check vertical swipe
    else {
      if (Math.abs(deltaY) > threshold && velocityY > velocityThreshold) {
        if (deltaY > 0) {
          handlers.onSwipeDown?.();
        } else {
          handlers.onSwipeUp?.();
        }
      }
    }

    touchStart.current = null;
    isSwiping.current = false;
  }, [handlers, threshold, velocityThreshold]);

  // Touch event handlers
  const onTouchStart = useCallback((e: TouchEvent) => {
    const touch = e.touches[0];
    handleStart(touch.clientX, touch.clientY);
  }, [handleStart]);

  const onTouchMove = useCallback((e: TouchEvent) => {
    const touch = e.touches[0];
    handleMove(touch.clientX, touch.clientY);
  }, [handleMove]);

  const onTouchEnd = useCallback((e: TouchEvent) => {
    const touch = e.changedTouches[0];
    handleEnd(touch.clientX, touch.clientY);
  }, [handleEnd]);

  // Mouse event handlers (for testing on desktop)
  const mouseStart = useRef(false);

  const onMouseDown = useCallback((e: MouseEvent) => {
    mouseStart.current = true;
    handleStart(e.clientX, e.clientY);
  }, [handleStart]);

  const onMouseMove = useCallback((e: MouseEvent) => {
    if (!mouseStart.current) return;
    handleMove(e.clientX, e.clientY);
  }, [handleMove]);

  const onMouseUp = useCallback((e: MouseEvent) => {
    if (!mouseStart.current) return;
    mouseStart.current = false;
    handleEnd(e.clientX, e.clientY);
  }, [handleEnd]);

  return {
    // Touch handlers
    onTouchStart,
    onTouchMove,
    onTouchEnd,
    // Mouse handlers (for desktop testing)
    onMouseDown,
    onMouseMove,
    onMouseUp,
  };
}
