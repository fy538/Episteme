/**
 * UnifiedBriefView — The single, unified brief experience.
 *
 * Replaces both CaseBriefView (free-form editor) and IntelligentBrief (section cards)
 * with a single view where writing and structural intelligence coexist.
 *
 * Layout:
 *   [Outline + Context (left)] | [Decision Frame + Grounding Header + Editor (center)]
 *
 * The chat panel lives outside this component (in the workspace page right column).
 */

'use client';

import { useState, useCallback, useMemo, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import dynamic from 'next/dynamic';

const BriefEditor = dynamic(
  () => import('@/components/editor/BriefEditor').then(mod => mod.BriefEditor),
  { ssr: false, loading: () => <div className="p-8 text-neutral-400 animate-pulse">Loading editor...</div> }
);

import { BriefOutlineNav } from '@/components/editor/BriefOutlineNav';
import { SectionContextPanel } from '@/components/editor/SectionContextPanel';
import { DecisionFrameHeader } from '@/components/editor/DecisionFrameHeader';
import { WordDiff } from '@/components/editor/WordDiff';
import { useBriefEditor } from '@/hooks/useBriefEditor';
import { documentsAPI } from '@/lib/api/documents';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { signalsAPI } from '@/lib/api/signals';
import {
  GROUNDING_SUMMARY,
  getGroundingScoreColor,
  getGroundingScoreStrokeColor,
} from '@/lib/constants/grounding';
import type { Case, CaseDocument, Inquiry, GroundingStatus } from '@/lib/types/case';

interface UnifiedBriefViewProps {
  caseData: Case;
  brief: CaseDocument | null;
  inquiries: Inquiry[];
  onStartInquiry: () => void;
  onOpenInquiry: (inquiryId: string) => void;
  onRefresh: () => void;
  /** 'embedded' = within workspace (default), 'focused' = full page mode */
  variant?: 'embedded' | 'focused';
}

export function UnifiedBriefView({
  caseData,
  brief,
  inquiries,
  onStartInquiry,
  onOpenInquiry,
  onRefresh,
  variant = 'embedded',
}: UnifiedBriefViewProps) {
  // ── Unified state from useBriefEditor ──────────────────────────
  const editor = useBriefEditor({
    caseId: caseData.id,
    documentId: brief?.id || '',
    onContentUpdate: () => onRefresh(),
  });

  // ── Local UI state ─────────────────────────────────────────────
  const [showOutline, setShowOutline] = useState(true);
  const [showVersionDiff, setShowVersionDiff] = useState(false);
  const [versionDiffData, setVersionDiffData] = useState<{ oldContent: string; newContent: string } | null>(null);
  const [loadingVersionDiff, setLoadingVersionDiff] = useState(false);
  const [briefToast, setBriefToast] = useState<string | null>(null);

  // ── Mark as Assumption handler ─────────────────────────────────
  const handleMarkAssumption = useCallback(async (text: string) => {
    try {
      await signalsAPI.markAssumption(text, caseData.id);
      setBriefToast('Assumption marked');
      setTimeout(() => setBriefToast(null), 3000);
    } catch (error) {
      console.error('Failed to mark assumption:', error);
      setBriefToast('Failed to mark assumption');
      setTimeout(() => setBriefToast(null), 3000);
    }
  }, [caseData.id]);

  // ── Keyboard shortcuts ────────────────────────────────────────
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const isMod = e.metaKey || e.ctrlKey;

      // Cmd+Shift+O — Toggle outline panel
      if (isMod && e.shiftKey && e.key === 'o') {
        e.preventDefault();
        setShowOutline(prev => !prev);
        return;
      }

      // Cmd+Shift+E — Trigger evolve
      if (isMod && e.shiftKey && e.key === 'e') {
        e.preventDefault();
        if (!editor.isEvolving) {
          editor.evolveBrief();
        }
        return;
      }

      // Cmd+J — Next section
      if (isMod && !e.shiftKey && e.key === 'j') {
        e.preventDefault();
        editor.navigateSection('next');
        return;
      }

      // Cmd+Shift+J — Previous section
      if (isMod && e.shiftKey && e.key === 'j') {
        e.preventDefault();
        editor.navigateSection('prev');
        return;
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [editor]);

  // ── Handlers ───────────────────────────────────────────────────

  const handleSectionClick = useCallback((sectionId: string) => {
    editor.setActiveSectionId(sectionId);
  }, [editor]);

  const handleCreateInquiryFromSection = useCallback(async (title: string, sectionId: string) => {
    try {
      const inquiry = await inquiriesAPI.create({
        case: caseData.id,
        title,
        status: 'open',
      });
      // Link the section to the inquiry
      await editor.linkToInquiry(sectionId, inquiry.id);
      onOpenInquiry(inquiry.id);
    } catch (error) {
      console.error('Failed to create inquiry from section:', error);
    }
  }, [caseData.id, editor, onOpenInquiry]);

  const handleCreateInquiryFromText = useCallback(async (selectedText: string) => {
    if (!brief) return;
    try {
      const { title } = await inquiriesAPI.generateTitle(selectedText);
      const inquiry = await inquiriesAPI.create({
        case: caseData.id,
        title,
        description: `Validate: "${selectedText}"`,
        origin_text: selectedText,
        origin_document: brief.id,
        status: 'open',
      });
      onOpenInquiry(inquiry.id);
    } catch (error) {
      console.error('Failed to create inquiry:', error);
    }
  }, [caseData.id, brief, onOpenInquiry]);

  const handleViewChanges = useCallback(async () => {
    if (!editor.briefId) return;
    setLoadingVersionDiff(true);
    setShowVersionDiff(true);
    try {
      const versions = await documentsAPI.getVersionHistoryWithContent(editor.briefId);
      if (versions.length >= 2) {
        setVersionDiffData({
          oldContent: versions[1]?.content_markdown || '',
          newContent: versions[0]?.content_markdown || '',
        });
      } else {
        setVersionDiffData(null);
      }
    } catch {
      setVersionDiffData(null);
    } finally {
      setLoadingVersionDiff(false);
    }
  }, [editor.briefId]);

  // ── Grounding header ──────────────────────────────────────────
  const scoreColor = getGroundingScoreColor(editor.overallGrounding);
  const strokeColor = getGroundingScoreStrokeColor(editor.overallGrounding);

  // ── No brief state ────────────────────────────────────────────
  if (!brief) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <p className="text-neutral-500 dark:text-neutral-400 mb-4">No brief found for this case.</p>
          <p className="text-sm text-neutral-400 dark:text-neutral-500">
            A brief will be auto-generated when the case is created.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Decision Frame Header (collapsible) */}
      <DecisionFrameHeader
        caseData={caseData}
        onRefresh={onRefresh}
      />

      {/* Grounding Header Bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950">
        <div className="flex items-center gap-3">
          {/* Grounding score ring */}
          <div className="relative w-9 h-9 flex items-center justify-center">
            <svg className="w-9 h-9 -rotate-90" viewBox="0 0 36 36">
              <circle
                cx="18" cy="18" r="15"
                fill="none"
                className="stroke-neutral-200 dark:stroke-neutral-700"
                strokeWidth="3"
              />
              <circle
                cx="18" cy="18" r="15"
                fill="none"
                className={strokeColor}
                strokeWidth="3"
                strokeDasharray={`${editor.overallGrounding * 0.942} 94.2`}
                strokeLinecap="round"
              />
            </svg>
            <span className={cn('absolute text-[10px] font-bold', scoreColor)}>
              {editor.overallGrounding}
            </span>
          </div>

          {/* Status breakdown */}
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-primary-900 dark:text-primary-50">
                Grounding
              </span>
              {editor.isPolling && (
                <span className="flex items-center gap-1 text-[10px] text-accent-500">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-500" />
                  </span>
                  Updating
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              {(Object.entries(editor.statusCounts) as [GroundingStatus, number][])
                .filter(([_, count]) => count > 0)
                .map(([status, count]) => (
                  <span
                    key={status}
                    className={cn('flex items-center gap-0.5 text-[10px]', GROUNDING_SUMMARY[status].color)}
                  >
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-current" />
                    {count} {GROUNDING_SUMMARY[status].label.toLowerCase()}
                  </span>
                ))}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => setShowOutline(!showOutline)}
          >
            {showOutline ? 'Hide' : 'Show'} Outline
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={editor.evolveBrief}
            disabled={editor.isEvolving}
          >
            {editor.isEvolving ? (
              <>
                <LoadingSpinner className="w-3 h-3 mr-1" />
                Evolving...
              </>
            ) : (
              <>
                <EvolveIcon className="w-3 h-3 mr-1" />
                Evolve
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Evolve diff banner */}
      {editor.lastEvolveDiff && (
        <EvolveDiffBanner
          diff={editor.lastEvolveDiff}
          onDismiss={editor.dismissEvolveDiff}
          onViewChanges={editor.briefId ? handleViewChanges : undefined}
        />
      )}

      {/* Main content area */}
      <div className="flex flex-1 min-h-0">
        {/* Left panel: Outline + Context */}
        {showOutline && (
          <aside className="w-56 border-r border-neutral-200 dark:border-neutral-800 flex flex-col overflow-hidden shrink-0 bg-neutral-50/30 dark:bg-neutral-900/30">
            {/* Outline */}
            <div className="flex-shrink-0 border-b border-neutral-200 dark:border-neutral-800 max-h-[40%] overflow-y-auto">
              <BriefOutlineNav
                sections={editor.sections}
                activeSectionId={editor.activeSectionId}
                onSectionClick={handleSectionClick}
                onReorderSections={editor.reorderSections}
                onAddSection={onStartInquiry}
              />
            </div>

            {/* Section Context */}
            <div className="flex-1 overflow-y-auto">
              <SectionContextPanel
                activeSection={editor.activeSection}
                overallGrounding={editor.overallGrounding}
                blockingAnnotations={editor.blockingAnnotations}
                statusCounts={editor.statusCounts}
                onDismissAnnotation={editor.dismissAnnotation}
                onNavigateToInquiry={onOpenInquiry}
                onCreateInquiry={handleCreateInquiryFromSection}
              />
            </div>
          </aside>
        )}

        {/* Center: Brief Editor */}
        <main className="flex-1 min-w-0">
          <BriefEditor
            document={brief}
            onSave={() => onRefresh()}
            sections={editor.sections}
            activeSectionId={editor.activeSectionId}
            onActiveSectionChange={editor.setActiveSectionId}
            hideHeader
            inlineEnabled={false}
            suggestions={editor.suggestions}
            onAcceptSuggestion={editor.acceptSuggestion}
            onRejectSuggestion={editor.rejectSuggestion}
            onCreateInquiry={handleCreateInquiryFromText}
            onMarkAssumption={handleMarkAssumption}
          />
        </main>
      </div>

      {/* Toast notification */}
      {briefToast && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2 bg-neutral-800 dark:bg-neutral-200 text-white dark:text-neutral-900 text-sm rounded-lg shadow-lg animate-in fade-in slide-in-from-bottom-2">
          {briefToast}
        </div>
      )}

      {/* Version Diff Modal */}
      {showVersionDiff && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
            <div className="px-6 py-4 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Content Changes
              </h3>
              <button
                onClick={() => setShowVersionDiff(false)}
                className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
              >
                &times;
              </button>
            </div>
            <div className="flex-1 overflow-auto p-6">
              {loadingVersionDiff ? (
                <p className="text-sm text-neutral-500 text-center py-8">Loading diff...</p>
              ) : versionDiffData ? (
                <WordDiff
                  oldText={versionDiffData.oldContent}
                  newText={versionDiffData.newContent}
                />
              ) : (
                <p className="text-sm text-neutral-500 text-center py-8">
                  No version history available to compare.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Evolve Diff Banner ──────────────────────────────────────────

function EvolveDiffBanner({
  diff,
  onDismiss,
  onViewChanges,
}: {
  diff: {
    section_changes: Array<{ id: string; heading: string; old_status: string; new_status: string }>;
    new_annotations: Array<{ id: string; type: string; section_heading: string }>;
    resolved_annotations: Array<{ id: string; type: string; section_heading: string }>;
    readiness_created?: number;
    readiness_auto_completed?: number;
  };
  onDismiss: () => void;
  onViewChanges?: () => void;
}) {
  const { section_changes, new_annotations, resolved_annotations } = diff;

  const parts: string[] = [];
  const statusOrder = ['empty', 'weak', 'moderate', 'strong'];

  const upgraded = section_changes.filter(c =>
    statusOrder.indexOf(c.new_status) > statusOrder.indexOf(c.old_status)
  );
  const downgraded = section_changes.filter(c =>
    statusOrder.indexOf(c.new_status) < statusOrder.indexOf(c.old_status) && c.new_status !== 'conflicted'
  );
  const newConflicts = section_changes.filter(c =>
    c.new_status === 'conflicted' && c.old_status !== 'conflicted'
  );

  if (upgraded.length > 0) parts.push(`${upgraded.length} section${upgraded.length !== 1 ? 's' : ''} strengthened`);
  if (downgraded.length > 0) parts.push(`${downgraded.length} weakened`);
  if (newConflicts.length > 0) parts.push(`${newConflicts.length} new conflict${newConflicts.length !== 1 ? 's' : ''}`);
  if (new_annotations.length > 0) parts.push(`${new_annotations.length} new annotation${new_annotations.length !== 1 ? 's' : ''}`);
  if (resolved_annotations.length > 0) parts.push(`${resolved_annotations.length} resolved`);
  if ((diff.readiness_auto_completed ?? 0) > 0) parts.push(`${diff.readiness_auto_completed} readiness auto-completed`);

  if (parts.length === 0) return null;

  const hasPositive = upgraded.length > 0 || resolved_annotations.length > 0;
  const hasNegative = downgraded.length > 0 || newConflicts.length > 0;

  const bannerStyle = hasNegative
    ? 'border-amber-200 dark:border-amber-900/40 bg-amber-50/50 dark:bg-amber-900/10'
    : hasPositive
    ? 'border-emerald-200 dark:border-emerald-900/40 bg-emerald-50/50 dark:bg-emerald-900/10'
    : 'border-blue-200 dark:border-blue-900/40 bg-blue-50/50 dark:bg-blue-900/10';
  const textStyle = hasNegative
    ? 'text-amber-700 dark:text-amber-300'
    : hasPositive
    ? 'text-emerald-700 dark:text-emerald-300'
    : 'text-blue-700 dark:text-blue-300';

  return (
    <div className={cn('px-4 py-2 border-b flex items-center justify-between gap-3', bannerStyle)}>
      <div className="flex-1 min-w-0">
        <span className={cn('text-xs font-medium', textStyle)}>
          Brief grounding updated:
        </span>{' '}
        <span className={cn('text-xs', textStyle.replace('700', '600').replace('300', '400'))}>
          {parts.join(' · ')}
        </span>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {onViewChanges && (
          <button
            onClick={onViewChanges}
            className={cn('text-[11px] underline hover:no-underline', textStyle)}
          >
            View changes
          </button>
        )}
        <button
          onClick={onDismiss}
          className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
          title="Dismiss"
        >
          <span className="text-sm">&times;</span>
        </button>
      </div>
    </div>
  );
}

// ── Icons ────────────────────────────────────────────────────────

function EvolveIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M23 4v6h-6M1 20v-6h6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LoadingSpinner({ className }: { className?: string }) {
  return (
    <svg className={cn(className, 'animate-spin')} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 019.17 6" strokeLinecap="round" />
    </svg>
  );
}

export default UnifiedBriefView;
