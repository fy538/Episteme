/**
 * Intelligence Transform Utilities
 *
 * Shared functions for transforming backend data into IntelligenceItem format.
 * Used by useIntelligence and dashboard pages.
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
