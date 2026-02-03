/**
 * Scroll-linked animation hook
 * Creates parallax and scroll-triggered effects
 */

'use client';

import { useEffect, useState, RefObject } from 'react';
import { useScroll, useTransform, MotionValue } from 'framer-motion';
import { useReducedMotion } from './useReducedMotion';

interface ScrollAnimationConfig {
  ref: RefObject<HTMLElement>;
  offset?: [string, string]; // e.g., ["start end", "end start"]
}

export function useScrollAnimation({ ref, offset }: ScrollAnimationConfig) {
  const prefersReducedMotion = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: offset as any || ['start end', 'end start'],
  });

  if (prefersReducedMotion) {
    return {
      opacity: 1,
      y: 0,
      scale: 1,
      scrollYProgress,
    };
  }

  return {
    scrollYProgress,
    opacity: useTransform(scrollYProgress, [0, 0.2, 0.8, 1], [0, 1, 1, 0]),
    y: useTransform(scrollYProgress, [0, 1], [100, -100]),
    scale: useTransform(scrollYProgress, [0, 0.5, 1], [0.8, 1, 0.8]),
  };
}

// Hook for parallax scrolling effect
export function useParallax(value: MotionValue<number>, distance: number) {
  const prefersReducedMotion = useReducedMotion();
  
  if (prefersReducedMotion) {
    return 0;
  }
  
  return useTransform(value, [0, 1], [-distance, distance]);
}

// Hook for scroll-triggered reveal
export function useScrollReveal(threshold = 0.1) {
  const [isVisible, setIsVisible] = useState(false);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (prefersReducedMotion) {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { threshold }
    );

    const element = document.querySelector('[data-scroll-reveal]');
    if (element) {
      observer.observe(element);
    }

    return () => {
      if (element) {
        observer.unobserve(element);
      }
    };
  }, [threshold, prefersReducedMotion]);

  return isVisible;
}
