/**
 * useBrief — React hook for managing intelligent brief state.
 *
 * Fetches brief sections with annotations, provides CRUD operations,
 * triggers grounding recomputation, and auto-polls for background
 * evolve updates (e.g., from Django signal handlers / Celery tasks).
 */

'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { casesAPI } from '@/lib/api/cases';
import type {
  BriefSection,
  BriefSectionsResponse,
  CreateBriefSectionData,
  UpdateBriefSectionData,
  GroundingStatus,
  EvolveDiff,
} from '@/lib/types/case';

interface UseBriefOptions {
  caseId: string;
  /** Auto-fetch on mount. Defaults to true. */
  autoFetch?: boolean;
  /**
   * Polling interval in ms for detecting background evolve updates.
   * Set to 0 to disable polling. Defaults to 15000 (15 seconds).
   * Polling is only active after the first manual evolve or when
   * grounding data suggests an evolve may be in flight.
   */
  pollInterval?: number;
}

interface UseBriefReturn {
  /** All top-level sections (subsections nested within) */
  sections: BriefSection[];
  /** Brief document ID */
  briefId: string | null;
  /** Loading state */
  isLoading: boolean;
  /** Evolving state (grounding recomputation in progress) */
  isEvolving: boolean;
  /** Whether polling for background updates is active */
  isPolling: boolean;
  /** Timestamp of last detected grounding update */
  lastEvolvedAt: Date | null;
  /** Diff from the last evolve operation (what changed) */
  lastEvolveDiff: EvolveDiff | null;
  /** Dismiss the evolve diff banner */
  dismissEvolveDiff: () => void;
  /** Error message */
  error: string | null;

  // ── Actions ──────────────────────────────────────────────────

  /** Refresh sections from API */
  refresh: () => Promise<void>;
  /** Add a new section */
  addSection: (data: CreateBriefSectionData) => Promise<BriefSection | null>;
  /** Update a section's metadata */
  updateSection: (sectionId: string, data: UpdateBriefSectionData) => Promise<BriefSection | null>;
  /** Delete a section */
  deleteSection: (sectionId: string) => Promise<boolean>;
  /** Reorder sections */
  reorderSections: (order: Array<{ id: string; order: number }>) => Promise<void>;
  /** Link section to inquiry */
  linkToInquiry: (sectionId: string, inquiryId: string) => Promise<BriefSection | null>;
  /** Unlink section from inquiry */
  unlinkFromInquiry: (sectionId: string) => Promise<BriefSection | null>;
  /** Dismiss an annotation */
  dismissAnnotation: (sectionId: string, annotationId: string) => Promise<void>;
  /** Toggle section collapsed state */
  toggleCollapse: (sectionId: string, collapsed: boolean) => Promise<void>;
  /** Trigger grounding recomputation */
  evolveBrief: () => Promise<void>;

  // ── Computed ─────────────────────────────────────────────────

  /** Overall grounding score (0-100) based on section statuses */
  overallGrounding: number;
  /** Annotations with 'blocking' priority across all sections */
  blockingAnnotations: Array<{ sectionHeading: string; annotation: BriefSection['annotations'][0] }>;
  /** Flat list of all sections (including nested) */
  allSections: BriefSection[];
  /** Count of sections by grounding status */
  statusCounts: Record<GroundingStatus, number>;
}

/**
 * Build a lightweight fingerprint from sections' grounding data
 * to detect background changes without deep-comparing all fields.
 */
function buildGroundingFingerprint(sections: BriefSection[]): string {
  const parts: string[] = [];
  const collect = (sects: BriefSection[]) => {
    for (const s of sects) {
      parts.push(`${s.id}:${s.grounding_status}:${s.annotations.length}:${s.updated_at}`);
      if (s.subsections?.length) collect(s.subsections);
    }
  };
  collect(sections);
  return parts.join('|');
}

export function useBrief({
  caseId,
  autoFetch = true,
  pollInterval = 15000,
}: UseBriefOptions): UseBriefReturn {
  const [sections, setSections] = useState<BriefSection[]>([]);
  const [briefId, setBriefId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isEvolving, setIsEvolving] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [lastEvolvedAt, setLastEvolvedAt] = useState<Date | null>(null);
  const [lastEvolveDiff, setLastEvolveDiff] = useState<EvolveDiff | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Track whether polling should be active
  // Polling activates after an evolve (manual or background) and
  // deactivates after a stable period with no changes.
  const [pollActive, setPollActive] = useState(false);
  const pollStableCountRef = useRef(0); // Consecutive polls with no change
  const pollFailureCountRef = useRef(0); // Consecutive poll failures
  const groundingFingerprintRef = useRef<string>('');

  // ── Fetch ──────────────────────────────────────────────────────

  const refresh = useCallback(async () => {
    if (!caseId) return;
    setIsLoading(true);
    setError(null);
    try {
      const response: BriefSectionsResponse = await casesAPI.getBriefSections(caseId);
      setSections(response.sections);
      setBriefId(response.brief_id);
      // Update fingerprint
      groundingFingerprintRef.current = buildGroundingFingerprint(response.sections);

      // Auto-activate polling if any sections are linked to inquiries
      // (which means grounding may update in the background via Django signals)
      const hasLinkedSections = response.sections.some(
        (s: BriefSection) => s.is_linked || s.inquiry
      );
      if (hasLinkedSections && !pollActive) {
        pollStableCountRef.current = 0;
        setPollActive(true);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load brief sections');
      // Not an error if case just has no sections yet
      if (typeof err === 'object' && err !== null && 'status' in err && (err as { status: number }).status === 404) {
        setSections([]);
        setError(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, [caseId, pollActive]);

  useEffect(() => {
    if (autoFetch) {
      refresh();
    }
  }, [autoFetch, refresh]);

  // ── Background polling ────────────────────────────────────────
  //
  // After an evolve (manual or background), poll the brief overview
  // endpoint at a lightweight interval to detect grounding changes.
  // Stops after 3 consecutive polls with no change.

  useEffect(() => {
    if (!pollActive || !caseId || pollInterval <= 0) return;

    setIsPolling(true);
    const intervalId = setInterval(async () => {
      try {
        const response: BriefSectionsResponse = await casesAPI.getBriefSections(caseId);
        const newFingerprint = buildGroundingFingerprint(response.sections);

        if (newFingerprint !== groundingFingerprintRef.current) {
          // Grounding changed — update state
          setSections(response.sections);
          setBriefId(response.brief_id);
          groundingFingerprintRef.current = newFingerprint;
          setLastEvolvedAt(new Date());
          pollStableCountRef.current = 0; // Reset stable counter
        } else {
          // No change detected
          pollStableCountRef.current += 1;
          // Stop polling after 3 stable checks (~45 seconds of no change)
          if (pollStableCountRef.current >= 3) {
            setPollActive(false);
          }
        }
        // Reset failure counter on success
        pollFailureCountRef.current = 0;
      } catch {
        // Polling is best-effort, but stop after repeated failures
        // to avoid hammering a down server
        pollFailureCountRef.current += 1;
        if (pollFailureCountRef.current >= 3) {
          setPollActive(false);
          console.warn('[useBrief] Polling stopped after 3 consecutive failures');
        }
      }
    }, pollInterval);

    return () => {
      clearInterval(intervalId);
      setIsPolling(false);
    };
  }, [pollActive, caseId, pollInterval]);

  // ── CRUD Actions ───────────────────────────────────────────────

  const addSection = useCallback(async (data: CreateBriefSectionData): Promise<BriefSection | null> => {
    try {
      const section = await casesAPI.createBriefSection(caseId, data);
      await refresh();
      return section;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to add section');
      return null;
    }
  }, [caseId, refresh]);

  const updateSection = useCallback(async (
    sectionId: string,
    data: UpdateBriefSectionData
  ): Promise<BriefSection | null> => {
    try {
      const section = await casesAPI.updateBriefSection(caseId, sectionId, data);
      // Optimistic update
      setSections(prev => prev.map(s =>
        s.id === sectionId ? { ...s, ...section } : s
      ));
      return section;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update section');
      return null;
    }
  }, [caseId]);

  const deleteSection = useCallback(async (sectionId: string): Promise<boolean> => {
    try {
      await casesAPI.deleteBriefSection(caseId, sectionId);
      setSections(prev => prev.filter(s => s.id !== sectionId));
      return true;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete section');
      return false;
    }
  }, [caseId]);

  const reorderSections = useCallback(async (
    order: Array<{ id: string; order: number }>
  ) => {
    try {
      // Optimistic reorder
      const orderMap = new Map(order.map(o => [o.id, o.order]));
      setSections(prev =>
        [...prev].sort((a, b) =>
          (orderMap.get(a.id) ?? a.order) - (orderMap.get(b.id) ?? b.order)
        )
      );
      await casesAPI.reorderBriefSections(caseId, order);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to reorder sections');
      await refresh(); // Revert on error
    }
  }, [caseId, refresh]);

  const linkToInquiry = useCallback(async (
    sectionId: string,
    inquiryId: string
  ): Promise<BriefSection | null> => {
    try {
      const section = await casesAPI.linkSectionToInquiry(caseId, sectionId, inquiryId);
      await refresh();
      // Linking triggers grounding recomputation server-side, so start polling
      pollStableCountRef.current = 0;
      setPollActive(true);
      return section;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to link inquiry');
      return null;
    }
  }, [caseId, refresh]);

  const unlinkFromInquiry = useCallback(async (sectionId: string): Promise<BriefSection | null> => {
    try {
      const section = await casesAPI.unlinkSectionFromInquiry(caseId, sectionId);
      await refresh();
      return section;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to unlink inquiry');
      return null;
    }
  }, [caseId, refresh]);

  const toggleCollapse = useCallback(async (sectionId: string, collapsed: boolean) => {
    // Optimistic update
    const updateCollapse = (sects: BriefSection[]): BriefSection[] =>
      sects.map(s => ({
        ...s,
        is_collapsed: s.id === sectionId ? collapsed : s.is_collapsed,
        subsections: s.subsections ? updateCollapse(s.subsections) : s.subsections,
      }));
    setSections(prev => updateCollapse(prev));
    try {
      await casesAPI.updateBriefSection(caseId, sectionId, { is_collapsed: collapsed });
    } catch (err: unknown) {
      // Revert on error
      setSections(prev => updateCollapse(prev).map(s => ({
        ...s,
        is_collapsed: s.id === sectionId ? !collapsed : s.is_collapsed,
      })));
      setError(err instanceof Error ? err.message : 'Failed to toggle section');
    }
  }, [caseId]);

  const dismissAnnotation = useCallback(async (sectionId: string, annotationId: string) => {
    try {
      await casesAPI.dismissAnnotation(caseId, sectionId, annotationId);
      // Optimistic: remove annotation from local state
      setSections(prev => prev.map(s => {
        if (s.id === sectionId) {
          return {
            ...s,
            annotations: s.annotations.filter(a => a.id !== annotationId),
          };
        }
        return s;
      }));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to dismiss annotation');
    }
  }, [caseId]);

  const evolveBrief = useCallback(async () => {
    setIsEvolving(true);
    try {
      const response = await casesAPI.evolveBrief(caseId);
      await refresh();
      setLastEvolvedAt(new Date());
      // Capture the diff if the backend returned one
      if (response.diff) {
        // Merge readiness counts from top-level response into the diff object
        const diff = {
          ...response.diff,
          readiness_created: response.readiness_created ?? 0,
          readiness_auto_completed: response.readiness_auto_completed ?? 0,
        };
        const hasChanges =
          diff.section_changes.length > 0 ||
          diff.new_annotations.length > 0 ||
          diff.resolved_annotations.length > 0 ||
          (diff.readiness_created ?? 0) > 0 ||
          (diff.readiness_auto_completed ?? 0) > 0;
        if (hasChanges) {
          setLastEvolveDiff(diff);
        }
      }
      // Start polling in case background tasks also trigger further updates
      pollStableCountRef.current = 0;
      pollFailureCountRef.current = 0;
      setPollActive(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to evolve brief');
    } finally {
      setIsEvolving(false);
    }
  }, [caseId, refresh]);

  const dismissEvolveDiff = useCallback(() => {
    setLastEvolveDiff(null);
  }, []);

  // ── Computed Values ────────────────────────────────────────────

  const allSections = useMemo((): BriefSection[] => {
    const flat: BriefSection[] = [];
    const flatten = (sects: BriefSection[]) => {
      for (const s of sects) {
        flat.push(s);
        if (s.subsections?.length) {
          flatten(s.subsections);
        }
      }
    };
    flatten(sections);
    return flat;
  }, [sections]);

  const statusCounts = useMemo((): Record<GroundingStatus, number> => {
    const counts: Record<GroundingStatus, number> = {
      empty: 0,
      weak: 0,
      moderate: 0,
      strong: 0,
      conflicted: 0,
    };
    for (const s of allSections) {
      counts[s.grounding_status] = (counts[s.grounding_status] || 0) + 1;
    }
    return counts;
  }, [allSections]);

  const overallGrounding = useMemo((): number => {
    if (allSections.length === 0) return 0;
    const scoreMap: Record<GroundingStatus, number> = {
      strong: 100,
      moderate: 60,
      weak: 30,
      conflicted: 20,
      empty: 0,
    };
    const total = allSections.reduce(
      (sum, s) => sum + (scoreMap[s.grounding_status] || 0),
      0
    );
    return Math.round(total / allSections.length);
  }, [allSections]);

  const blockingAnnotations = useMemo(() => {
    const blocking: Array<{ sectionHeading: string; annotation: BriefSection['annotations'][0] }> = [];
    for (const s of allSections) {
      for (const a of s.annotations) {
        if (a.priority === 'blocking') {
          blocking.push({ sectionHeading: s.heading, annotation: a });
        }
      }
    }
    return blocking;
  }, [allSections]);

  return {
    sections,
    briefId,
    isLoading,
    isEvolving,
    isPolling,
    lastEvolvedAt,
    lastEvolveDiff,
    dismissEvolveDiff,
    error,
    refresh,
    addSection,
    updateSection,
    deleteSection,
    reorderSections,
    linkToInquiry,
    unlinkFromInquiry,
    dismissAnnotation,
    toggleCollapse,
    evolveBrief,
    overallGrounding,
    blockingAnnotations,
    allSections,
    statusCounts,
  };
}
