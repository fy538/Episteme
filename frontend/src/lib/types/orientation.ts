/**
 * Types for the lens-based project orientation layer.
 *
 * Orientation sits on top of the hierarchical cluster map and provides
 * editorial analysis — what the documents mean, not just what topics they cover.
 */

import type { ProjectInsight } from './hierarchy';

export type LensType =
  | 'positions_and_tensions'
  | 'structure_and_dependencies'
  | 'perspectives_and_sentiment'
  | 'obligations_and_constraints'
  | 'events_and_causation'
  | 'concepts_and_progression';

export type OrientationStatus = 'generating' | 'ready' | 'failed' | 'none';

export interface ProjectOrientation {
  id: string;
  project: string;
  status: OrientationStatus;
  lens_type: LensType | string;
  lead_text: string;
  lens_scores: Partial<Record<LensType, number>>;
  secondary_lens: string;
  secondary_lens_reason: string;
  is_current: boolean;
  generation_metadata: Record<string, unknown>;
  findings: OrientationFinding[];
  created_at: string;
  updated_at: string;
}

/**
 * A finding or exploration angle within an orientation.
 * Extends the base ProjectInsight with orientation-specific rendering fields.
 */
export type OrientationFinding = ProjectInsight;

/** Human-readable labels for each lens type. */
export const LENS_LABELS: Record<LensType, string> = {
  positions_and_tensions: 'Positions & Tensions',
  structure_and_dependencies: 'Structure & Dependencies',
  perspectives_and_sentiment: 'Perspectives & Sentiment',
  obligations_and_constraints: 'Obligations & Constraints',
  events_and_causation: 'Events & Causation',
  concepts_and_progression: 'Concepts & Progression',
};

/**
 * SSE event types emitted by the orientation stream:
 * - status: { status, lens_type }
 * - lead: { lead_text }
 * - finding: ProjectInsight (one per finding)
 * - angle: ProjectInsight (one per exploration angle)
 * - completed: { status: 'ready', metadata }
 * - failed: { error }
 * - timeout: { error }
 *
 * The actual handler type is `{ event: string; data: unknown }`
 * to match the base `streamGet` signature.
 */
