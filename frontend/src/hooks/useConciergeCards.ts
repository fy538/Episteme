/**
 * useConciergeCards Hook
 *
 * Fetches concierge data from the backend and runs the card
 * selection algorithm to pick the best 1-3 cards to display
 * on the project home page.
 *
 * Card priority (highest first):
 *   1. Decision at Risk — overdue outcome check or contradicted assumption
 *   2. Worth Exploring — proactive strategic prompt (Phase 5)
 *   3. Case Needs Attention — untested load-bearing assumptions
 *   4. Resume Work — recently active case, mid-investigation
 *   5. Orientation Shift — knowledge base changed meaningfully
 *   6. Get Started — upload docs or start a case
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { projectsAPI } from '@/lib/api/projects';
import type { ConciergeData, ConciergeCard } from '@/lib/types/concierge';

function insightTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    exploration_angle: 'A direction worth investigating',
    tension: 'A contradiction in your sources',
    gap: 'A gap in your knowledge base',
    blind_spot: 'An unquestioned assumption detected',
    weak_evidence: 'A claim with thin support',
    pattern: 'A recurring pattern across your sources',
  };
  return labels[type] || 'Something worth exploring';
}

function selectCards(data: ConciergeData, projectId: string): ConciergeCard[] {
  const candidates: ConciergeCard[] = [];

  // Priority 1: Decision at Risk
  for (const risk of data.decisions_at_risk.slice(0, 2)) {
    candidates.push({
      type: 'decision_at_risk',
      priority: 1,
      title: risk.case_title,
      subtitle:
        risk.risk_type === 'overdue_outcome'
          ? `Outcome check overdue by ${risk.days_overdue} day${risk.days_overdue !== 1 ? 's' : ''}`
          : 'Key assumption now contested by new evidence',
      href: `/cases/${risk.case_id}`,
      caseId: risk.case_id,
      variant: 'warning',
    });
  }

  // Priority 2: Worth Exploring
  for (const prompt of data.worth_exploring.slice(0, 1)) {
    candidates.push({
      type: 'worth_exploring',
      priority: 2,
      title: prompt.title,
      subtitle: insightTypeLabel(prompt.insight_type),
      href: `/projects/${projectId}/explore`,
      variant: 'accent',
    });
  }

  // Priority 3: Case Needs Attention
  for (const att of data.cases_needing_attention.slice(0, 2)) {
    candidates.push({
      type: 'case_needs_attention',
      priority: 3,
      title: att.case_title,
      subtitle: att.detail,
      href: `/cases/${att.case_id}`,
      caseId: att.case_id,
      variant: 'info',
    });
  }

  // Priority 4: Resume Work
  for (const recent of data.recent_active_cases.slice(0, 2)) {
    candidates.push({
      type: 'resume_work',
      priority: 4,
      title: recent.case_title,
      subtitle: recent.progress_summary,
      href: `/cases/${recent.case_id}`,
      caseId: recent.case_id,
      variant: 'neutral',
    });
  }

  // Priority 5: Orientation Shift
  if (data.orientation_shift?.has_shift) {
    candidates.push({
      type: 'orientation_shift',
      priority: 5,
      title: 'Your knowledge base has changed',
      subtitle: 'New themes or evidence have been detected',
      href: `/projects/${projectId}/explore`,
      variant: 'info',
    });
  }

  // Priority 6: Get Started
  if (!data.has_documents) {
    candidates.push({
      type: 'get_started',
      priority: 6,
      title: 'Upload documents',
      subtitle: 'Add sources to build your knowledge base',
      href: `#upload`,
      variant: 'action',
    });
  }
  if (!data.has_cases) {
    candidates.push({
      type: 'get_started',
      priority: 6,
      title: 'Start a decision',
      subtitle: 'Describe a decision question to investigate',
      href: `/projects/${projectId}/chat`,
      variant: 'action',
    });
  }

  // ─── De-duplicate by caseId (keep highest priority per case) ───
  const seenCaseIds = new Set<string>();
  const deduped = candidates.filter((c) => {
    if (c.caseId) {
      if (seenCaseIds.has(c.caseId)) return false;
      seenCaseIds.add(c.caseId);
    }
    return true;
  });

  // ─── Limit to 1 card per type (except get_started) ───
  const seenTypes = new Set<string>();
  const typeFiltered = deduped.filter((c) => {
    if (c.type === 'get_started') return true;
    if (seenTypes.has(c.type)) return false;
    seenTypes.add(c.type);
    return true;
  });

  // ─── Sort by priority, take top 3 ───
  typeFiltered.sort((a, b) => a.priority - b.priority);
  return typeFiltered.slice(0, 3);
}

export function useConciergeCards(projectId: string) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['project-concierge', projectId],
    queryFn: () => projectsAPI.getConcierge(projectId),
    staleTime: 30_000, // 30 seconds
    enabled: !!projectId,
  });

  const cards = useMemo(() => {
    if (!data) return [];
    return selectCards(data, projectId);
  }, [data, projectId]);

  return { cards, isLoading, error, data };
}
