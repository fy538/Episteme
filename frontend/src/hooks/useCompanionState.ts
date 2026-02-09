/**
 * useCompanionState — Unified companion state for all chat contexts.
 *
 * Manages:
 * - Reflection/thinking state (streaming + completed)
 * - Action hints from AI responses
 * - Session receipts and background work
 * - Companion panel position (sidebar/bottom/hidden, localStorage-persisted)
 * - Section ranking (priority-based adaptive display)
 * - Section pinning (user override)
 */

import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import type { ActionHint } from '@/lib/types/chat';
import type { ChatMode, BackgroundWorkItem, SessionReceipt, CaseState } from '@/lib/types/companion';
import type { StreamingCallbacks } from '@/lib/types/streaming';
import { rankSections, type CompanionSectionId } from '@/lib/utils/companion-ranking';

export type CompanionPosition = 'sidebar' | 'bottom' | 'hidden';

const STORAGE_KEY = 'episteme_companion_position';

export interface UseCompanionStateOptions {
  mode: ChatMode;
  /** Consumer-specific logic to run on message completion */
  onMessageComplete?: (messageId?: string) => void;
}

export interface CompanionThinking {
  content: string;
  isStreaming: boolean;
}

export interface UseCompanionStateReturn {
  streamCallbacks: StreamingCallbacks;
  companionThinking: CompanionThinking;
  actionHints: ActionHint[];
  clearReflection: () => void;
  // Status & receipts
  status: { inProgress: BackgroundWorkItem[]; justCompleted: BackgroundWorkItem[] };
  sessionReceipts: SessionReceipt[];
  addReceipt: (receipt: SessionReceipt) => void;
  addBackgroundWork: (item: BackgroundWorkItem) => void;
  completeBackgroundWork: (id: string) => void;
  dismissCompleted: (id: string) => void;
  // Case state (set by consumer)
  caseState: CaseState | undefined;
  setCaseState: (state: CaseState | undefined) => void;
  // Position
  companionPosition: CompanionPosition;
  setCompanionPosition: (pos: CompanionPosition) => void;
  toggleCompanion: () => void;
  // Ranking
  rankedSections: CompanionSectionId[];
  pinnedSection: CompanionSectionId | null;
  setPinnedSection: (id: CompanionSectionId | null) => void;
}

export function useCompanionState({
  mode,
  onMessageComplete,
}: UseCompanionStateOptions): UseCompanionStateReturn {
  // --- Core state ---
  const [reflection, setReflection] = useState('');
  const [isReflectionStreaming, setIsReflectionStreaming] = useState(false);
  const [actionHints, setActionHints] = useState<ActionHint[]>([]);

  // --- Status & receipts ---
  const [backgroundWork, setBackgroundWork] = useState<BackgroundWorkItem[]>([]);
  const [sessionReceipts, setSessionReceipts] = useState<SessionReceipt[]>([]);
  const [caseState, setCaseState] = useState<CaseState | undefined>(undefined);

  // --- Position (SSR-safe: default to sidebar, read localStorage in effect) ---
  const [companionPosition, setPositionState] = useState<CompanionPosition>('sidebar');

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === 'sidebar' || saved === 'bottom' || saved === 'hidden') {
        setPositionState(saved);
      }
    } catch {
      // SSR or localStorage unavailable
    }
  }, []);

  const setCompanionPosition = useCallback((pos: CompanionPosition) => {
    setPositionState(pos);
    try {
      localStorage.setItem(STORAGE_KEY, pos);
    } catch {
      // ignore
    }
  }, []);

  const toggleCompanion = useCallback(() => {
    setPositionState(prev => {
      const next = prev === 'hidden' ? 'sidebar' : 'hidden';
      try { localStorage.setItem(STORAGE_KEY, next); } catch { /* ignore */ }
      return next;
    });
  }, []);

  // --- Pinning ---
  const [pinnedSection, setPinnedSection] = useState<CompanionSectionId | null>(null);

  // --- Last-updated tracking for ranking ---
  // Ref stores the actual timestamps; counter state triggers re-ranking.
  const lastUpdatedRef = useRef<Partial<Record<CompanionSectionId, number>>>({});
  const [rankingEpoch, setRankingEpoch] = useState(0);

  const markUpdated = useCallback((section: CompanionSectionId) => {
    lastUpdatedRef.current[section] = Date.now();
    setRankingEpoch(e => e + 1);
  }, []);

  // Ref for onMessageComplete to keep streamCallbacks stable
  const onMessageCompleteRef = useRef(onMessageComplete);
  onMessageCompleteRef.current = onMessageComplete;

  const clearReflection = useCallback(() => {
    setReflection('');
    setIsReflectionStreaming(false);
  }, []);

  // --- Status & receipts methods ---
  const addReceipt = useCallback((receipt: SessionReceipt) => {
    setSessionReceipts(prev => [receipt, ...prev]);
    markUpdated('receipts');
  }, [markUpdated]);

  const addBackgroundWork = useCallback((item: BackgroundWorkItem) => {
    setBackgroundWork(prev => [...prev, item]);
    markUpdated('status');
  }, [markUpdated]);

  const completeBackgroundWork = useCallback((id: string) => {
    setBackgroundWork(prev => prev.map(item =>
      item.id === id ? { ...item, status: 'completed' as const, completedAt: new Date().toISOString() } : item
    ));
    markUpdated('status');
  }, [markUpdated]);

  const dismissCompleted = useCallback((id: string) => {
    setBackgroundWork(prev => prev.filter(item => item.id !== id));
  }, []);

  // Derive status from backgroundWork
  const status = useMemo(() => ({
    inProgress: backgroundWork.filter(w => w.status === 'running'),
    justCompleted: backgroundWork.filter(w => w.status === 'completed'),
  }), [backgroundWork]);

  // Stable callbacks — no deps that change per render.
  // markUpdated is stable (useCallback with []), so it's safe in the dep array.
  const streamCallbacks: StreamingCallbacks = useMemo(() => ({
    onReflectionChunk: (delta: string) => {
      setReflection(prev => prev + delta);
      setIsReflectionStreaming(true);
      markUpdated('thinking');
    },
    onReflectionComplete: (content: string) => {
      setReflection(content);
      setIsReflectionStreaming(false);
      markUpdated('thinking');
    },
    onActionHints: (hints: ActionHint[]) => {
      setActionHints(hints);
      markUpdated('action_hints');
    },
    onMessageComplete: (messageId?: string) => {
      onMessageCompleteRef.current?.(messageId);
    },
  }), [markUpdated]);

  const companionThinking: CompanionThinking = useMemo(() => ({
    content: reflection,
    isStreaming: isReflectionStreaming,
  }), [reflection, isReflectionStreaming]);

  // --- Section ranking (recomputed on state changes + ranking epoch) ---
  const rankedSections = useMemo(() => rankSections({
    thinking: { content: reflection, isStreaming: isReflectionStreaming },
    actionHints,
    status,
    sessionReceipts,
    caseState,
    mode,
    pinnedSection,
    lastUpdated: lastUpdatedRef.current,
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [reflection, isReflectionStreaming, actionHints, status, sessionReceipts, caseState, mode, pinnedSection, rankingEpoch]);

  return {
    streamCallbacks,
    companionThinking,
    actionHints,
    clearReflection,
    status,
    sessionReceipts,
    addReceipt,
    addBackgroundWork,
    completeBackgroundWork,
    dismissCompleted,
    caseState,
    setCaseState,
    companionPosition,
    setCompanionPosition,
    toggleCompanion,
    rankedSections,
    pinnedSection,
    setPinnedSection,
  };
}
