/**
 * useProjectDashboard Hook
 *
 * Fetches and aggregates all data needed for the project home page:
 * - Project metadata
 * - Cases with inquiries, plans, and readiness
 * - Cross-case assumption stats
 * - Aggregated action items (resolve inquiry, untested assumptions, etc.)
 * - Recent activity across all cases
 *
 * Uses React Query for caching. Reuses the case-home cache key from useHomeDashboard.
 */

import { useMemo } from 'react';
import { useQuery, useQueries } from '@tanstack/react-query';
import { projectsAPI } from '@/lib/api/projects';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { plansAPI } from '@/lib/api/plans';
import type { Project } from '@/lib/types/project';
import type { CaseHomeData, CaseStage, PlanAssumption } from '@/lib/types/plan';
import type { Case, Inquiry } from '@/lib/types/case';

// ===== Types =====

export interface ProjectCaseSummary {
  id: string;
  title: string;
  status: string;
  stage: CaseStage;
  updatedAt: string;
  inquiries: {
    total: number;
    resolved: number;
    investigating: number;
    open: number;
  };
  assumptions: {
    total: number;
    untested: number;
    highRiskUntested: number;
  };
  isReady: boolean;
}

export interface ProjectStats {
  totalCases: number;
  readyCases: number;
  totalInquiries: number;
  resolvedInquiries: number;
  totalAssumptions: number;
  untestedAssumptions: number;
  highRiskUntested: number;
}

export interface ProjectActionItem {
  id: string;
  type: 'resolve_inquiry' | 'untested_assumptions' | 'resume_investigating' | 'criteria_progress' | 'start_investigation';
  caseId: string;
  caseTitle: string;
  title: string;
  description: string;
  priority: number;
  href: string;
}

export interface UseProjectDashboardReturn {
  project: Project | null;
  cases: ProjectCaseSummary[];
  stats: ProjectStats;
  actionItems: ProjectActionItem[];
  isLoading: boolean;
  error: string | null;
}

// Priority constants (lower = higher priority)
const PRIORITY_RESOLVE = 10;
const PRIORITY_ASSUMPTIONS = 20;
const PRIORITY_RESUME = 30;
const PRIORITY_CRITERIA = 40;
const PRIORITY_START = 50;

const MAX_ACTION_ITEMS = 5;

// ===== Hook =====

export function useProjectDashboard(projectId: string): UseProjectDashboardReturn {
  // 1. Fetch project metadata
  const projectQuery = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsAPI.getProject(projectId),
    enabled: !!projectId,
    staleTime: 60_000,
  });

  // 2. Fetch all cases (we filter by project client-side)
  const casesQuery = useQuery({
    queryKey: ['cases-list'],
    queryFn: () => casesAPI.listCases(),
    staleTime: 30_000,
  });

  // Filter to this project's cases
  const projectCaseIds = useMemo(() => {
    if (!casesQuery.data) return [];
    return casesQuery.data
      .filter((c: Case) => c.project === projectId && c.status !== 'archived')
      .sort((a: Case, b: Case) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  }, [casesQuery.data, projectId]);

  // 3. Fetch case home data for each case in parallel (reuses cache from useHomeDashboard)
  const caseHomeQueries = useQueries({
    queries: projectCaseIds.map((c: Case) => ({
      queryKey: ['case-home', c.id],
      queryFn: () => plansAPI.getCaseHome(c.id),
      staleTime: 30_000,
      enabled: projectCaseIds.length > 0,
    })),
  });

  const isLoading =
    projectQuery.isLoading ||
    casesQuery.isLoading ||
    caseHomeQueries.some((q) => q.isLoading);

  const error =
    projectQuery.error instanceof Error ? projectQuery.error.message :
    casesQuery.error instanceof Error ? casesQuery.error.message :
    null;

  // 4. Build case summaries with aggregated data
  const cases = useMemo<ProjectCaseSummary[]>(() => {
    return projectCaseIds.map((caseItem: Case, idx: number) => {
      const homeData = caseHomeQueries[idx]?.data as CaseHomeData | undefined;
      const inquiries = homeData?.inquiries ?? [];
      const assumptions = homeData?.plan?.current_content?.assumptions ?? [];

      const resolved = inquiries.filter((i) => i.status === 'resolved').length;
      const investigating = inquiries.filter((i) => i.status === 'investigating').length;
      const open = inquiries.filter((i) => i.status === 'open').length;

      const untested = assumptions.filter((a: PlanAssumption) => a.status === 'untested').length;
      const highRiskUntested = assumptions.filter(
        (a: PlanAssumption) => a.status === 'untested' && a.risk_level === 'high'
      ).length;

      const isReady = inquiries.length > 0 && resolved === inquiries.length;

      return {
        id: caseItem.id,
        title: caseItem.title,
        status: caseItem.status,
        stage: homeData?.plan?.stage ?? 'exploring',
        updatedAt: caseItem.updated_at,
        inquiries: {
          total: inquiries.length,
          resolved,
          investigating,
          open,
        },
        assumptions: {
          total: assumptions.length,
          untested,
          highRiskUntested,
        },
        isReady,
      };
    });
  }, [projectCaseIds, caseHomeQueries]);

  // 5. Build aggregate stats
  const stats = useMemo<ProjectStats>(() => {
    return cases.reduce(
      (acc, c) => ({
        totalCases: acc.totalCases + 1,
        readyCases: acc.readyCases + (c.isReady ? 1 : 0),
        totalInquiries: acc.totalInquiries + c.inquiries.total,
        resolvedInquiries: acc.resolvedInquiries + c.inquiries.resolved,
        totalAssumptions: acc.totalAssumptions + c.assumptions.total,
        untestedAssumptions: acc.untestedAssumptions + c.assumptions.untested,
        highRiskUntested: acc.highRiskUntested + c.assumptions.highRiskUntested,
      }),
      {
        totalCases: 0,
        readyCases: 0,
        totalInquiries: 0,
        resolvedInquiries: 0,
        totalAssumptions: 0,
        untestedAssumptions: 0,
        highRiskUntested: 0,
      }
    );
  }, [cases]);

  // 6. Build prioritized action items across cases
  const actionItems = useMemo<ProjectActionItem[]>(() => {
    const items: ProjectActionItem[] = [];

    caseHomeQueries.forEach((query, idx) => {
      const caseItem = projectCaseIds[idx] as Case | undefined;
      if (!caseItem || !query.data) return;
      const data = query.data as CaseHomeData;
      const caseTitle = data.case.title;
      const caseId = caseItem.id;

      // Ready to resolve: inquiries with evidence
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
            href: `/cases/${caseId}`,
          });
        });

      // High-risk untested assumptions
      const assumptions = data.plan?.current_content?.assumptions ?? [];
      const highRiskUntested = assumptions.filter(
        (a: PlanAssumption) => a.status === 'untested' && a.risk_level === 'high'
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
          href: `/cases/${caseId}`,
        });
      }

      // Resume investigating
      const investigating = data.inquiries.filter((i) => i.status === 'investigating');
      if (investigating.length > 0 && !items.some((i) => i.caseId === caseId && i.type === 'resolve_inquiry')) {
        items.push({
          id: `resume-${caseId}`,
          type: 'resume_investigating',
          caseId,
          caseTitle,
          title: `Continue investigating`,
          description: `${investigating.length} active inquir${investigating.length > 1 ? 'ies' : 'y'}`,
          priority: PRIORITY_RESUME,
          href: `/cases/${caseId}`,
        });
      }

      // Criteria progress
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
            href: `/cases/${caseId}`,
          });
        }
      }

      // Open inquiries not started
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
          href: `/cases/${caseId}`,
        });
      }
    });

    // Sort by priority and take top N
    items.sort((a, b) => a.priority - b.priority);
    return items.slice(0, MAX_ACTION_ITEMS);
  }, [caseHomeQueries, projectCaseIds]);

  return {
    project: projectQuery.data ?? null,
    cases,
    stats,
    actionItems,
    isLoading,
    error,
  };
}
