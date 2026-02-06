/**
 * Intelligence Transform Utilities
 *
 * Shared functions for transforming backend data into IntelligenceItem format.
 * Used by useCaseReadiness, useIntelligence, and dashboard pages.
 */

import type { IntelligenceItem } from '@/lib/types/intelligence';
import type { BlindSpotPrompt } from '@/lib/types/case';

/**
 * Generate a simple unique ID
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2, 11);
}

/**
 * Transform BlindSpotPrompt to IntelligenceItem
 */
export function transformBlindSpotToIntelligenceItem(
  prompt: BlindSpotPrompt,
  caseId?: string,
  caseTitle?: string
): IntelligenceItem {
  return {
    id: `blind-${generateId()}`,
    type: 'blind_spot',
    priority: prompt.type === 'assumption' ? 'important' : 'suggested',
    scope: 'case',
    title: prompt.text,
    description: `${prompt.type}: ${prompt.text}`,
    caseId,
    caseTitle,
    blindSpot: {
      area: prompt.text,
      impact: 'May affect case conclusion',
      suggestedAction: prompt.action === 'create_inquiry' ? 'add_inquiry'
        : prompt.action === 'investigate' ? 'research'
        : 'discuss',
    },
    createdAt: new Date().toISOString(),
  };
}

/**
 * Transform contradiction string to tension IntelligenceItem
 */
export function transformContradictionToTension(
  contradiction: string,
  caseId?: string,
  caseTitle?: string
): IntelligenceItem {
  return {
    id: `tension-${generateId()}`,
    type: 'tension',
    priority: 'blocking',
    scope: 'case',
    title: 'Sources disagree',
    description: contradiction,
    caseId,
    caseTitle,
    tension: {
      sourceA: {
        id: 'source-a',
        name: 'Source A',
        content: contradiction,
        implication: 'Requires resolution',
      },
      sourceB: {
        id: 'source-b',
        name: 'Source B',
        content: 'Conflicting perspective',
        implication: 'Alternative interpretation',
      },
    },
    createdAt: new Date().toISOString(),
  };
}

/**
 * Calculate readiness score based on inquiry completion and blockers
 *
 * Formula:
 * - Inquiry completion: 50% weight (or 25% if no inquiries)
 * - Checklist completion: 30% weight (or 15% if no checklist)
 * - Base score: 20%
 * - Penalties: -10 per tension, -3 per blind spot
 */
export function calculateReadinessScore(
  inquiries: { total: number; resolved: number },
  checklistProgress?: { required: number; required_completed: number },
  tensionsCount: number = 0,
  blindSpotsCount: number = 0
): number {
  // Inquiry completion: 50% weight
  const inquiryScore = inquiries.total > 0
    ? (inquiries.resolved / inquiries.total) * 50
    : 25; // Partial credit if no inquiries yet

  // Checklist completion: 30% weight
  const checklistScore = checklistProgress && checklistProgress.required > 0
    ? (checklistProgress.required_completed / checklistProgress.required) * 30
    : 15; // Partial credit if no checklist yet

  // Base score of 20
  const baseScore = 20;

  // Penalties
  const tensionPenalty = tensionsCount * 10;
  const blindSpotPenalty = blindSpotsCount * 3;

  const rawScore = inquiryScore + checklistScore + baseScore - tensionPenalty - blindSpotPenalty;
  return Math.max(0, Math.min(100, Math.round(rawScore)));
}

/**
 * Sort intelligence items by priority
 */
export function sortByPriority(items: IntelligenceItem[]): IntelligenceItem[] {
  const priorityOrder: Record<string, number> = {
    blocking: 0,
    important: 1,
    suggested: 2,
  };
  return [...items].sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);
}

/**
 * Check if a date is within a certain number of hours ago
 */
export function isRecent(dateStr: string, hours: number): boolean {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);
  return diffHours <= hours;
}
