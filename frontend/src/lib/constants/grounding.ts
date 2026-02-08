/**
 * Shared grounding, annotation, and section type constants.
 *
 * Single source of truth for status colors, labels, icons, and action configs
 * used across BriefSectionCard, IntelligentBrief, SectionGroundingGutter,
 * SectionContextPanel, and BriefOutlineNav.
 */

import type {
  GroundingStatus,
  AnnotationType,
  AnnotationPriority,
  SectionType,
} from '@/lib/types/case';

// ── Grounding status display ────────────────────────────────────

export const GROUNDING_CONFIG: Record<
  GroundingStatus,
  { color: string; bg: string; dotBg: string; label: string }
> = {
  empty: {
    color: 'text-neutral-400',
    bg: 'bg-neutral-200 dark:bg-neutral-700',
    dotBg: 'bg-neutral-300 dark:bg-neutral-600',
    label: 'No evidence',
  },
  weak: {
    color: 'text-amber-500',
    bg: 'bg-amber-200 dark:bg-amber-900/40',
    dotBg: 'bg-amber-400 dark:bg-amber-500',
    label: 'Under-evidenced',
  },
  moderate: {
    color: 'text-blue-500',
    bg: 'bg-blue-200 dark:bg-blue-900/40',
    dotBg: 'bg-blue-400 dark:bg-blue-500',
    label: 'Some evidence',
  },
  strong: {
    color: 'text-emerald-500',
    bg: 'bg-emerald-200 dark:bg-emerald-900/40',
    dotBg: 'bg-emerald-400 dark:bg-emerald-500',
    label: 'Well-grounded',
  },
  conflicted: {
    color: 'text-red-500',
    bg: 'bg-red-200 dark:bg-red-900/40',
    dotBg: 'bg-red-400 dark:bg-red-500',
    label: 'Has tensions',
  },
};

// Grounding summary labels used in the IntelligentBrief header
export const GROUNDING_SUMMARY: Record<
  GroundingStatus,
  { label: string; color: string }
> = {
  empty: { label: 'No evidence', color: 'text-neutral-400' },
  weak: { label: 'Weak', color: 'text-amber-500' },
  moderate: { label: 'Moderate', color: 'text-blue-500' },
  strong: { label: 'Strong', color: 'text-emerald-500' },
  conflicted: { label: 'Conflicted', color: 'text-red-500' },
};

// ── Annotation type display ─────────────────────────────────────

export const ANNOTATION_CONFIG: Record<
  AnnotationType,
  { icon: string; color: string; label: string }
> = {
  tension: { icon: '\u26A1', color: 'text-red-600 dark:text-red-400', label: 'Tension' },
  blind_spot: { icon: '\uD83D\uDC41\uFE0F', color: 'text-amber-600 dark:text-amber-400', label: 'Blind spot' },
  ungrounded: { icon: '\u26A0\uFE0F', color: 'text-amber-600 dark:text-amber-400', label: 'Unvalidated' },
  evidence_desert: { icon: '\uD83D\uDCED', color: 'text-neutral-500', label: 'Needs evidence' },
  well_grounded: { icon: '\u2705', color: 'text-emerald-600 dark:text-emerald-400', label: 'Strong' },
  stale: { icon: '\u23F0', color: 'text-neutral-500', label: 'Stale' },
  circular: { icon: '\uD83D\uDD04', color: 'text-red-600 dark:text-red-400', label: 'Circular' },
  low_credibility: { icon: '\u2B50', color: 'text-amber-600 dark:text-amber-400', label: 'Low credibility' },
};

// ── Annotation action config ────────────────────────────────────

export type AnnotationActionType = 'resolve_ai' | 'investigate' | 'find_evidence' | 'validate';

export const ANNOTATION_ACTIONS: Record<
  string,
  { label: string; actionType: AnnotationActionType }
> = {
  tension: { label: 'Resolve with AI', actionType: 'resolve_ai' },
  blind_spot: { label: 'Investigate', actionType: 'investigate' },
  evidence_desert: { label: 'Find Evidence', actionType: 'find_evidence' },
  ungrounded: { label: 'Validate', actionType: 'validate' },
  circular: { label: 'Resolve with AI', actionType: 'resolve_ai' },
  stale: { label: 'Refresh Evidence', actionType: 'find_evidence' },
  low_credibility: { label: 'Find Stronger Evidence', actionType: 'find_evidence' },
};

// ── Annotation priority display ─────────────────────────────────

export const ANNOTATION_PRIORITY_CONFIG: Record<
  AnnotationPriority,
  { color: string; bg: string; label: string }
> = {
  blocking: { color: 'text-red-600 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/30', label: 'Blocking' },
  important: { color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-100 dark:bg-amber-900/30', label: 'Important' },
  info: { color: 'text-neutral-500', bg: 'bg-neutral-100 dark:bg-neutral-800', label: 'Info' },
};

// ── Section type labels ─────────────────────────────────────────

export const SECTION_TYPE_LABELS: Record<SectionType, string> = {
  decision_frame: 'Decision Frame',
  inquiry_brief: 'Inquiry',
  synthesis: 'Synthesis',
  trade_offs: 'Trade-offs',
  recommendation: 'Recommendation',
  custom: 'Custom',
};

// ── Grounding score color helper ────────────────────────────────

export function getGroundingScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-500';
  if (score >= 50) return 'text-blue-500';
  if (score >= 25) return 'text-amber-500';
  return 'text-neutral-400';
}

export function getGroundingScoreStrokeColor(score: number): string {
  if (score >= 80) return 'stroke-emerald-500';
  if (score >= 50) return 'stroke-blue-500';
  if (score >= 25) return 'stroke-amber-500';
  return 'stroke-neutral-400';
}
