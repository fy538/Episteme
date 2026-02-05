/**
 * Companion Theme Configuration
 *
 * Centralized theme for companion sidebar components.
 * Switch between terminal (cyan/amber) and professional (semantic) aesthetics
 * by changing the ACTIVE_THEME constant.
 *
 * Usage:
 *   import { theme } from '@/lib/theme/companionTheme';
 *   <div className={theme.thinking.text}>...</div>
 */

// =============================================================================
// THEME DEFINITIONS
// =============================================================================

/**
 * Terminal aesthetic - cyan/amber/purple hacker-style theme
 */
const terminalTheme = {
  // Mode: Thinking/Reflection
  thinking: {
    text: 'text-cyan-400',
    textMuted: 'text-cyan-600',
    textSubtle: 'text-cyan-700',
    bg: 'bg-cyan-950/10',
    bgHover: 'hover:bg-cyan-950/20',
    border: 'border-cyan-900/30',
    icon: 'text-cyan-500',
  },

  // Mode: Case
  case: {
    text: 'text-amber-400',
    textMuted: 'text-amber-600',
    textSubtle: 'text-amber-700',
    bg: 'bg-amber-950/10',
    bgHover: 'hover:bg-amber-950/20',
    border: 'border-amber-900/30',
    icon: 'text-amber-500',
  },

  // Mode: Inquiry Focus
  inquiry: {
    text: 'text-purple-400',
    textMuted: 'text-purple-600',
    textSubtle: 'text-purple-700',
    bg: 'bg-purple-950/10',
    bgHover: 'hover:bg-purple-950/20',
    border: 'border-purple-900/30',
    icon: 'text-purple-500',
  },

  // Status indicators
  status: {
    running: {
      text: 'text-cyan-400',
      bg: 'bg-cyan-950/20',
      icon: 'text-cyan-500',
    },
    completed: {
      text: 'text-green-400',
      bg: 'bg-green-950/20',
      icon: 'text-green-500',
    },
    error: {
      text: 'text-red-400',
      bg: 'bg-red-950/20',
      icon: 'text-red-500',
    },
  },

  // Session receipt types
  receipts: {
    case_created: { text: 'text-amber-400', icon: 'text-amber-500' },
    signals_extracted: { text: 'text-cyan-400', icon: 'text-cyan-500' },
    inquiry_resolved: { text: 'text-green-400', icon: 'text-green-500' },
    evidence_added: { text: 'text-purple-400', icon: 'text-purple-500' },
    research_completed: { text: 'text-blue-400', icon: 'text-blue-500' },
  },

  // Case state metrics
  metrics: {
    positive: 'text-green-400',
    negative: 'text-red-400',
    neutral: 'text-amber-400',
  },

  // Panel chrome
  panel: {
    bg: 'bg-[#0a0f14]',
    border: 'border-cyan-500/30',
    header: 'text-cyan-400',
    headerBg: 'bg-[#0a0f14]',
  },

  // Typography
  mono: true, // Use monospace font
} as const;

/**
 * Professional aesthetic - uses semantic design tokens
 */
const professionalTheme = {
  // Mode: Thinking/Reflection
  thinking: {
    text: 'text-accent-600 dark:text-accent-400',
    textMuted: 'text-accent-500 dark:text-accent-500',
    textSubtle: 'text-neutral-600 dark:text-neutral-400',
    bg: 'bg-accent-50 dark:bg-accent-950/20',
    bgHover: 'hover:bg-accent-100 dark:hover:bg-accent-950/30',
    border: 'border-accent-200 dark:border-accent-800',
    icon: 'text-accent-500',
  },

  // Mode: Case
  case: {
    text: 'text-warning-600 dark:text-warning-400',
    textMuted: 'text-warning-500 dark:text-warning-500',
    textSubtle: 'text-neutral-600 dark:text-neutral-400',
    bg: 'bg-warning-50 dark:bg-warning-950/20',
    bgHover: 'hover:bg-warning-100 dark:hover:bg-warning-950/30',
    border: 'border-warning-200 dark:border-warning-800',
    icon: 'text-warning-500',
  },

  // Mode: Inquiry Focus
  inquiry: {
    text: 'text-primary-600 dark:text-primary-400',
    textMuted: 'text-primary-500 dark:text-primary-500',
    textSubtle: 'text-neutral-600 dark:text-neutral-400',
    bg: 'bg-primary-50 dark:bg-primary-950/20',
    bgHover: 'hover:bg-primary-100 dark:hover:bg-primary-950/30',
    border: 'border-primary-200 dark:border-primary-800',
    icon: 'text-primary-500',
  },

  // Status indicators
  status: {
    running: {
      text: 'text-info-600 dark:text-info-400',
      bg: 'bg-info-50 dark:bg-info-950/20',
      icon: 'text-info-500',
    },
    completed: {
      text: 'text-success-600 dark:text-success-400',
      bg: 'bg-success-50 dark:bg-success-950/20',
      icon: 'text-success-500',
    },
    error: {
      text: 'text-error-600 dark:text-error-400',
      bg: 'bg-error-50 dark:bg-error-950/20',
      icon: 'text-error-500',
    },
  },

  // Session receipt types
  receipts: {
    case_created: { text: 'text-warning-600 dark:text-warning-400', icon: 'text-warning-500' },
    signals_extracted: { text: 'text-accent-600 dark:text-accent-400', icon: 'text-accent-500' },
    inquiry_resolved: { text: 'text-success-600 dark:text-success-400', icon: 'text-success-500' },
    evidence_added: { text: 'text-primary-600 dark:text-primary-400', icon: 'text-primary-500' },
    research_completed: { text: 'text-info-600 dark:text-info-400', icon: 'text-info-500' },
  },

  // Case state metrics
  metrics: {
    positive: 'text-success-600 dark:text-success-400',
    negative: 'text-error-600 dark:text-error-400',
    neutral: 'text-warning-600 dark:text-warning-400',
  },

  // Panel chrome
  panel: {
    bg: 'bg-neutral-50 dark:bg-neutral-900',
    border: 'border-neutral-200 dark:border-neutral-800',
    header: 'text-neutral-900 dark:text-neutral-100',
    headerBg: 'bg-neutral-50 dark:bg-neutral-900',
  },

  // Typography
  mono: false, // Use default font
} as const;

// =============================================================================
// ACTIVE THEME SELECTION
// =============================================================================

/**
 * Change this to switch between themes:
 * - 'terminal': Cyan/amber hacker aesthetic
 * - 'professional': Semantic design tokens
 */
type ThemeName = 'terminal' | 'professional';
const ACTIVE_THEME: ThemeName = 'terminal';

// =============================================================================
// EXPORTS
// =============================================================================

const themes = {
  terminal: terminalTheme,
  professional: professionalTheme,
} as const;

/** Active theme configuration */
export const theme = themes[ACTIVE_THEME];

/** Theme name for conditional logic */
export const themeName = ACTIVE_THEME;

/** Check if using terminal theme */
export const isTerminalTheme = ACTIVE_THEME === 'terminal';

/** All available themes (for theme switcher UI) */
export const availableThemes = themes;

/** Theme type for TypeScript */
export type CompanionTheme = typeof terminalTheme;
