/**
 * Application-wide constants
 *
 * Centralizes magic numbers and configuration values for:
 * - Timeouts and delays
 * - UI constraints
 */

// ============================================================================
// TIMEOUTS (in milliseconds)
// ============================================================================

export const TIMEOUT = {
  /** Time to first token before showing timeout error */
  TTFT: 30000,
  /** Total stream timeout */
  STREAM_TOTAL: 60000,
  /** Debounce delay for search/input */
  DEBOUNCE: 300,
  /** Auto-save delay for preferences */
  AUTO_SAVE: 1000,
  /** Toast auto-dismiss duration */
  TOAST_DURATION: 5000,
  /** Polling interval for async operations */
  POLL_INTERVAL: 2000,
  /** Loading bar hide delay after completion */
  LOADING_BAR_HIDE: 300,
} as const;

// ============================================================================
// UI CONSTRAINTS
// ============================================================================

export const UI = {
  /** Maximum character count for message input */
  MAX_MESSAGE_LENGTH: 10000,
  /** Maximum items to show in a list before "show more" */
  LIST_PREVIEW_LIMIT: 5,
  /** Pull-to-refresh threshold (pixels) */
  PULL_REFRESH_THRESHOLD: 80,
  /** Swipe action threshold (pixels) */
  SWIPE_THRESHOLD: 100,
  /** Loading bar max progress before completion */
  LOADING_BAR_MAX_PROGRESS: 90,
  /** Loading bar progress interval */
  LOADING_BAR_INTERVAL: 100,
} as const;
