/**
 * Motion configuration constants
 * Centralized easing curves and animation settings
 */

export const easingCurves = {
  // Natural, accelerating exit (like iOS)
  easeOutExpo: [0.19, 1, 0.22, 1] as const,
  
  // Smooth both ways (default for most UI)
  easeInOutQuart: [0.76, 0, 0.24, 1] as const,
  
  // Snappy, responsive feel (buttons, clicks)
  easeOutQuart: [0.25, 1, 0.5, 1] as const,
  
  // Gentle entrance (modals, toasts)
  easeOutCubic: [0.33, 1, 0.68, 1] as const,
};

export const springConfig = {
  // Bouncy, playful (buttons, micro-interactions)
  bouncy: {
    type: 'spring' as const,
    stiffness: 400,
    damping: 17,
  },
  
  // Smooth, natural (cards, panels)
  smooth: {
    type: 'spring' as const,
    stiffness: 300,
    damping: 30,
  },
  
  // Gentle, slow (page transitions)
  gentle: {
    type: 'spring' as const,
    stiffness: 200,
    damping: 25,
  },
};

export const transitionDurations = {
  fast: 0.15,
  normal: 0.3,
  slow: 0.5,
};
