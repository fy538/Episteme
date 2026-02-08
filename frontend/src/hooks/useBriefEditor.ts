/**
 * useBriefEditor — Composed hook for the unified brief editor.
 *
 * Merges `useBrief` (grounding, sections, annotations, evolve) with
 * `useBriefSuggestions` (AI suggestions) and adds section-cursor tracking
 * for the editor. Provides a single interface for the UnifiedBriefView.
 */

'use client';

import { useState, useMemo, useCallback } from 'react';
import { useBrief } from '@/hooks/useBrief';
import { useBriefSuggestions } from '@/hooks/useBriefSuggestions';
import type { BriefSection, BriefAnnotation } from '@/lib/types/case';

interface UseBriefEditorOptions {
  caseId: string;
  documentId: string;
  onContentUpdate?: (newContent: string) => void;
}

export function useBriefEditor({
  caseId,
  documentId,
  onContentUpdate,
}: UseBriefEditorOptions) {
  // ── Grounding & Sections ──────────────────────────────────────
  const brief = useBrief({ caseId });

  // ── AI Suggestions ────────────────────────────────────────────
  const suggestions = useBriefSuggestions({
    documentId,
    onContentUpdate,
  });

  // ── Active Section Tracking ───────────────────────────────────
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);

  // Build O(1) lookup map: sectionId → BriefSection
  const sectionMap = useMemo(() => {
    const map = new Map<string, BriefSection>();
    const collect = (sections: BriefSection[]) => {
      for (const s of sections) {
        map.set(s.section_id, s);
        if (s.subsections?.length) collect(s.subsections);
      }
    };
    collect(brief.sections);
    return map;
  }, [brief.sections]);

  // Also build ID-based lookup (section.id, not section_id)
  const sectionByIdMap = useMemo(() => {
    const map = new Map<string, BriefSection>();
    const collect = (sections: BriefSection[]) => {
      for (const s of sections) {
        map.set(s.id, s);
        if (s.subsections?.length) collect(s.subsections);
      }
    };
    collect(brief.sections);
    return map;
  }, [brief.sections]);

  // Get section by marker ID (the section_id field, e.g. "sf-abc12345")
  const getSectionByMarker = useCallback(
    (sectionId: string): BriefSection | null => {
      return sectionMap.get(sectionId) ?? null;
    },
    [sectionMap]
  );

  // Get section by UUID (the id field)
  const getSectionById = useCallback(
    (id: string): BriefSection | null => {
      return sectionByIdMap.get(id) ?? null;
    },
    [sectionByIdMap]
  );

  // Derive active section from activeSectionId
  const activeSection = useMemo((): BriefSection | null => {
    if (!activeSectionId) return null;
    // Try marker ID first, then UUID
    return sectionMap.get(activeSectionId) ?? sectionByIdMap.get(activeSectionId) ?? null;
  }, [activeSectionId, sectionMap, sectionByIdMap]);

  // Get annotations for a specific section
  const getSectionAnnotations = useCallback(
    (sectionId: string): BriefAnnotation[] => {
      const section = sectionMap.get(sectionId) ?? sectionByIdMap.get(sectionId);
      return section?.annotations ?? [];
    },
    [sectionMap, sectionByIdMap]
  );

  // Ordered flat list of section_ids for navigation (next/prev)
  const sectionOrder = useMemo(() => {
    return brief.sections.map((s) => s.section_id);
  }, [brief.sections]);

  // Navigate to next/previous section
  const navigateSection = useCallback(
    (direction: 'next' | 'prev') => {
      if (sectionOrder.length === 0) return null;
      if (!activeSectionId) {
        return sectionOrder[direction === 'next' ? 0 : sectionOrder.length - 1];
      }
      const idx = sectionOrder.indexOf(activeSectionId);
      if (idx === -1) return sectionOrder[0];
      const nextIdx = direction === 'next'
        ? Math.min(idx + 1, sectionOrder.length - 1)
        : Math.max(idx - 1, 0);
      return sectionOrder[nextIdx];
    },
    [sectionOrder, activeSectionId]
  );

  return {
    // ── Grounding & Sections (from useBrief) ────────────────────
    sections: brief.sections,
    briefId: brief.briefId,
    isLoading: brief.isLoading,
    isEvolving: brief.isEvolving,
    isPolling: brief.isPolling,
    lastEvolvedAt: brief.lastEvolvedAt,
    lastEvolveDiff: brief.lastEvolveDiff,
    dismissEvolveDiff: brief.dismissEvolveDiff,
    error: brief.error,
    overallGrounding: brief.overallGrounding,
    blockingAnnotations: brief.blockingAnnotations,
    allSections: brief.allSections,
    statusCounts: brief.statusCounts,

    // Section CRUD (from useBrief)
    refresh: brief.refresh,
    addSection: brief.addSection,
    updateSection: brief.updateSection,
    deleteSection: brief.deleteSection,
    reorderSections: brief.reorderSections,
    linkToInquiry: brief.linkToInquiry,
    unlinkFromInquiry: brief.unlinkFromInquiry,
    dismissAnnotation: brief.dismissAnnotation,
    toggleCollapse: brief.toggleCollapse,
    evolveBrief: brief.evolveBrief,

    // ── Active Section Tracking ──────────────────────────────────
    activeSectionId,
    setActiveSectionId,
    activeSection,
    getSectionByMarker,
    getSectionById,
    getSectionAnnotations,
    sectionOrder,
    navigateSection,

    // ── AI Suggestions (from useBriefSuggestions) ────────────────
    suggestions: suggestions.suggestions,
    suggestionsLoading: suggestions.isLoading,
    isGenerating: suggestions.isGenerating,
    suggestionsError: suggestions.error,
    generateSuggestions: suggestions.generateSuggestions,
    acceptSuggestion: suggestions.acceptSuggestion,
    rejectSuggestion: suggestions.rejectSuggestion,
    acceptAllSuggestions: suggestions.acceptAllSuggestions,
    rejectAllSuggestions: suggestions.rejectAllSuggestions,
    clearSuggestions: suggestions.clearSuggestions,
    pendingCount: suggestions.pendingCount,
  };
}
