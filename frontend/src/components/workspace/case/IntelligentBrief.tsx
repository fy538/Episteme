/**
 * IntelligentBrief — Living, intelligent case brief component.
 *
 * Replaces the static brief section with a dynamic, structured view:
 * - Overall grounding overview with status breakdown
 * - Ordered list of BriefSectionCard components with drag-to-reorder
 * - Add section capability
 * - Evolve (recompute grounding) trigger with auto-refresh pulse
 * - Blocking annotations summary
 * - Link inquiry modal for connecting sections to inquiries
 */

'use client';

import { useState, useMemo, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useBrief } from '@/hooks/useBrief';
import { BriefSectionCard } from './BriefSectionCard';
import { WordDiff } from '@/components/editor/WordDiff';
import { documentsAPI } from '@/lib/api/documents';
import type { Case, Inquiry, SectionType, GroundingStatus, EvolveDiff } from '@/lib/types/case';

interface IntelligentBriefProps {
  caseId: string;
  caseData: Case;
  inquiries: Inquiry[];
  onNavigateToInquiry?: (inquiryId: string) => void;
  onStartChat?: (prompt?: string) => void;
  onOpenBriefEditor?: () => void;
  className?: string;
}

// Section type options for the add-section menu
const SECTION_TYPE_OPTIONS: Array<{ value: SectionType; label: string; description: string }> = [
  { value: 'custom', label: 'Custom', description: 'Free-form section' },
  { value: 'inquiry_brief', label: 'Inquiry', description: 'Link to an inquiry thread' },
  { value: 'synthesis', label: 'Synthesis', description: 'Synthesize findings across inquiries' },
  { value: 'trade_offs', label: 'Trade-offs', description: 'Compare alternatives and trade-offs' },
  { value: 'recommendation', label: 'Recommendation', description: 'Your recommendation or conclusion' },
];

// Grounding status display configuration
const GROUNDING_SUMMARY: Record<GroundingStatus, { label: string; color: string }> = {
  empty: { label: 'No evidence', color: 'text-neutral-400' },
  weak: { label: 'Weak', color: 'text-amber-500' },
  moderate: { label: 'Moderate', color: 'text-blue-500' },
  strong: { label: 'Strong', color: 'text-emerald-500' },
  conflicted: { label: 'Conflicted', color: 'text-red-500' },
};

export function IntelligentBrief({
  caseId,
  caseData,
  inquiries,
  onNavigateToInquiry,
  onStartChat,
  onOpenBriefEditor,
  className,
}: IntelligentBriefProps) {
  const {
    sections,
    briefId,
    isLoading,
    isEvolving,
    isPolling,
    lastEvolvedAt,
    lastEvolveDiff,
    dismissEvolveDiff,
    error,
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
    statusCounts,
  } = useBrief({ caseId });

  // Local state
  const [showAddSection, setShowAddSection] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState<string | null>(null); // section ID
  const [newSectionHeading, setNewSectionHeading] = useState('');
  const [newSectionType, setNewSectionType] = useState<SectionType>('custom');

  // Version diff state (for "View changes" on evolve)
  const [showVersionDiff, setShowVersionDiff] = useState(false);
  const [versionDiffData, setVersionDiffData] = useState<{ oldContent: string; newContent: string } | null>(null);
  const [loadingVersionDiff, setLoadingVersionDiff] = useState(false);

  const handleViewChanges = useCallback(async () => {
    if (!briefId) return;
    setLoadingVersionDiff(true);
    setShowVersionDiff(true);
    try {
      const versions = await documentsAPI.getVersionHistoryWithContent(briefId);
      if (versions.length >= 2) {
        // Compare the two most recent versions
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
  }, [briefId]);

  // ── Drag-and-drop state ──────────────────────────────────────
  const [dragSourceId, setDragSourceId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);

  // Inquiries that can be linked (not already linked to a section)
  const linkedInquiryIds = useMemo(() => {
    const ids = new Set<string>();
    const collect = (sects: typeof sections) => {
      for (const s of sects) {
        if (s.inquiry) ids.add(s.inquiry);
        if (s.subsections?.length) collect(s.subsections);
      }
    };
    collect(sections);
    return ids;
  }, [sections]);

  const availableInquiries = useMemo(
    () => inquiries.filter(inq => !linkedInquiryIds.has(inq.id)),
    [inquiries, linkedInquiryIds]
  );

  // Grounding ring color
  const groundingColor = useMemo(() => {
    if (overallGrounding >= 80) return 'text-emerald-500';
    if (overallGrounding >= 50) return 'text-blue-500';
    if (overallGrounding >= 25) return 'text-amber-500';
    return 'text-neutral-400';
  }, [overallGrounding]);

  // ── Handlers ──────────────────────────────────────────────────

  const handleAddSection = useCallback(async () => {
    if (!newSectionHeading.trim()) return;
    await addSection({
      heading: newSectionHeading.trim(),
      section_type: newSectionType,
      order: sections.length,
    });
    setNewSectionHeading('');
    setNewSectionType('custom');
    setShowAddSection(false);
  }, [newSectionHeading, newSectionType, sections.length, addSection]);

  const handleUpdateHeading = useCallback(async (sectionId: string, heading: string) => {
    await updateSection(sectionId, { heading });
  }, [updateSection]);

  const handleDelete = useCallback(async (sectionId: string) => {
    await deleteSection(sectionId);
  }, [deleteSection]);

  const handleLinkInquiry = useCallback(async (sectionId: string) => {
    setShowLinkModal(sectionId);
  }, []);

  const handleConfirmLink = useCallback(async (inquiryId: string) => {
    if (!showLinkModal) return;
    await linkToInquiry(showLinkModal, inquiryId);
    setShowLinkModal(null);
  }, [showLinkModal, linkToInquiry]);

  const handleUnlinkInquiry = useCallback(async (sectionId: string) => {
    await unlinkFromInquiry(sectionId);
  }, [unlinkFromInquiry]);

  const handleDismissAnnotation = useCallback(async (sectionId: string, annotationId: string) => {
    await dismissAnnotation(sectionId, annotationId);
  }, [dismissAnnotation]);

  const handleNavigateToInquiry = useCallback((inquiryId: string) => {
    onNavigateToInquiry?.(inquiryId);
  }, [onNavigateToInquiry]);

  // ── Drag-and-drop handlers ────────────────────────────────────

  const handleDragStart = useCallback((e: React.DragEvent, sectionId: string) => {
    setDragSourceId(sectionId);
    e.dataTransfer.effectAllowed = 'move';
    // Set a minimal drag image (the browser will show the element by default)
    e.dataTransfer.setData('text/plain', sectionId);
  }, []);

  const handleDragEnd = useCallback(() => {
    setDragSourceId(null);
    setDragOverId(null);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, sectionId: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (sectionId !== dragSourceId) {
      setDragOverId(sectionId);
    }
  }, [dragSourceId]);

  const handleDragLeave = useCallback(() => {
    setDragOverId(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    setDragOverId(null);

    if (!dragSourceId || dragSourceId === targetId) {
      setDragSourceId(null);
      return;
    }

    // Compute new order: move source to target's position
    const currentOrder = sections.map(s => s.id);
    const sourceIdx = currentOrder.indexOf(dragSourceId);
    const targetIdx = currentOrder.indexOf(targetId);

    if (sourceIdx === -1 || targetIdx === -1) {
      setDragSourceId(null);
      return;
    }

    // Remove source and insert at target position
    const newOrder = [...currentOrder];
    newOrder.splice(sourceIdx, 1);
    newOrder.splice(targetIdx, 0, dragSourceId);

    // Build reorder payload
    const reorderPayload = newOrder.map((id, idx) => ({ id, order: idx }));
    reorderSections(reorderPayload);

    setDragSourceId(null);
  }, [dragSourceId, sections, reorderSections]);

  // ── Loading State ─────────────────────────────────────────────

  if (isLoading && sections.length === 0) {
    return (
      <div className={cn('animate-pulse space-y-3', className)}>
        <div className="h-16 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
        <div className="h-24 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
        <div className="h-24 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
      </div>
    );
  }

  // ── Empty State ───────────────────────────────────────────────

  if (!isLoading && sections.length === 0) {
    return (
      <div className={cn('border border-dashed border-neutral-300 dark:border-neutral-700 rounded-xl p-8 text-center', className)}>
        <BriefEmptyIcon className="w-10 h-10 mx-auto text-neutral-300 dark:text-neutral-600 mb-3" />
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
          No brief sections yet. Add sections to start building your case brief.
        </p>
        <Button
          size="sm"
          onClick={() => setShowAddSection(true)}
        >
          <PlusIcon className="w-4 h-4 mr-1" />
          Add Section
        </Button>
        {showAddSection && (
          <AddSectionForm
            heading={newSectionHeading}
            sectionType={newSectionType}
            onHeadingChange={setNewSectionHeading}
            onTypeChange={setNewSectionType}
            onSubmit={handleAddSection}
            onCancel={() => setShowAddSection(false)}
          />
        )}
      </div>
    );
  }

  // ── Main Render ───────────────────────────────────────────────

  return (
    <div className={cn('space-y-4', className)}>
      {/* Grounding Overview Header */}
      <div className="flex items-center justify-between p-3 border border-neutral-200 dark:border-neutral-800 rounded-xl bg-neutral-50/50 dark:bg-neutral-900/50">
        <div className="flex items-center gap-4">
          {/* Grounding score ring */}
          <div className="relative w-12 h-12 flex items-center justify-center">
            <svg className="w-12 h-12 -rotate-90" viewBox="0 0 36 36">
              <circle
                cx="18" cy="18" r="15"
                fill="none"
                className="stroke-neutral-200 dark:stroke-neutral-700"
                strokeWidth="3"
              />
              <circle
                cx="18" cy="18" r="15"
                fill="none"
                className={groundingColor.replace('text-', 'stroke-')}
                strokeWidth="3"
                strokeDasharray={`${overallGrounding * 0.942} 94.2`}
                strokeLinecap="round"
              />
            </svg>
            <span className={cn('absolute text-xs font-bold', groundingColor)}>
              {overallGrounding}
            </span>
          </div>

          {/* Status breakdown */}
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-primary-900 dark:text-primary-50">
                Brief Grounding
              </span>
              {/* Evolve pulse — shows when background evolve detected */}
              {isPolling && (
                <span className="flex items-center gap-1 text-[10px] text-accent-500 dark:text-accent-400">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-500" />
                  </span>
                  Updating...
                </span>
              )}
              {lastEvolvedAt && !isPolling && !isEvolving && (
                <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
                  Updated {formatRelativeTime(lastEvolvedAt)}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-0.5 text-xs">
              {(Object.entries(statusCounts) as [GroundingStatus, number][])
                .filter(([_, count]) => count > 0)
                .map(([status, count]) => (
                  <span
                    key={status}
                    className={cn('flex items-center gap-1', GROUNDING_SUMMARY[status].color)}
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
            onClick={evolveBrief}
            disabled={isEvolving}
          >
            {isEvolving ? (
              <>
                <LoadingSpinner className="w-3.5 h-3.5 mr-1" />
                Evolving...
              </>
            ) : (
              <>
                <EvolveIcon className="w-3.5 h-3.5 mr-1" />
                Evolve
              </>
            )}
          </Button>
          {onOpenBriefEditor && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={onOpenBriefEditor}
            >
              <EditIcon className="w-3.5 h-3.5 mr-1" />
              Edit Brief
            </Button>
          )}
        </div>
      </div>

      {/* Blocking Annotations Banner */}
      {blockingAnnotations.length > 0 && (
        <div className="p-3 border border-red-200 dark:border-red-900/40 rounded-xl bg-red-50/50 dark:bg-red-900/10">
          <div className="flex items-center gap-2 text-xs font-medium text-red-600 dark:text-red-400 mb-1">
            <BlockingIcon className="w-3.5 h-3.5" />
            {blockingAnnotations.length} blocking issue{blockingAnnotations.length !== 1 ? 's' : ''}
          </div>
          <ul className="space-y-1">
            {blockingAnnotations.slice(0, 3).map(({ sectionHeading, annotation }) => (
              <li key={annotation.id} className="text-xs text-red-500 dark:text-red-400/80">
                <span className="font-medium">{sectionHeading}:</span> {annotation.description}
              </li>
            ))}
            {blockingAnnotations.length > 3 && (
              <li className="text-xs text-red-400 dark:text-red-500">
                +{blockingAnnotations.length - 3} more
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="p-3 border border-amber-200 dark:border-amber-900/40 rounded-xl bg-amber-50/50 dark:bg-amber-900/10 text-xs text-amber-600 dark:text-amber-400">
          {error}
        </div>
      )}

      {/* Evolve Diff Banner — shows what changed after grounding recomputation */}
      {lastEvolveDiff && (
        <EvolveDiffBanner
          diff={lastEvolveDiff}
          onDismiss={dismissEvolveDiff}
          onViewChanges={briefId ? handleViewChanges : undefined}
        />
      )}

      {/* Version Diff Modal — shows content diff after evolve */}
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

      {/* Section Cards — with drag-to-reorder */}
      <div className="space-y-2">
        {sections.map((section) => (
          <BriefSectionCard
            key={section.id}
            section={section}
            onUpdateHeading={handleUpdateHeading}
            onDelete={handleDelete}
            onLinkInquiry={handleLinkInquiry}
            onUnlinkInquiry={handleUnlinkInquiry}
            onDismissAnnotation={handleDismissAnnotation}
            onNavigateToInquiry={handleNavigateToInquiry}
            onToggleCollapse={toggleCollapse}
            onStartChat={onStartChat}
            isDragging={dragSourceId === section.id}
            isDragOver={dragOverId === section.id}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          />
        ))}
      </div>

      {/* Add Section */}
      {showAddSection ? (
        <AddSectionForm
          heading={newSectionHeading}
          sectionType={newSectionType}
          onHeadingChange={setNewSectionHeading}
          onTypeChange={setNewSectionType}
          onSubmit={handleAddSection}
          onCancel={() => {
            setShowAddSection(false);
            setNewSectionHeading('');
            setNewSectionType('custom');
          }}
        />
      ) : (
        <button
          onClick={() => setShowAddSection(true)}
          className="w-full py-2 border border-dashed border-neutral-300 dark:border-neutral-700 rounded-xl text-xs text-neutral-500 dark:text-neutral-400 hover:border-neutral-400 dark:hover:border-neutral-600 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
        >
          <PlusIcon className="w-3.5 h-3.5 inline mr-1" />
          Add section
        </button>
      )}

      {/* Link Inquiry Modal */}
      {showLinkModal && (
        <LinkInquiryModal
          inquiries={availableInquiries}
          onSelect={handleConfirmLink}
          onClose={() => setShowLinkModal(null)}
        />
      )}
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────

function formatRelativeTime(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 10) return 'just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

// ── Sub-components ──────────────────────────────────────────────

function AddSectionForm({
  heading,
  sectionType,
  onHeadingChange,
  onTypeChange,
  onSubmit,
  onCancel,
}: {
  heading: string;
  sectionType: SectionType;
  onHeadingChange: (v: string) => void;
  onTypeChange: (v: SectionType) => void;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="mt-3 p-4 border border-neutral-200 dark:border-neutral-800 rounded-xl bg-white dark:bg-neutral-900">
      <div className="space-y-3">
        <input
          type="text"
          value={heading}
          onChange={(e) => onHeadingChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSubmit()}
          placeholder="Section heading..."
          className="w-full text-sm font-medium text-primary-900 dark:text-primary-50 bg-transparent border-b border-neutral-300 dark:border-neutral-700 pb-1 outline-none focus:border-accent-500 dark:focus:border-accent-400"
          autoFocus
        />
        <div className="flex flex-wrap gap-1.5">
          {SECTION_TYPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onTypeChange(opt.value)}
              className={cn(
                'px-2 py-1 rounded-md text-xs transition-colors',
                sectionType === opt.value
                  ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-700 dark:text-accent-300 ring-1 ring-accent-300 dark:ring-accent-700'
                  : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
              )}
              title={opt.description}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 justify-end">
          <Button variant="ghost" size="sm" onClick={onCancel} className="h-7 text-xs">
            Cancel
          </Button>
          <Button size="sm" onClick={onSubmit} className="h-7 text-xs" disabled={!heading.trim()}>
            Add
          </Button>
        </div>
      </div>
    </div>
  );
}

function LinkInquiryModal({
  inquiries,
  onSelect,
  onClose,
}: {
  inquiries: Inquiry[];
  onSelect: (inquiryId: string) => void;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-xl shadow-lg w-full max-w-sm mx-4">
        <div className="p-4 border-b border-neutral-200 dark:border-neutral-800">
          <h3 className="text-sm font-semibold text-primary-900 dark:text-primary-50">
            Link to Inquiry
          </h3>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
            Connect this section to an inquiry for grounding
          </p>
        </div>

        <div className="p-2 max-h-60 overflow-y-auto">
          {inquiries.length === 0 ? (
            <p className="text-xs text-neutral-500 dark:text-neutral-400 text-center py-4">
              No available inquiries. All are linked or none exist.
            </p>
          ) : (
            inquiries.map((inq) => (
              <button
                key={inq.id}
                onClick={() => onSelect(inq.id)}
                className="w-full text-left p-2.5 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
              >
                <div className="text-sm font-medium text-primary-900 dark:text-primary-50">
                  {inq.title}
                </div>
                <div className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                  {inq.status === 'resolved' ? 'Resolved' : inq.status === 'investigating' ? 'Investigating' : 'Open'}
                </div>
              </button>
            ))
          )}
        </div>

        <div className="p-3 border-t border-neutral-200 dark:border-neutral-800 flex justify-end">
          <Button variant="ghost" size="sm" onClick={onClose} className="h-7 text-xs">
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Evolve Diff Banner ───────────────────────────────────────────

function EvolveDiffBanner({
  diff,
  onDismiss,
  onViewChanges,
}: {
  diff: EvolveDiff;
  onDismiss: () => void;
  onViewChanges?: () => void;
}) {
  const { section_changes, new_annotations, resolved_annotations } = diff;

  // Build summary line
  const parts: string[] = [];

  // Section status changes
  const upgraded = section_changes.filter(c => {
    const order = ['empty', 'weak', 'moderate', 'strong'];
    return order.indexOf(c.new_status) > order.indexOf(c.old_status);
  });
  const downgraded = section_changes.filter(c => {
    const order = ['empty', 'weak', 'moderate', 'strong'];
    return order.indexOf(c.new_status) < order.indexOf(c.old_status) && c.new_status !== 'conflicted';
  });
  const newConflicts = section_changes.filter(c => c.new_status === 'conflicted' && c.old_status !== 'conflicted');

  if (upgraded.length > 0) {
    parts.push(`${upgraded.length} section${upgraded.length !== 1 ? 's' : ''} strengthened`);
  }
  if (downgraded.length > 0) {
    parts.push(`${downgraded.length} section${downgraded.length !== 1 ? 's' : ''} weakened`);
  }
  if (newConflicts.length > 0) {
    parts.push(`${newConflicts.length} new conflict${newConflicts.length !== 1 ? 's' : ''}`);
  }

  // Annotations
  const newTensions = new_annotations.filter(a => a.type === 'tension');
  const newBlindSpots = new_annotations.filter(a => a.type === 'blind_spot');
  const otherNew = new_annotations.filter(a => a.type !== 'tension' && a.type !== 'blind_spot');

  if (newTensions.length > 0) {
    parts.push(`${newTensions.length} new tension${newTensions.length !== 1 ? 's' : ''} found`);
  }
  if (newBlindSpots.length > 0) {
    parts.push(`${newBlindSpots.length} blind spot${newBlindSpots.length !== 1 ? 's' : ''} detected`);
  }
  if (otherNew.length > 0) {
    parts.push(`${otherNew.length} new annotation${otherNew.length !== 1 ? 's' : ''}`);
  }
  if (resolved_annotations.length > 0) {
    parts.push(`${resolved_annotations.length} resolved`);
  }

  // Readiness checklist updates
  const readinessCreated = diff.readiness_created ?? 0;
  const readinessCompleted = diff.readiness_auto_completed ?? 0;
  if (readinessCompleted > 0) {
    parts.push(`${readinessCompleted} readiness item${readinessCompleted !== 1 ? 's' : ''} auto-completed`);
  }
  if (readinessCreated > 0) {
    parts.push(`${readinessCreated} new readiness item${readinessCreated !== 1 ? 's' : ''}`);
  }

  if (parts.length === 0) return null;

  // Determine banner tone
  const hasPositive = upgraded.length > 0 || resolved_annotations.length > 0 || readinessCompleted > 0;
  const hasNegative = downgraded.length > 0 || newConflicts.length > 0 || newTensions.length > 0;
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
    <div className={cn('p-3 border rounded-xl flex items-start justify-between gap-3', bannerStyle)}>
      <div className="flex-1 min-w-0">
        <div className={cn('text-xs font-medium flex items-center gap-1.5', textStyle)}>
          <EvolveIcon className="w-3.5 h-3.5 flex-shrink-0" />
          Brief grounding updated
        </div>
        <p className={cn('text-xs mt-1', textStyle.replace('700', '600').replace('300', '400'))}>
          {parts.join(' · ')}
        </p>
        {/* Section-level detail for up to 3 changes */}
        {section_changes.length > 0 && section_changes.length <= 3 && (
          <div className="mt-1.5 space-y-0.5">
            {section_changes.map(change => (
              <div key={change.id} className="text-[11px] text-neutral-500 dark:text-neutral-400 flex items-center gap-1.5">
                <span className="font-medium">{change.heading}</span>
                <span className="text-neutral-400 dark:text-neutral-500">
                  {change.old_status} → {change.new_status}
                </span>
              </div>
            ))}
          </div>
        )}
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
          className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 mt-0.5"
          title="Dismiss"
        >
          <span className="text-sm">&times;</span>
        </button>
      </div>
    </div>
  );
}

// ── Icons ────────────────────────────────────────────────────────

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function EvolveIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M23 4v6h-6M1 20v-6h6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function EditIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
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

function BlockingIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" strokeLinecap="round" />
      <line x1="12" y1="17" x2="12.01" y2="17" strokeLinecap="round" />
    </svg>
  );
}

function BriefEmptyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" strokeLinecap="round" />
    </svg>
  );
}

export default IntelligentBrief;
