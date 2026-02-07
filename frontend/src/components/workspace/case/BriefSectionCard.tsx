/**
 * BriefSectionCard — Individual section in the intelligent brief.
 *
 * Shows:
 * - Drag handle (visible on hover) for reordering
 * - Grounding indicator dot (colored by status)
 * - Heading (editable on click)
 * - Content preview (1-2 lines from markdown)
 * - Section type badge
 * - Inquiry link (if linked)
 * - Annotations (progressive disclosure — badges, expand on click)
 * - Action buttons: [Chat about this] [View evidence] [Link inquiry]
 * - Lock state for recommendation/synthesis sections
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type {
  BriefSection,
  GroundingStatus,
  AnnotationType,
  SectionType,
} from '@/lib/types/case';

// Annotation action config: what action to offer for each annotation type
const ANNOTATION_ACTIONS: Record<string, { label: string; actionType: 'resolve_ai' | 'investigate' | 'find_evidence' | 'validate' }> = {
  tension: { label: 'Resolve with AI', actionType: 'resolve_ai' },
  blind_spot: { label: 'Investigate', actionType: 'investigate' },
  evidence_desert: { label: 'Find Evidence', actionType: 'find_evidence' },
  ungrounded: { label: 'Validate', actionType: 'validate' },
  circular: { label: 'Resolve with AI', actionType: 'resolve_ai' },
  stale: { label: 'Refresh Evidence', actionType: 'find_evidence' },
};

interface BriefSectionCardProps {
  section: BriefSection;
  onUpdateHeading?: (sectionId: string, heading: string) => void;
  onDelete?: (sectionId: string) => void;
  onLinkInquiry?: (sectionId: string) => void;
  onUnlinkInquiry?: (sectionId: string) => void;
  onDismissAnnotation?: (sectionId: string, annotationId: string) => void;
  onNavigateToInquiry?: (inquiryId: string) => void;
  onStartChat?: (prompt?: string) => void;
  onToggleCollapse?: (sectionId: string, collapsed: boolean) => void;
  /** Open agentic task dialog pre-filled with a resolution task */
  onStartAgenticTask?: (task: string) => void;
  /** Create a new inquiry from an annotation */
  onCreateInquiry?: (title: string, sectionId: string) => void;
  /** Drag-and-drop props */
  isDragging?: boolean;
  isDragOver?: boolean;
  onDragStart?: (e: React.DragEvent, sectionId: string) => void;
  onDragEnd?: (e: React.DragEvent) => void;
  onDragOver?: (e: React.DragEvent, sectionId: string) => void;
  onDragLeave?: (e: React.DragEvent) => void;
  onDrop?: (e: React.DragEvent, sectionId: string) => void;
}

// Grounding status colors and labels
const GROUNDING_CONFIG: Record<GroundingStatus, { color: string; bg: string; label: string }> = {
  empty: { color: 'text-neutral-400', bg: 'bg-neutral-200 dark:bg-neutral-700', label: 'No evidence' },
  weak: { color: 'text-amber-500', bg: 'bg-amber-200 dark:bg-amber-900/40', label: 'Under-evidenced' },
  moderate: { color: 'text-blue-500', bg: 'bg-blue-200 dark:bg-blue-900/40', label: 'Some evidence' },
  strong: { color: 'text-emerald-500', bg: 'bg-emerald-200 dark:bg-emerald-900/40', label: 'Well-grounded' },
  conflicted: { color: 'text-red-500', bg: 'bg-red-200 dark:bg-red-900/40', label: 'Has tensions' },
};

// Annotation type icons and colors
const ANNOTATION_CONFIG: Record<AnnotationType, { icon: string; color: string; label: string }> = {
  tension: { icon: '\u26A1', color: 'text-red-600 dark:text-red-400', label: 'Tension' },
  blind_spot: { icon: '\uD83D\uDC41\uFE0F', color: 'text-amber-600 dark:text-amber-400', label: 'Blind spot' },
  ungrounded: { icon: '\u26A0\uFE0F', color: 'text-amber-600 dark:text-amber-400', label: 'Unvalidated' },
  evidence_desert: { icon: '\uD83D\uDCED', color: 'text-neutral-500', label: 'Needs evidence' },
  well_grounded: { icon: '\u2705', color: 'text-emerald-600 dark:text-emerald-400', label: 'Strong' },
  stale: { icon: '\u23F0', color: 'text-neutral-500', label: 'Stale' },
  circular: { icon: '\uD83D\uDD04', color: 'text-red-600 dark:text-red-400', label: 'Circular' },
};

// Section type labels
const SECTION_TYPE_LABELS: Record<SectionType, string> = {
  decision_frame: 'Decision Frame',
  inquiry_brief: 'Inquiry',
  synthesis: 'Synthesis',
  trade_offs: 'Trade-offs',
  recommendation: 'Recommendation',
  custom: 'Custom',
};

export function BriefSectionCard({
  section,
  onUpdateHeading,
  onDelete,
  onLinkInquiry,
  onUnlinkInquiry,
  onDismissAnnotation,
  onNavigateToInquiry,
  onStartChat,
  onToggleCollapse,
  onStartAgenticTask,
  onCreateInquiry,
  isDragging,
  isDragOver,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDragLeave,
  onDrop,
}: BriefSectionCardProps) {
  const [isEditingHeading, setIsEditingHeading] = useState(false);
  const [headingValue, setHeadingValue] = useState(section.heading);
  const [showAnnotations, setShowAnnotations] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const headingRef = useRef<HTMLInputElement>(null);

  const grounding = GROUNDING_CONFIG[section.grounding_status];
  const hasAnnotations = section.annotations.length > 0;
  const blockingCount = section.annotations.filter(a => a.priority === 'blocking').length;

  useEffect(() => {
    if (isEditingHeading && headingRef.current) {
      headingRef.current.focus();
      headingRef.current.select();
    }
  }, [isEditingHeading]);

  const handleHeadingSave = () => {
    setIsEditingHeading(false);
    if (headingValue !== section.heading && onUpdateHeading) {
      onUpdateHeading(section.id, headingValue);
    }
  };

  if (section.is_locked) {
    return (
      <div className="px-4 py-3 border border-neutral-200 dark:border-neutral-800 rounded-xl bg-neutral-50/30 dark:bg-neutral-900/30 opacity-60">
        <div className="flex items-center gap-3">
          <LockIcon className="w-4 h-4 text-neutral-400" />
          <span className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
            {section.heading}
          </span>
        </div>
        {section.lock_reason && (
          <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1 ml-7">
            {section.lock_reason}
          </p>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'border border-neutral-200 dark:border-neutral-800 rounded-xl transition-all',
        'hover:border-neutral-300 dark:hover:border-neutral-700',
        section.depth > 0 && 'ml-6',
        isDragging && 'opacity-40 scale-[0.98]',
        isDragOver && 'border-accent-400 dark:border-accent-600 bg-accent-50/30 dark:bg-accent-900/10',
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
      draggable={!!onDragStart}
      onDragStart={(e) => onDragStart?.(e, section.id)}
      onDragEnd={onDragEnd}
      onDragOver={(e) => onDragOver?.(e, section.id)}
      onDragLeave={onDragLeave}
      onDrop={(e) => onDrop?.(e, section.id)}
    >
      {/* Section Header */}
      <div className="px-4 py-3 flex items-start gap-2">
        {/* Collapse chevron */}
        {onToggleCollapse && (
          <button
            onClick={() => onToggleCollapse(section.id, !section.is_collapsed)}
            className="mt-0.5 flex-shrink-0 p-0.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
            aria-label={section.is_collapsed ? 'Expand section' : 'Collapse section'}
            aria-expanded={!section.is_collapsed}
          >
            <CollapseChevron className="w-3.5 h-3.5 text-neutral-400" collapsed={section.is_collapsed} />
          </button>
        )}

        {/* Drag Handle — visible on hover */}
        {onDragStart && (
          <div
            className={cn(
              'mt-1 flex-shrink-0 cursor-grab active:cursor-grabbing transition-opacity',
              showActions ? 'opacity-50 hover:opacity-100' : 'opacity-0'
            )}
            title="Drag to reorder"
          >
            <DragHandleIcon className="w-4 h-4 text-neutral-400" />
          </div>
        )}

        {/* Grounding Dot */}
        <div className="mt-1 flex-shrink-0" title={grounding.label}>
          <div className={cn('w-2.5 h-2.5 rounded-full', grounding.bg)} />
        </div>

        {/* Heading + Type + Content Preview */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {isEditingHeading ? (
              <input
                ref={headingRef}
                value={headingValue}
                onChange={(e) => setHeadingValue(e.target.value)}
                onBlur={handleHeadingSave}
                onKeyDown={(e) => e.key === 'Enter' && handleHeadingSave()}
                className="text-sm font-semibold text-primary-900 dark:text-primary-50 bg-transparent border-b border-accent-400 outline-none w-full"
              />
            ) : (
              <h3
                className="text-sm font-semibold text-primary-900 dark:text-primary-50 cursor-text"
                onClick={() => setIsEditingHeading(true)}
              >
                {section.heading}
              </h3>
            )}

            {/* Section type badge */}
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 flex-shrink-0">
              {SECTION_TYPE_LABELS[section.section_type]}
            </span>
          </div>

          {/* Collapsible body: content preview, inquiry link, grounding summary */}
          {!section.is_collapsed && (
            <>
              {/* Content preview — 1-2 lines of prose from markdown */}
              {section.content_preview && (
                <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-2 leading-relaxed">
                  {section.content_preview}
                </p>
              )}

              {/* Inquiry link */}
              {section.inquiry_title && (
                <button
                  onClick={() => section.inquiry && onNavigateToInquiry?.(section.inquiry)}
                  className="text-xs text-accent-600 dark:text-accent-400 hover:underline mt-0.5"
                >
                  Linked to: {section.inquiry_title}
                </button>
              )}

              {/* Grounding summary (compact) */}
              {section.is_linked && section.grounding_data.evidence_count !== undefined && (
                <div className="flex items-center gap-3 mt-1.5 text-xs text-neutral-500 dark:text-neutral-400">
                  <span>{section.grounding_data.evidence_count} evidence</span>
                  {(section.grounding_data.tensions_count ?? 0) > 0 && (
                    <span className="text-red-500">
                      {section.grounding_data.tensions_count} tension{(section.grounding_data.tensions_count ?? 0) !== 1 ? 's' : ''}
                    </span>
                  )}
                  {(section.grounding_data.unvalidated_assumptions ?? 0) > 0 && (
                    <span className="text-amber-500">
                      {section.grounding_data.unvalidated_assumptions} unvalidated
                    </span>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Right side: annotation badges + actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Annotation badges */}
          {hasAnnotations && (
            <button
              onClick={() => setShowAnnotations(!showAnnotations)}
              className={cn(
                'flex items-center gap-1 px-2 py-0.5 rounded-full text-xs transition-colors',
                blockingCount > 0
                  ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                  : 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'
              )}
            >
              {blockingCount > 0 ? '\u26A1' : '\u26A0\uFE0F'} {section.annotations.length}
            </button>
          )}

          {/* Actions (show on hover) */}
          {showActions && (
            <div className="flex items-center gap-1">
              {!section.inquiry && onLinkInquiry && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={() => onLinkInquiry(section.id)}
                >
                  Link
                </Button>
              )}
              {section.inquiry && onUnlinkInquiry && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={() => onUnlinkInquiry(section.id)}
                >
                  Unlink
                </Button>
              )}
              {onDelete && section.created_by !== 'system' && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs text-red-500"
                  onClick={() => onDelete(section.id)}
                >
                  Delete
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Annotations (progressive disclosure) — hidden when collapsed */}
      {!section.is_collapsed && showAnnotations && hasAnnotations && (
        <div className="px-4 pb-3 pt-0 border-t border-neutral-100 dark:border-neutral-800 mt-0">
          <div className="space-y-2 mt-2">
            {section.annotations.map((annotation) => {
              const config = ANNOTATION_CONFIG[annotation.annotation_type];
              const actionConfig = ANNOTATION_ACTIONS[annotation.annotation_type];
              return (
                <div
                  key={annotation.id}
                  className="flex items-start gap-2 text-xs group/ann"
                >
                  <span className={cn('flex-shrink-0 mt-0.5', config.color)}>
                    {config.icon}
                  </span>
                  <div className="flex-1 min-w-0">
                    <span className="text-neutral-700 dark:text-neutral-300">
                      {annotation.description}
                    </span>
                    {/* Annotation action button */}
                    {actionConfig && (
                      <div className="mt-1 opacity-0 group-hover/ann:opacity-100 transition-opacity">
                        <button
                          className="text-[10px] px-2 py-0.5 rounded border border-accent-200 text-accent-600 hover:bg-accent-50 dark:border-accent-800 dark:text-accent-400 dark:hover:bg-accent-900/20"
                          onClick={() => {
                            const { actionType } = actionConfig;
                            if (actionType === 'resolve_ai' && onStartAgenticTask) {
                              onStartAgenticTask(
                                `Resolve ${config.label.toLowerCase()} in "${section.heading}": ${annotation.description}`
                              );
                            } else if (
                              (actionType === 'investigate' || actionType === 'find_evidence' || actionType === 'validate') &&
                              onCreateInquiry
                            ) {
                              const title =
                                actionType === 'investigate'
                                  ? `Investigate blind spot: ${annotation.description.slice(0, 80)}`
                                  : actionType === 'find_evidence'
                                  ? `Find evidence for: ${section.heading}`
                                  : `Validate: ${annotation.description.slice(0, 80)}`;
                              onCreateInquiry(title, section.id);
                            }
                          }}
                        >
                          {actionConfig.label}
                        </button>
                      </div>
                    )}
                  </div>
                  {onDismissAnnotation && (
                    <button
                      onClick={() => onDismissAnnotation(section.id, annotation.id)}
                      className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 flex-shrink-0"
                      title="Dismiss"
                    >
                      &times;
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick actions bar */}
      {section.is_linked && !section.is_collapsed && (
        <div className="px-4 pb-2 flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs text-neutral-500"
            onClick={() => onStartChat?.(
              `Let's discuss ${section.heading}${section.inquiry_title ? ` (${section.inquiry_title})` : ''}`
            )}
          >
            Chat about this
          </Button>
          {section.inquiry && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs text-neutral-500"
              onClick={() => section.inquiry && onNavigateToInquiry?.(section.inquiry)}
            >
              View inquiry
            </Button>
          )}
        </div>
      )}

      {/* Nested subsections — hidden when collapsed */}
      {!section.is_collapsed && section.subsections?.length > 0 && (
        <div className="px-4 pb-3 space-y-2">
          {section.subsections.map((sub) => (
            <BriefSectionCard
              key={sub.id}
              section={sub}
              onUpdateHeading={onUpdateHeading}
              onDelete={onDelete}
              onLinkInquiry={onLinkInquiry}
              onUnlinkInquiry={onUnlinkInquiry}
              onDismissAnnotation={onDismissAnnotation}
              onNavigateToInquiry={onNavigateToInquiry}
              onStartChat={onStartChat}
              onToggleCollapse={onToggleCollapse}
              onStartAgenticTask={onStartAgenticTask}
              onCreateInquiry={onCreateInquiry}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Icons
function LockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0110 0v4" />
    </svg>
  );
}

function CollapseChevron({ className, collapsed }: { className?: string; collapsed?: boolean }) {
  return (
    <svg
      className={cn(className, 'transition-transform duration-150', collapsed ? '' : 'rotate-90')}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DragHandleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <circle cx="9" cy="6" r="1.5" />
      <circle cx="15" cy="6" r="1.5" />
      <circle cx="9" cy="12" r="1.5" />
      <circle cx="15" cy="12" r="1.5" />
      <circle cx="9" cy="18" r="1.5" />
      <circle cx="15" cy="18" r="1.5" />
    </svg>
  );
}

export default BriefSectionCard;
