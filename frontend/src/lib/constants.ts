/**
 * Application-wide constants
 *
 * Centralizes magic numbers and configuration values for:
 * - Animation durations
 * - Timeouts and delays
 * - UI constraints
 * - API settings
 */

// ============================================================================
// ANIMATION DURATIONS (in milliseconds)
// ============================================================================

export const ANIMATION = {
  /** Fast transitions (hover, focus) */
  FAST: 150,
  /** Standard transitions (modals, panels) */
  STANDARD: 200,
  /** Slow transitions (page changes) */
  SLOW: 300,
  /** Loading bar progress duration */
  LOADING_BAR_DURATION: 2000,
  /** Bounce animation delay offsets */
  BOUNCE_DELAY_OFFSET: 0.2,
} as const;

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

// ============================================================================
// API SETTINGS
// ============================================================================

export const API = {
  /** Default page size for paginated lists */
  DEFAULT_PAGE_SIZE: 20,
  /** Maximum retries for failed requests */
  MAX_RETRIES: 3,
  /** Retry delay multiplier (exponential backoff) */
  RETRY_DELAY_MULTIPLIER: 1.5,
  /** Base retry delay */
  RETRY_BASE_DELAY: 1000,
} as const;

// ============================================================================
// Z-INDEX LAYERS
// ============================================================================

export const Z_INDEX = {
  /** Base content */
  CONTENT: 0,
  /** Sticky headers */
  STICKY: 10,
  /** Dropdowns and popovers */
  DROPDOWN: 50,
  /** Modals and dialogs */
  MODAL: 100,
  /** Toasts and notifications */
  TOAST: 150,
  /** Loading indicators */
  LOADING: 200,
} as const;
