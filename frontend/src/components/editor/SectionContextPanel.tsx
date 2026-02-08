/**
 * SectionContextPanel — Shows intelligence for the active section.
 *
 * When a section is active: grounding summary, annotations, linked inquiry, actions.
 * When no section is active: overall grounding score and blocking annotations.
 */

'use client';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  GROUNDING_CONFIG,
  GROUNDING_SUMMARY,
  ANNOTATION_CONFIG,
  ANNOTATION_ACTIONS,
  SECTION_TYPE_LABELS,
  getGroundingScoreColor,
  getGroundingScoreStrokeColor,
} from '@/lib/constants/grounding';
import type { BriefSection, BriefAnnotation, GroundingStatus } from '@/lib/types/case';

interface SectionContextPanelProps {
  activeSection: BriefSection | null;
  overallGrounding: number;
  blockingAnnotations: Array<{ sectionHeading: string; annotation: BriefAnnotation }>;
  statusCounts: Record<GroundingStatus, number>;
  onDismissAnnotation?: (sectionId: string, annotationId: string) => void;
  onNavigateToInquiry?: (inquiryId: string) => void;
  onStartChat?: (prompt?: string) => void;
  onCreateInquiry?: (title: string, sectionId: string) => void;
  className?: string;
}

export function SectionContextPanel({
  activeSection,
  overallGrounding,
  blockingAnnotations,
  statusCounts,
  onDismissAnnotation,
  onNavigateToInquiry,
  onStartChat,
  onCreateInquiry,
  className,
}: SectionContextPanelProps) {
  if (activeSection) {
    return (
      <SectionDetail
        section={activeSection}
        onDismissAnnotation={onDismissAnnotation}
        onNavigateToInquiry={onNavigateToInquiry}
        onStartChat={onStartChat}
        onCreateInquiry={onCreateInquiry}
        className={className}
      />
    );
  }

  return (
    <OverallSummary
      overallGrounding={overallGrounding}
      blockingAnnotations={blockingAnnotations}
      statusCounts={statusCounts}
      className={className}
    />
  );
}

// ── Section Detail View ─────────────────────────────────────────

function SectionDetail({
  section,
  onDismissAnnotation,
  onNavigateToInquiry,
  onStartChat,
  onCreateInquiry,
  className,
}: {
  section: BriefSection;
  onDismissAnnotation?: (sectionId: string, annotationId: string) => void;
  onNavigateToInquiry?: (inquiryId: string) => void;
  onStartChat?: (prompt?: string) => void;
  onCreateInquiry?: (title: string, sectionId: string) => void;
  className?: string;
}) {
  const config = GROUNDING_CONFIG[section.grounding_status];
  const { grounding_data } = section;

  return (
    <div className={cn('space-y-3', className)}>
      {/* Section header */}
      <div className="px-3 pt-2">
        <div className="flex items-center gap-2">
          <div className={cn('w-2.5 h-2.5 rounded-full flex-shrink-0', config.dotBg)} />
          <h4 className="text-xs font-semibold text-primary-900 dark:text-primary-50 truncate">
            {section.heading}
          </h4>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400">
            {SECTION_TYPE_LABELS[section.section_type]}
          </span>
          <span className={cn('text-[10px] font-medium', config.color)}>
            {config.label}
          </span>
        </div>
      </div>

      {/* Grounding data */}
      {section.is_linked && grounding_data.evidence_count !== undefined && (
        <div className="px-3">
          <h5 className="text-[10px] font-medium uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-1.5">
            Evidence
          </h5>
          <div className="space-y-1">
            <EvidenceBar label="Supporting" count={grounding_data.supporting ?? 0} color="bg-emerald-400" />
            <EvidenceBar label="Contradicting" count={grounding_data.contradicting ?? 0} color="bg-red-400" />
            <EvidenceBar label="Neutral" count={grounding_data.neutral ?? 0} color="bg-neutral-300" />
          </div>
          <div className="flex items-center gap-3 mt-2 text-[10px] text-neutral-500 dark:text-neutral-400">
            <span>{grounding_data.evidence_count} total</span>
            {(grounding_data.tensions_count ?? 0) > 0 && (
              <span className="text-red-500">
                {grounding_data.tensions_count} tension{(grounding_data.tensions_count ?? 0) !== 1 ? 's' : ''}
              </span>
            )}
            {(grounding_data.unvalidated_assumptions ?? 0) > 0 && (
              <span className="text-amber-500">
                {grounding_data.unvalidated_assumptions} unvalidated
              </span>
            )}
          </div>
        </div>
      )}

      {/* Linked inquiry */}
      {section.inquiry_title && (
        <div className="px-3">
          <h5 className="text-[10px] font-medium uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-1">
            Linked Inquiry
          </h5>
          <button
            onClick={() => section.inquiry && onNavigateToInquiry?.(section.inquiry)}
            className="text-xs text-accent-600 dark:text-accent-400 hover:underline"
          >
            {section.inquiry_title}
          </button>
        </div>
      )}

      {/* Annotations */}
      {section.annotations.length > 0 && (
        <div className="px-3">
          <h5 className="text-[10px] font-medium uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-1.5">
            Annotations ({section.annotations.length})
          </h5>
          <div className="space-y-2">
            {section.annotations.map((annotation) => (
              <AnnotationItem
                key={annotation.id}
                annotation={annotation}
                sectionId={section.id}
                sectionHeading={section.heading}
                onDismiss={onDismissAnnotation}
                onCreateInquiry={onCreateInquiry}
              />
            ))}
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div className="px-3 pb-2 flex flex-wrap gap-1.5">
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-[10px]"
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
            className="h-6 px-2 text-[10px]"
            onClick={() => section.inquiry && onNavigateToInquiry?.(section.inquiry)}
          >
            View inquiry
          </Button>
        )}
        {!section.inquiry && onCreateInquiry && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-[10px]"
            onClick={() => onCreateInquiry?.(
              `Investigate: ${section.heading}`,
              section.id
            )}
          >
            Create inquiry
          </Button>
        )}
      </div>
    </div>
  );
}

// ── Overall Summary View ────────────────────────────────────────

function OverallSummary({
  overallGrounding,
  blockingAnnotations,
  statusCounts,
  className,
}: {
  overallGrounding: number;
  blockingAnnotations: Array<{ sectionHeading: string; annotation: BriefAnnotation }>;
  statusCounts: Record<GroundingStatus, number>;
  className?: string;
}) {
  const scoreColor = getGroundingScoreColor(overallGrounding);
  const strokeColor = getGroundingScoreStrokeColor(overallGrounding);

  return (
    <div className={cn('space-y-3', className)}>
      {/* Overall grounding score */}
      <div className="px-3 pt-2 flex items-center gap-3">
        <div className="relative w-10 h-10 flex items-center justify-center">
          <svg className="w-10 h-10 -rotate-90" viewBox="0 0 36 36">
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
              strokeDasharray={`${overallGrounding * 0.942} 94.2`}
              strokeLinecap="round"
            />
          </svg>
          <span className={cn('absolute text-[10px] font-bold', scoreColor)}>
            {overallGrounding}
          </span>
        </div>
        <div>
          <p className="text-xs font-medium text-primary-900 dark:text-primary-50">
            Brief Grounding
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            {(Object.entries(statusCounts) as [GroundingStatus, number][])
              .filter(([_, count]) => count > 0)
              .map(([status, count]) => (
                <span
                  key={status}
                  className={cn('flex items-center gap-0.5 text-[10px]', GROUNDING_SUMMARY[status].color)}
                >
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-current" />
                  {count}
                </span>
              ))}
          </div>
        </div>
      </div>

      {/* Blocking annotations */}
      {blockingAnnotations.length > 0 && (
        <div className="px-3">
          <h5 className="text-[10px] font-medium uppercase tracking-wider text-red-500 dark:text-red-400 mb-1.5">
            Blocking Issues ({blockingAnnotations.length})
          </h5>
          <div className="space-y-1.5">
            {blockingAnnotations.slice(0, 5).map(({ sectionHeading, annotation }) => {
              const annConfig = ANNOTATION_CONFIG[annotation.annotation_type];
              return (
                <div key={annotation.id} className="text-xs">
                  <span className="font-medium text-neutral-700 dark:text-neutral-300">
                    {sectionHeading}:
                  </span>{' '}
                  <span className="text-neutral-500 dark:text-neutral-400">
                    {annotation.description}
                  </span>
                </div>
              );
            })}
            {blockingAnnotations.length > 5 && (
              <p className="text-[10px] text-neutral-400">
                +{blockingAnnotations.length - 5} more
              </p>
            )}
          </div>
        </div>
      )}

      {/* Hint when no blocking issues */}
      {blockingAnnotations.length === 0 && (
        <div className="px-3">
          <p className="text-xs text-neutral-400 dark:text-neutral-500">
            Click a section in the outline or editor to see its grounding details.
          </p>
        </div>
      )}
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────

function EvidenceBar({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-neutral-500 dark:text-neutral-400 w-20 text-right">
        {label}
      </span>
      <div className="flex-1 h-1.5 bg-neutral-100 dark:bg-neutral-800 rounded-full overflow-hidden">
        {count > 0 && (
          <div
            className={cn('h-full rounded-full', color)}
            style={{ width: `${Math.min(count * 20, 100)}%` }}
          />
        )}
      </div>
      <span className="text-[10px] text-neutral-500 w-4 text-center">{count}</span>
    </div>
  );
}

function AnnotationItem({
  annotation,
  sectionId,
  sectionHeading,
  onDismiss,
  onCreateInquiry,
}: {
  annotation: BriefAnnotation;
  sectionId: string;
  sectionHeading: string;
  onDismiss?: (sectionId: string, annotationId: string) => void;
  onCreateInquiry?: (title: string, sectionId: string) => void;
}) {
  const config = ANNOTATION_CONFIG[annotation.annotation_type];
  const actionConfig = ANNOTATION_ACTIONS[annotation.annotation_type];

  return (
    <div className="flex items-start gap-1.5 text-xs group/ann">
      <span className={cn('flex-shrink-0 mt-0.5 text-[10px]', config.color)}>
        {config.icon}
      </span>
      <div className="flex-1 min-w-0">
        <span className="text-neutral-700 dark:text-neutral-300 text-[11px] leading-tight">
          {annotation.description}
        </span>
        {actionConfig && onCreateInquiry && (
          <div className="mt-0.5 opacity-0 group-hover/ann:opacity-100 transition-opacity">
            <button
              className="text-[9px] px-1.5 py-0.5 rounded border border-accent-200 text-accent-600 hover:bg-accent-50 dark:border-accent-800 dark:text-accent-400 dark:hover:bg-accent-900/20"
              onClick={() => {
                const title = actionConfig.actionType === 'investigate'
                  ? `Investigate: ${annotation.description.slice(0, 80)}`
                  : actionConfig.actionType === 'find_evidence'
                  ? `Find evidence for: ${sectionHeading}`
                  : `Validate: ${annotation.description.slice(0, 80)}`;
                onCreateInquiry(title, sectionId);
              }}
            >
              {actionConfig.label}
            </button>
          </div>
        )}
      </div>
      {onDismiss && (
        <button
          onClick={() => onDismiss(sectionId, annotation.id)}
          className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 flex-shrink-0 opacity-0 group-hover/ann:opacity-100 transition-opacity"
          title="Dismiss"
        >
          &times;
        </button>
      )}
    </div>
  );
}
