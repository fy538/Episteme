/**
 * useTodaysBrief Hook
 *
 * Pure derivation from ProjectWithCases[] → personalized home page data.
 * Zero additional API calls — everything computed from cached project data.
 */

import { useMemo } from 'react';
import type { ProjectWithCases } from './useProjectsQuery';

export interface BriefActionItem {
  heading: string;
  reason: string;
  impact: string;
  caseId: string;
  caseTitle: string;
  severity: 'high' | 'medium' | 'low';
  type: 'tension' | 'blind_spot' | 'continue';
}

export interface BriefArticle {
  id: string;
  title: string;
  subtitle: string;
  snippet: string;
  caseId: string;
  type: 'tension_digest' | 'progress_update' | 'cross_case_pattern';
}

export interface TodaysBrief {
  welcomeSlogan: string;
  welcomeSubtitle: string;
  actionItem: BriefActionItem | null;
  articles: BriefArticle[];
  stats: {
    activeCases: number;
    nearReadyCases: number;
    totalTensions: number;
    totalBlindSpots: number;
    openInquiries: number;
  };
  isEmpty: boolean;
}

function getTimeGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export function useTodaysBrief(projects: ProjectWithCases[]): TodaysBrief {
  return useMemo(() => {
    const allCases = projects.flatMap(p => p.cases);

    if (allCases.length === 0) {
      return {
        welcomeSlogan: 'What would you like to work on?',
        welcomeSubtitle: 'Ask a question, explore a decision, or start something new',
        actionItem: null,
        articles: [],
        stats: { activeCases: 0, nearReadyCases: 0, totalTensions: 0, totalBlindSpots: 0, openInquiries: 0 },
        isEmpty: true,
      };
    }

    // Stats
    const activeCases = allCases.length;
    const nearReadyCases = allCases.filter(c => c.readinessScore >= 80).length;
    const totalTensions = allCases.reduce((sum, c) => sum + c.tensionsCount, 0);
    const totalBlindSpots = allCases.reduce((sum, c) => sum + c.blindSpotsCount, 0);
    const openInquiries = allCases.reduce(
      (sum, c) => sum + c.inquiries.filter(i => i.status !== 'resolved').length,
      0
    );
    const needsAttention = totalTensions + totalBlindSpots;

    // Welcome slogan
    const greeting = getTimeGreeting();
    let sloganContext = `${activeCases} ${activeCases === 1 ? 'case' : 'cases'} active`;
    if (needsAttention > 0) {
      sloganContext += `, ${needsAttention} ${needsAttention === 1 ? 'needs' : 'need'} attention`;
    }
    const welcomeSlogan = needsAttention === 0 && activeCases > 0
      ? `${greeting}. All decisions on track.`
      : `${greeting}. ${sloganContext}.`;
    const welcomeSubtitle = needsAttention > 0
      ? "Here's what matters today"
      : 'Pick up where you left off or start something new';

    // Action item — top priority
    const sortedByTensions = [...allCases].sort((a, b) => b.tensionsCount - a.tensionsCount);
    const sortedByBlindSpots = [...allCases].sort((a, b) => b.blindSpotsCount - a.blindSpotsCount);
    const sortedByRecent = [...allCases].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );

    let actionItem: BriefActionItem | null = null;
    if (sortedByTensions[0]?.tensionsCount > 0) {
      const c = sortedByTensions[0];
      actionItem = {
        heading: `Resolve ${c.tensionsCount} ${c.tensionsCount === 1 ? 'tension' : 'tensions'}`,
        reason: 'Sources disagree on key points in your analysis',
        impact: c.readinessScore > 0
          ? `Readiness blocked at ${c.readinessScore}%`
          : 'Blocking your readiness score',
        caseId: c.id,
        caseTitle: c.title,
        severity: 'high',
        type: 'tension',
      };
    } else if (sortedByBlindSpots[0]?.blindSpotsCount > 0) {
      const c = sortedByBlindSpots[0];
      const openCount = c.inquiries.filter(i => i.status !== 'resolved').length;
      actionItem = {
        heading: `Address ${c.blindSpotsCount} blind ${c.blindSpotsCount === 1 ? 'spot' : 'spots'}`,
        reason: 'Areas of your analysis that may need more evidence',
        impact: openCount > 0
          ? `${openCount} ${openCount === 1 ? 'inquiry' : 'inquiries'} still open`
          : 'Strengthen your conclusions',
        caseId: c.id,
        caseTitle: c.title,
        severity: 'medium',
        type: 'blind_spot',
      };
    } else if (sortedByRecent[0]) {
      const c = sortedByRecent[0];
      const openCount = c.inquiries.filter(i => i.status !== 'resolved').length;
      actionItem = {
        heading: `Continue working on ${c.title}`,
        reason: openCount > 0
          ? `${openCount} open ${openCount === 1 ? 'inquiry' : 'inquiries'} to investigate`
          : 'Pick up where you left off',
        impact: c.readinessScore >= 80
          ? `${c.readinessScore}% ready — review the brief`
          : c.readinessScore > 0
          ? `${c.readinessScore}% readiness so far`
          : 'Build your analysis',
        caseId: c.id,
        caseTitle: c.title,
        severity: 'low',
        type: 'continue',
      };
    }

    // Articles — newspaper-style cards (max 3)
    const articles: BriefArticle[] = [];

    // Tension digest cards
    const tensionCases = allCases.filter(c => c.tensionsCount > 0).sort((a, b) => b.tensionsCount - a.tensionsCount);
    for (const c of tensionCases.slice(0, 2)) {
      articles.push({
        id: `tension-${c.id}`,
        title: `${c.tensionsCount} ${c.tensionsCount === 1 ? 'Tension' : 'Tensions'} to Resolve`,
        subtitle: c.title,
        snippet: `Sources disagree on key points. Review the conflicting evidence to strengthen your analysis.`,
        caseId: c.id,
        type: 'tension_digest',
      });
    }

    // Progress update cards
    const progressCases = allCases
      .filter(c => c.readinessScore >= 80 && !tensionCases.includes(c))
      .sort((a, b) => b.readinessScore - a.readinessScore);
    for (const c of progressCases.slice(0, 1)) {
      articles.push({
        id: `progress-${c.id}`,
        title: `${c.readinessScore}% Ready`,
        subtitle: c.title,
        snippet: `Nearly decision-ready. Review the brief and confirm your conclusions.`,
        caseId: c.id,
        type: 'progress_update',
      });
    }

    // Cross-case pattern card (when 2+ cases)
    if (allCases.length >= 2 && articles.length < 3) {
      articles.push({
        id: 'cross-case',
        title: 'Cross-Case Patterns',
        subtitle: `${allCases.length} active cases`,
        snippet: `Look for connections and shared evidence across your active analyses.`,
        caseId: allCases[0].id,
        type: 'cross_case_pattern',
      });
    }

    return {
      welcomeSlogan,
      welcomeSubtitle,
      actionItem,
      articles: articles.slice(0, 3),
      stats: { activeCases, nearReadyCases, totalTensions, totalBlindSpots, openInquiries },
      isEmpty: false,
    };
  }, [projects]);
}
