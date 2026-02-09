/**
 * useHomeDashboard Hook
 *
 * Fetches cross-case data for the home page dashboard.
 * Aggregates case home data + inquiry dashboards to produce:
 *   - The most recent active case (for the "recent decision" card)
 *   - Prioritized action items across all cases (for suggested action cards)
 *
 * Uses React Query for caching. Shares cache keys with useCaseHome (['case-home', caseId]).
 */

import { useMemo } from 'react';
import { useQueries } from '@tanstack/react-query';
import { useProjectsQuery } from './useProjectsQuery';
import { plansAPI } from '@/lib/api/plans';
import type { CaseHomeData, CaseStage } from '@/lib/types/plan';
import type { ActionCardVariant } from '@/components/ui/action-card';

// ===== Types =====

export interface HomeActionItem {
  id: string;
  type:
    | 'resolve_inquiry'
    | 'research_completed'
    | 'untested_assumptions'
    | 'resume_investigating'
    | 'criteria_progress'
    | 'start_investigation'
    | 'new_exploration';
  caseId: string;
  caseTitle: string;
  title: string;
  description: string;
  priority: number;
  variant: ActionCardVariant;
  href: string;
}

export interface RecentDecision {
  caseId: string;
  title: string;
  stage: CaseStage;
  inquiryProgress: { resolved: number; total: number };
  criteriaProgress: { met: number; total: number };
  updatedAt: string;
}

export interface UseHomeDashboardReturn {
  recentDecision: RecentDecision | null;
  actionItems: HomeActionItem[];
  isLoading: boolean;
}

// ===== Priority constants =====

const PRIORITY_RESOLVE = 10;
const PRIORITY_RESEARCH = 20;
const PRIORITY_ASSUMPTIONS = 30;
const PRIORITY_RESUME = 40;
const PRIORITY_CRITERIA = 50;
const PRIORITY_START = 60;
const PRIORITY_NEW = 100;

const MAX_CASES_TO_FETCH = 5;
const MAX_ACTION_ITEMS = 3;

// ===== Hook =====

export function useHomeDashboard(): UseHomeDashboardReturn {
  const { data: projects = [], isLoading: projectsLoading } = useProjectsQuery();

  // Flatten all cases and sort by most recently updated
  const activeCases = useMemo(() => {
    const allCases = projects.flatMap((p) => p.cases);
    return allCases
      .filter((c) => c.status !== 'archived')
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, MAX_CASES_TO_FETCH);
  }, [projects]);

  // Fetch case home data for each active case in parallel
  const caseHomeQueries = useQueries({
    queries: activeCases.map((c) => ({
      queryKey: ['case-home', c.id],
      queryFn: () => plansAPI.getCaseHome(c.id),
      staleTime: 30_000,
      enabled: activeCases.length > 0,
    })),
  });

  const isLoading = projectsLoading || caseHomeQueries.some((q) => q.isLoading);

  // Build the most recent decision card
  const recentDecision = useMemo<RecentDecision | null>(() => {
    if (activeCases.length === 0) return null;
    const mostRecent = activeCases[0];
    const homeData = caseHomeQueries[0]?.data;

    const inquiries = homeData?.inquiries ?? [];
    const criteria = homeData?.plan?.current_content?.decision_criteria ?? [];

    return {
      caseId: mostRecent.id,
      title: mostRecent.title,
      stage: homeData?.plan?.stage ?? 'exploring',
      inquiryProgress: {
        resolved: inquiries.filter((i) => i.status === 'resolved').length,
        total: inquiries.length,
      },
      criteriaProgress: {
        met: criteria.filter((c) => c.is_met).length,
        total: criteria.length,
      },
      updatedAt: mostRecent.updated_at,
    };
  }, [activeCases, caseHomeQueries]);

  // Build prioritized action items across all cases
  const actionItems = useMemo<HomeActionItem[]>(() => {
    const items: HomeActionItem[] = [];

    caseHomeQueries.forEach((query, idx) => {
      const caseItem = activeCases[idx];
      if (!caseItem || !query.data) return;
      const data: CaseHomeData = query.data;
      const caseTitle = data.case.title;
      const caseId = caseItem.id;

      // 1. Ready to resolve: inquiries with investigating status + enough evidence
      data.inquiries
        .filter((i) => i.status === 'investigating' && i.evidence_count >= 2)
        .forEach((i) => {
          items.push({
            id: `resolve-${i.id}`,
            type: 'resolve_inquiry',
            caseId,
            caseTitle,
            title: `Ready to resolve: ${i.title}`,
            description: `${i.evidence_count} evidence items collected`,
            priority: PRIORITY_RESOLVE,
            variant: 'warning',
            href: `/cases/${caseId}`,
          });
        });

      // 2. Research completed (recent events)
      data.activity.recent_events
        .filter((e) => e.type === 'ResearchCompleted')
        .forEach((e) => {
          const title = (e.payload?.title as string) || 'Research report';
          items.push({
            id: `research-${e.id}`,
            type: 'research_completed',
            caseId,
            caseTitle,
            title: `Research completed: ${title}`,
            description: `New findings for ${caseTitle}`,
            priority: PRIORITY_RESEARCH,
            variant: 'info',
            href: `/cases/${caseId}`,
          });
        });

      // 3. High-risk untested assumptions
      const assumptions = data.plan?.current_content?.assumptions ?? [];
      const highRiskUntested = assumptions.filter(
        (a) => a.status === 'untested' && a.risk_level === 'high'
      );
      if (highRiskUntested.length > 0) {
        items.push({
          id: `assumptions-${caseId}`,
          type: 'untested_assumptions',
          caseId,
          caseTitle,
          title: `${highRiskUntested.length} untested high-risk assumption${highRiskUntested.length > 1 ? 's' : ''}`,
          description: caseTitle,
          priority: PRIORITY_ASSUMPTIONS,
          variant: 'warning',
          href: `/cases/${caseId}`,
        });
      }

      // 4. Resume investigating (has active inquiries)
      const investigating = data.inquiries.filter((i) => i.status === 'investigating');
      if (investigating.length > 0 && !items.some((i) => i.caseId === caseId && i.type === 'resolve_inquiry')) {
        items.push({
          id: `resume-${caseId}`,
          type: 'resume_investigating',
          caseId,
          caseTitle,
          title: `Continue investigating`,
          description: `${investigating.length} active inquir${investigating.length > 1 ? 'ies' : 'y'} in ${caseTitle}`,
          priority: PRIORITY_RESUME,
          variant: 'accent',
          href: `/cases/${caseId}`,
        });
      }

      // 5. Criteria progress (synthesizing/ready stage)
      const stage = data.plan?.stage;
      const criteria = data.plan?.current_content?.decision_criteria ?? [];
      if ((stage === 'synthesizing' || stage === 'ready') && criteria.length > 0) {
        const met = criteria.filter((c) => c.is_met).length;
        if (met < criteria.length) {
          items.push({
            id: `criteria-${caseId}`,
            type: 'criteria_progress',
            caseId,
            caseTitle,
            title: `${met}/${criteria.length} decision criteria met`,
            description: caseTitle,
            priority: PRIORITY_CRITERIA,
            variant: 'success',
            href: `/cases/${caseId}`,
          });
        }
      }

      // 6. Start investigation (open inquiries not started)
      const openInquiries = data.inquiries.filter((i) => i.status === 'open');
      if (openInquiries.length > 0) {
        items.push({
          id: `start-${caseId}`,
          type: 'start_investigation',
          caseId,
          caseTitle,
          title: `${openInquiries.length} open question${openInquiries.length > 1 ? 's' : ''} to investigate`,
          description: caseTitle,
          priority: PRIORITY_START,
          variant: 'default',
          href: `/cases/${caseId}`,
        });
      }
    });

    // Sort by priority (lower = higher) and take top N
    items.sort((a, b) => a.priority - b.priority);

    // Deduplicate — at most one item per case to keep diversity
    const seen = new Set<string>();
    const deduped: HomeActionItem[] = [];
    for (const item of items) {
      if (deduped.length >= MAX_ACTION_ITEMS) break;
      if (!seen.has(item.caseId)) {
        seen.add(item.caseId);
        deduped.push(item);
      } else if (deduped.length < MAX_ACTION_ITEMS) {
        // Allow multiple from same case if we haven't filled slots
        deduped.push(item);
      }
    }

    // Always include "new exploration" as fallback to fill remaining slots
    while (deduped.length < MAX_ACTION_ITEMS) {
      deduped.push({
        id: `new-${deduped.length}`,
        type: 'new_exploration',
        caseId: '',
        caseTitle: '',
        title: deduped.length === 0 ? 'Start a new decision' : 'Explore a new question',
        description: deduped.length === 0 ? 'Describe a decision you\'re working through' : 'Chat about anything on your mind',
        priority: PRIORITY_NEW,
        variant: 'accent',
        href: '',
      });
    }

    return deduped;
  }, [caseHomeQueries, activeCases]);

  return {
    recentDecision,
    actionItems,
    isLoading,
  };
}
