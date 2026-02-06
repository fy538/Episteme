/**
 * useIntelligence Hook
 *
 * Fetches and ranks intelligence items for a given scope.
 * Returns the most important action that should be surfaced.
 *
 * Connects to real backend APIs for:
 * - Gap analysis (blind spots and contradictions)
 * - Inquiry dashboard (next actions)
 * - Recent inquiries (activity feed)
 */

import { useState, useEffect, useCallback } from 'react';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import {
  generateId,
  transformBlindSpotToIntelligenceItem,
  transformContradictionToTension,
  sortByPriority,
  isRecent,
} from '@/lib/utils/intelligence-transforms';
import type {
  IntelligenceState,
  IntelligenceItem,
  ActivityItem,
  IntelligenceScope,
  ContinueState,
} from '@/lib/types/intelligence';
import type { BlindSpotPrompt, Inquiry } from '@/lib/types/case';

interface UseIntelligenceOptions {
  scope: IntelligenceScope;
  projectId?: string;
  caseId?: string;
  inquiryId?: string;
}

// Transform recent inquiry to activity item
function transformInquiryToActivity(inquiry: Inquiry): ActivityItem {
  const types: Record<string, ActivityItem['type']> = {
    resolved: 'inquiry_resolved',
    investigating: 'research_complete',
    open: 'blind_spot_surfaced',
  };

  return {
    id: `activity-${inquiry.id}`,
    type: types[inquiry.status] || 'inquiry_resolved',
    title: inquiry.status === 'resolved' ? 'Inquiry resolved' : `Inquiry ${inquiry.status}`,
    description: inquiry.title,
    caseId: inquiry.case,
    inquiryId: inquiry.id,
    inquiryTitle: inquiry.title,
    timestamp: inquiry.updated_at,
    isNew: isRecent(inquiry.updated_at, 24), // New if updated in last 24 hours
  };
}

export function useIntelligence(options: UseIntelligenceOptions): IntelligenceState & {
  continueState: ContinueState | null;
  error: string | null;
  refresh: () => void;
  dismissItem: (itemId: string) => void;
} {
  const { scope, projectId, caseId } = options;

  const [state, setState] = useState<IntelligenceState>({
    scope,
    topAction: null,
    exploration: null,
    activity: [],
    allItems: [],
    isLoading: true,
    lastUpdated: new Date().toISOString(),
  });

  const [continueState, setContinueState] = useState<ContinueState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchIntelligence = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true }));
    setError(null);

    try {
      let topAction: IntelligenceItem | null = null;
      let exploration: IntelligenceItem | null = null;
      let activity: ActivityItem[] = [];
      let allItems: IntelligenceItem[] = [];

      if (scope === 'case' && caseId) {
        // Fetch case-specific intelligence
        const [gaps, inquiries] = await Promise.all([
          casesAPI.getBlindSpotPrompts(caseId).catch(() => null),
          inquiriesAPI.getByCase(caseId).catch(() => []),
        ]);

        // Transform contradictions to tensions using shared utility
        const contradictions = gaps?.contradictions || [];
        const tensions = contradictions.map((c: string) =>
          transformContradictionToTension(c, caseId)
        );

        // Transform blind spot prompts using shared utility
        const blindSpotPrompts = gaps?.prompts || [];
        const blindSpots = blindSpotPrompts.map((p: BlindSpotPrompt) =>
          transformBlindSpotToIntelligenceItem(p, caseId)
        );

        // Combine and sort using shared utility
        allItems = sortByPriority([...tensions, ...blindSpots]);
        topAction = allItems[0] || null;

        // Activity from recent inquiries
        const recentInquiries = inquiries
          .filter((i: Inquiry) => isRecent(i.updated_at, 72)) // Last 72 hours
          .slice(0, 5);
        activity = recentInquiries.map(transformInquiryToActivity);

      } else if (scope === 'project' && projectId) {
        // For project scope, we'd need to aggregate across cases
        // For MVP, return empty - the readiness hook handles per-case data
        allItems = [];
        topAction = null;

        // Exploration for project level
        exploration = {
          id: `explore-${generateId()}`,
          type: 'explore',
          priority: 'suggested',
          scope: 'project',
          title: 'Explore connections across your cases',
          description: 'Look for patterns and relationships between cases in this project.',
          projectId,
          exploration: {
            question: 'What connections exist between the cases in this project?',
            context: 'Cross-case analysis',
            connectionType: 'cross_case',
          },
          createdAt: new Date().toISOString(),
        };

      } else if (scope === 'home') {
        // For home scope, provide simple data-driven placeholder content
        // In future: aggregate across all projects/cases from API

        // Placeholder "continue" action - would come from tracking last activity
        topAction = {
          id: `continue-${generateId()}`,
          type: 'continue',
          priority: 'suggested',
          scope: 'home',
          title: 'Pick up where you left off',
          description: 'Continue your analysis work',
          createdAt: new Date().toISOString(),
        };

        // Placeholder exploration
        exploration = {
          id: `explore-${generateId()}`,
          type: 'explore',
          priority: 'suggested',
          scope: 'home',
          title: 'Start a new analysis',
          description: 'Begin investigating a new question or decision.',
          exploration: {
            question: 'What decision are you working on?',
            context: 'I can help structure your thinking and gather evidence.',
            connectionType: 'new_angle',
          },
          createdAt: new Date().toISOString(),
        };

        // Placeholder activity - would come from aggregating recent changes
        activity = [
          {
            id: `activity-placeholder-1`,
            type: 'research_complete' as const,
            title: 'Analysis tools ready',
            description: 'Start by selecting a case or creating a new one',
            timestamp: new Date().toISOString(),
            isNew: true,
          },
        ];

        allItems = [topAction, exploration];

        // Set placeholder continue state
        // In future: derive from actual recent case activity
        setContinueState({
          type: 'case',
          title: 'Recent Analysis',
          subtitle: 'Continue your work',
          lastActivity: new Date().toISOString(),
        });
      }

      setState({
        scope,
        topAction,
        exploration,
        activity,
        allItems,
        isLoading: false,
        lastUpdated: new Date().toISOString(),
      });
    } catch (err) {
      console.error('Failed to fetch intelligence:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch intelligence');

      setState({
        scope,
        topAction: null,
        exploration: null,
        activity: [],
        allItems: [],
        isLoading: false,
        lastUpdated: new Date().toISOString(),
      });
    }
  }, [scope, projectId, caseId]);

  // Initial fetch
  useEffect(() => {
    fetchIntelligence();
  }, [fetchIntelligence]);

  // Refresh function
  const refresh = useCallback(() => {
    fetchIntelligence();
  }, [fetchIntelligence]);

  // Dismiss an item
  const dismissItem = useCallback((itemId: string) => {
    setState(prev => ({
      ...prev,
      allItems: prev.allItems.map(item =>
        item.id === itemId ? { ...item, dismissed: true, dismissedAt: new Date().toISOString() } : item
      ),
      // If we dismissed the top action, find the next one
      topAction: prev.topAction?.id === itemId
        ? prev.allItems.find(item => item.id !== itemId && !item.dismissed) || null
        : prev.topAction,
    }));
  }, []);

  return {
    ...state,
    continueState,
    error,
    refresh,
    dismissItem,
  };
}

export default useIntelligence;
