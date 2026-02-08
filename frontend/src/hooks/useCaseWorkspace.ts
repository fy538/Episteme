/**
 * useCaseWorkspace Hook
 *
 * Extracts the 14 useState calls from the case workspace page into organized groups:
 * - Data state: case, brief, inquiries, allCases, projects, threadId, loading
 * - UI state: settingsOpen, viewMode, activeInquiryId
 * - Integration/checklist: integrationPreview, checklistItems, checklistProgress
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { documentsAPI } from '@/lib/api/documents';
import { chatAPI } from '@/lib/api/chat';
import { projectsAPI } from '@/lib/api/projects';
import { plansAPI } from '@/lib/api/plans';
import { useChatMode } from '@/hooks/useChatMode';
import { useCompanionState } from '@/hooks/useCompanionState';
import type { Case, CaseDocument, Inquiry } from '@/lib/types/case';
import type { Project } from '@/lib/types/project';
import type { CompanionState } from '@/lib/types/companion';
import type { InvestigationPlan, PlanAssumption } from '@/lib/types/plan';
import type { ReadinessChecklistItemData, ChecklistProgress } from '@/components/readiness';

export type ViewMode = 'home' | 'brief' | 'inquiry' | 'inquiry-dashboard' | 'readiness' | 'document';

interface UseCaseWorkspaceOptions {
  caseId: string;
}

export function useCaseWorkspace({ caseId }: UseCaseWorkspaceOptions) {
  const router = useRouter();

  // --- Data state ---
  const [caseData, setCase] = useState<Case | null>(null);
  const [brief, setBrief] = useState<CaseDocument | null>(null);
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [plan, setPlan] = useState<InvestigationPlan | null>(null);
  const [allCases, setAllCases] = useState<Case[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [threadId, setThreadId] = useState<string>('');
  const [loading, setLoading] = useState(true);

  // --- UI state ---
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('home');
  const [activeInquiryId, setActiveInquiryId] = useState<string | null>(null);

  // --- Nav collapse state (persisted) ---
  const [isNavCollapsed, setIsNavCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('episteme_case_nav_collapsed') === 'true';
    }
    return false;
  });

  // --- Chat panel collapse state (persisted) ---
  const [isChatCollapsed, setIsChatCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('episteme_chat_collapsed') === 'true';
    }
    return false;
  });

  // --- Integration preview ---
  const [integrationPreview, setIntegrationPreview] = useState<Record<string, unknown> | null>(null);

  // --- Readiness checklist ---
  const [checklistItems, setChecklistItems] = useState<ReadinessChecklistItemData[]>([]);
  const [checklistProgress, setChecklistProgress] = useState<ChecklistProgress>({
    completed: 0,
    required: 0,
    required_completed: 0,
    total: 0,
  });

  // --- Chat mode ---
  const chatMode = useChatMode({
    threadId: threadId || null,
    initialCaseId: caseId,
    initialCaseName: caseData?.title,
  });

  // Track signal count to auto-generate receipts
  const prevSignalCountRef = useRef(0);

  // --- Companion state (unified hook) ---
  const companion = useCompanionState({
    mode: chatMode.mode.mode,
    onMessageComplete: () => {
      // Auto-receipt when new signals were extracted during this message
      const newCount = companion.signals.length;
      if (newCount > prevSignalCountRef.current) {
        const delta = newCount - prevSignalCountRef.current;
        companion.addReceipt({
          id: `receipt-signals-${Date.now()}`,
          type: 'signals_extracted',
          title: `${delta} signal${delta > 1 ? 's' : ''} extracted`,
          timestamp: new Date().toISOString(),
          relatedCaseId: caseId,
        });
        prevSignalCountRef.current = newCount;
      }
    },
  });

  // Sync case state into companion whenever case data, inquiries, or plan change
  useEffect(() => {
    if (caseData) {
      // Compute real assumption counts from plan data
      const planAssumptions: PlanAssumption[] = plan?.current_content?.assumptions ?? [];
      const validated = planAssumptions.filter(
        (a) => a.status === 'confirmed'
      ).length;
      const unvalidated = planAssumptions.filter(
        (a) => a.status === 'untested' || a.status === 'challenged'
      ).length;
      const evidenceGaps = planAssumptions.filter(
        (a) => a.status === 'untested' && !a.evidence_summary
      ).length;

      companion.setCaseState({
        caseId: caseData.id,
        caseName: caseData.title,
        inquiries: {
          open: inquiries.filter(i => i.status === 'open').length,
          resolved: inquiries.filter(i => i.status === 'resolved').length,
        },
        assumptions: { validated, unvalidated },
        evidenceGaps,
      });
    } else {
      companion.setCaseState(undefined);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseData?.id, caseData?.title, inquiries, plan]);

  // Build CompanionState from pieces
  const companionState: CompanionState = {
    mode: chatMode.mode,
    thinking: companion.companionThinking,
    status: companion.status,
    sessionReceipts: companion.sessionReceipts,
    caseState: companion.caseState,
  };

  // Load workspace data
  const loadWorkspace = useCallback(async () => {
    setLoading(true);
    try {
      const [caseResp, inqs, docs, allCasesResp] = await Promise.all([
        casesAPI.getCase(caseId),
        inquiriesAPI.getByCase(caseId),
        documentsAPI.getByCase(caseId),
        casesAPI.listCases(),
      ]);

      setCase(caseResp);
      setInquiries(inqs);
      setAllCases(allCasesResp);

      // Find main brief
      const mainBrief = docs.find(d => d.id === caseResp.main_brief);
      setBrief(mainBrief || null);

      // Get or create thread for this case
      if (caseResp.linked_thread) {
        setThreadId(caseResp.linked_thread);
      } else {
        const thread = await chatAPI.createThread(null, { title: `Chat: ${caseResp.title}` });
        setThreadId(thread.id);
        await chatAPI.updateThread(thread.id, { primary_case: caseResp.id });
        await casesAPI.updateCase(caseResp.id, { linked_thread: thread.id });
      }

      // Load plan (may not exist for new cases)
      try {
        const planResp = await plansAPI.getPlan(caseId);
        setPlan(planResp);
      } catch (error) {
        // Plan may not exist yet — that's fine
        setPlan(null);
      }

      // Load projects
      try {
        const projectsResp = await projectsAPI.listProjects();
        setProjects(projectsResp);
      } catch (error) {
        console.error('Failed to load projects:', error);
        setProjects([]);
      }

      // Load readiness checklist
      await loadChecklist();
    } catch (error) {
      console.error('Failed to load workspace:', error);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  // Load checklist
  const loadChecklist = useCallback(async () => {
    try {
      const response = await fetch(`/api/cases/${caseId}/readiness-checklist/`);
      if (!response.ok) throw new Error('Failed to load checklist');

      const data = await response.json();
      setChecklistItems(data.items || []);
      setChecklistProgress(data.progress || {
        completed: 0,
        required: 0,
        required_completed: 0,
        total: 0,
      });
    } catch (error) {
      console.error('Failed to load checklist:', error);
    }
  }, [caseId]);

  // Initial load
  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  // --- Actions ---
  const handleCreateCase = useCallback(async () => {
    try {
      const newCase = await casesAPI.createCase('New Case');
      router.push(`/cases/${newCase.case.id}`);
    } catch (error) {
      console.error('Failed to create case:', error);
    }
  }, [router]);

  const handleStartInquiry = useCallback(async () => {
    if (!caseData) return;

    try {
      const inquiry = await inquiriesAPI.create({
        case: caseData.id,
        title: 'New Inquiry',
        status: 'open',
      });

      setActiveInquiryId(inquiry.id);
      setViewMode('inquiry');
      await loadWorkspace();
    } catch (error) {
      console.error('Failed to create inquiry:', error);
    }
  }, [caseData, loadWorkspace]);

  const handleOpenInquiry = useCallback((inquiryId: string) => {
    setActiveInquiryId(inquiryId);
    setViewMode('inquiry');

    // Transition chat mode to inquiry_focus
    const inquiry = inquiries.find(i => i.id === inquiryId);
    if (inquiry) {
      chatMode.focusOnInquiry(inquiryId, inquiry.title);
    }

    // Clear reflection from previous context
    companion.clearReflection();
  }, [inquiries, chatMode, companion]);

  const handleViewHome = useCallback(() => {
    setViewMode('home');
    setActiveInquiryId(null);

    // Transition chat mode back to case
    chatMode.exitFocus();

    // Clear reflection from previous context
    companion.clearReflection();
  }, [chatMode, companion]);

  const toggleNav = useCallback(() => {
    setIsNavCollapsed(prev => {
      const next = !prev;
      if (typeof window !== 'undefined') {
        localStorage.setItem('episteme_case_nav_collapsed', String(next));
      }
      return next;
    });
  }, []);

  const toggleChat = useCallback(() => {
    setIsChatCollapsed(prev => {
      const next = !prev;
      if (typeof window !== 'undefined') {
        localStorage.setItem('episteme_chat_collapsed', String(next));
      }
      return next;
    });
  }, []);

  // Focus mode: collapse both nav and chat, or expand both
  const isFocusMode = isNavCollapsed && isChatCollapsed;

  const toggleFocusMode = useCallback(() => {
    const enterFocus = !isNavCollapsed || !isChatCollapsed;
    setIsNavCollapsed(enterFocus);
    setIsChatCollapsed(enterFocus);
    if (typeof window !== 'undefined') {
      localStorage.setItem('episteme_case_nav_collapsed', String(enterFocus));
      localStorage.setItem('episteme_chat_collapsed', String(enterFocus));
    }
  }, [isNavCollapsed, isChatCollapsed]);

  const handleViewBrief = useCallback(() => {
    setViewMode('brief');
    setActiveInquiryId(null);

    // Transition chat mode back to case
    chatMode.exitFocus();

    // Clear reflection from previous context
    companion.clearReflection();
  }, [chatMode, companion]);

  // Derived state
  const activeInquiry = activeInquiryId
    ? inquiries.find(i => i.id === activeInquiryId) || null
    : null;

  return {
    // Data
    caseData,
    brief,
    inquiries,
    plan,
    allCases,
    projects,
    threadId,
    loading,

    // UI
    settingsOpen,
    setSettingsOpen,
    viewMode,
    setViewMode,
    activeInquiryId,
    activeInquiry,
    isNavCollapsed,
    toggleNav,
    isChatCollapsed,
    toggleChat,
    isFocusMode,
    toggleFocusMode,

    // Integration
    integrationPreview,
    setIntegrationPreview,

    // Checklist
    checklistItems,
    checklistProgress,

    // Chat mode + companion
    chatMode,
    companionState,
    streamCallbacks: companion.streamCallbacks,
    actionHints: companion.actionHints,
    signals: companion.signals,
    companionPosition: companion.companionPosition,
    setCompanionPosition: companion.setCompanionPosition,
    toggleCompanion: companion.toggleCompanion,
    rankedSections: companion.rankedSections,
    pinnedSection: companion.pinnedSection,
    setPinnedSection: companion.setPinnedSection,
    addReceipt: companion.addReceipt,
    addBackgroundWork: companion.addBackgroundWork,
    completeBackgroundWork: companion.completeBackgroundWork,
    dismissCompleted: companion.dismissCompleted,

    // Actions
    loadWorkspace,
    loadChecklist,
    handleCreateCase,
    handleStartInquiry,
    handleOpenInquiry,
    handleViewHome,
    handleViewBrief,
  };
}
