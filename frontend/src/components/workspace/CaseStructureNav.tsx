/**
 * CaseStructureNav
 *
 * Left column tree navigation for the case workspace.
 * Shows plan phases with nested inquiries, assumptions, criteria.
 * Falls back to simplified nav when no plan exists.
 *
 * Uses Framer Motion expand/collapse patterns.
 */

'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { transitionDurations } from '@/lib/motion-config';
import { cn } from '@/lib/utils';
import type { InvestigationPlan } from '@/lib/types/plan';
import type { Inquiry } from '@/lib/types/case';
import type { ActiveSkillSummary } from '@/lib/types/skill';
import type { ViewMode } from '@/hooks/useCaseWorkspace';

interface CaseStructureNavProps {
  caseId: string;
  caseTitle: string;
  plan: InvestigationPlan | null;
  inquiries: Inquiry[];
  documentCount?: number;
  viewMode: ViewMode;
  activeInquiryId: string | null;
  onNavigate: (mode: ViewMode, inquiryId?: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  activeSkills?: ActiveSkillSummary[];
  hideCollapseToggle?: boolean;
}

export function CaseStructureNav({
  caseId,
  caseTitle,
  plan,
  inquiries,
  documentCount = 0,
  viewMode,
  activeInquiryId,
  onNavigate,
  isCollapsed,
  onToggleCollapse,
  activeSkills,
  hideCollapseToggle,
}: CaseStructureNavProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['phases', 'assumptions', 'criteria'])
  );
  const prefersReducedMotion = useReducedMotion();

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  };

  const content = plan?.current_content;
  const phases = content?.phases ?? [];
  const assumptions = content?.assumptions ?? [];
  const criteria = content?.decision_criteria ?? [];

  // Count assumption statuses
  const confirmedCount = assumptions.filter(a => a.status === 'confirmed').length;
  const metCount = criteria.filter(c => c.is_met).length;

  // Build a set of inquiry IDs that are in the plan for quick lookup
  const planInquiryIds = new Set(phases.flatMap(p => p.inquiry_ids));

  // Map inquiry IDs to inquiry data
  const inquiryMap = new Map(inquiries.map(i => [i.id, i]));

  const motionProps = prefersReducedMotion
    ? {}
    : {
        initial: { height: 0, opacity: 0 },
        animate: { height: 'auto', opacity: 1 },
        exit: { height: 0, opacity: 0 },
        transition: { duration: transitionDurations.fast },
      };

  return (
    <nav className="flex flex-col h-full bg-neutral-50/50 dark:bg-neutral-950/50" aria-label="Case structure">
      {/* Case title */}
      <div className="px-3 py-3 border-b border-neutral-200/60 dark:border-neutral-800/60">
        <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">
          {caseTitle}
        </h2>
        {plan && (
          <span className="text-[10px] uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mt-0.5 block">
            {plan.stage}
          </span>
        )}
        {/* Active skill chips */}
        {activeSkills && activeSkills.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {activeSkills.map(skill => (
              <span
                key={skill.id}
                title={skill.name}
                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded-md bg-accent-50 dark:bg-accent-900/20 text-accent-600 dark:text-accent-400 border border-accent-200/50 dark:border-accent-800/50 truncate max-w-[120px]"
              >
                <span className="w-1 h-1 rounded-full bg-accent-400 dark:bg-accent-500 flex-shrink-0" />
                {skill.name}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Nav items */}
      <div className="flex-1 overflow-y-auto py-2">
        {/* Primary nav items */}
        <NavItem
          icon={<HomeIcon />}
          label="Home"
          isActive={viewMode === 'home'}
          onClick={() => onNavigate('home')}
        />
        <NavItem
          icon={<DocIcon />}
          label="Brief"
          isActive={viewMode === 'brief'}
          onClick={() => onNavigate('brief')}
        />
        <NavItem
          icon={<UploadIcon />}
          label="Documents"
          badge={documentCount > 0 ? documentCount : undefined}
          isActive={viewMode === 'document'}
          onClick={() => onNavigate('document')}
        />

        {/* Plan-dependent sections */}
        {plan && content && (
          <>
            {/* Separator */}
            <div className="mx-3 my-2 border-t border-neutral-200/60 dark:border-neutral-800/60" />

            {/* Phases + Inquiries */}
            {phases.length > 0 && (
              <SectionHeader
                label="Investigation"
                isExpanded={expandedSections.has('phases')}
                onToggle={() => toggleSection('phases')}
              />
            )}
            <AnimatePresence initial={false}>
              {expandedSections.has('phases') && phases.map(phase => (
                <motion.div key={phase.id} {...motionProps} className="overflow-hidden">
                  <div className="px-3 py-1">
                    <span className="text-[10px] uppercase tracking-wider text-neutral-400 dark:text-neutral-500 font-medium">
                      {phase.title}
                    </span>
                  </div>
                  {phase.inquiry_ids.map(inquiryId => {
                    const inquiry = inquiryMap.get(inquiryId);
                    if (!inquiry) return null;
                    return (
                      <NavItem
                        key={inquiryId}
                        icon={<InquiryStatusIcon status={inquiry.status} />}
                        label={inquiry.title}
                        isActive={viewMode === 'inquiry' && activeInquiryId === inquiryId}
                        onClick={() => onNavigate('inquiry', inquiryId)}
                        indent
                      />
                    );
                  })}
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Orphan inquiries not in any phase */}
            {inquiries.filter(i => !planInquiryIds.has(i.id)).length > 0 && (
              <>
                {inquiries.filter(i => !planInquiryIds.has(i.id)).map(inquiry => (
                  <NavItem
                    key={inquiry.id}
                    icon={<InquiryStatusIcon status={inquiry.status} />}
                    label={inquiry.title}
                    isActive={viewMode === 'inquiry' && activeInquiryId === inquiry.id}
                    onClick={() => onNavigate('inquiry', inquiry.id)}
                    indent
                  />
                ))}
              </>
            )}

            {/* Assumptions */}
            {assumptions.length > 0 && (
              <>
                <div className="mx-3 my-2 border-t border-neutral-200/60 dark:border-neutral-800/60" />
                <SectionHeader
                  label={`Assumptions${assumptions.length > 0 ? ` (${confirmedCount}/${assumptions.length})` : ''}`}
                  isExpanded={expandedSections.has('assumptions')}
                  onToggle={() => toggleSection('assumptions')}
                />
                <AnimatePresence initial={false}>
                  {expandedSections.has('assumptions') && (
                    <motion.div {...motionProps} className="overflow-hidden">
                      {assumptions.map(a => (
                        <div
                          key={a.id}
                          className="flex items-start gap-2 px-3 py-1.5 pl-5"
                        >
                          <AssumptionStatusIcon status={a.status} />
                          <span className="text-xs text-neutral-600 dark:text-neutral-400 leading-tight line-clamp-2">
                            {a.text}
                          </span>
                        </div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </>
            )}

            {/* Decision Criteria */}
            {criteria.length > 0 && (
              <>
                <div className="mx-3 my-2 border-t border-neutral-200/60 dark:border-neutral-800/60" />
                <SectionHeader
                  label={`Criteria${criteria.length > 0 ? ` (${metCount}/${criteria.length})` : ''}`}
                  isExpanded={expandedSections.has('criteria')}
                  onToggle={() => toggleSection('criteria')}
                />
                <AnimatePresence initial={false}>
                  {expandedSections.has('criteria') && (
                    <motion.div {...motionProps} className="overflow-hidden">
                      {criteria.map(c => (
                        <div
                          key={c.id}
                          className="flex items-start gap-2 px-3 py-1.5 pl-5"
                        >
                          <span className={cn(
                            'mt-0.5 shrink-0',
                            c.is_met ? 'text-emerald-500' : 'text-neutral-300 dark:text-neutral-600'
                          )}>
                            {c.is_met ? (
                              <CheckIcon className="w-3.5 h-3.5" />
                            ) : (
                              <CircleIcon className="w-3.5 h-3.5" />
                            )}
                          </span>
                          <span className={cn(
                            'text-xs leading-tight line-clamp-2',
                            c.is_met
                              ? 'text-neutral-500 dark:text-neutral-400'
                              : 'text-neutral-600 dark:text-neutral-400'
                          )}>
                            {c.text}
                          </span>
                        </div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </>
            )}
          </>
        )}

        {/* Inquiries without plan (fallback) */}
        {!plan && inquiries.length > 0 && (
          <>
            <div className="mx-3 my-2 border-t border-neutral-200/60 dark:border-neutral-800/60" />
            <SectionHeader
              label="Inquiries"
              isExpanded={expandedSections.has('phases')}
              onToggle={() => toggleSection('phases')}
            />
            <AnimatePresence initial={false}>
              {expandedSections.has('phases') && (
                <motion.div {...motionProps} className="overflow-hidden">
                  {inquiries.map(inquiry => (
                    <NavItem
                      key={inquiry.id}
                      icon={<InquiryStatusIcon status={inquiry.status} />}
                      label={inquiry.title}
                      isActive={viewMode === 'inquiry' && activeInquiryId === inquiry.id}
                      onClick={() => onNavigate('inquiry', inquiry.id)}
                      indent
                    />
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </div>

      {/* Bottom nav items */}
      <div className="border-t border-neutral-200/60 dark:border-neutral-800/60 py-2">
        <NavItem
          icon={<ResearchIcon />}
          label="Research"
          isActive={viewMode === 'inquiry-dashboard'}
          onClick={() => onNavigate('inquiry-dashboard')}
        />
        <NavItem
          icon={<ReadinessIcon />}
          label="Readiness"
          isActive={viewMode === 'readiness'}
          onClick={() => onNavigate('readiness')}
        />
      </div>

      {/* Collapse toggle */}
      {!hideCollapseToggle && (
        <button
          onClick={onToggleCollapse}
          className="flex items-center justify-center py-2 border-t border-neutral-200/60 dark:border-neutral-800/60 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
          title={isCollapsed ? 'Expand nav' : 'Collapse nav'}
        >
          <CollapseIcon className="w-4 h-4" />
        </button>
      )}
    </nav>
  );
}

// ─── Sub-components ────────────────────────────────────────

function NavItem({
  icon,
  label,
  badge,
  isActive,
  onClick,
  indent = false,
}: {
  icon: React.ReactNode;
  label: string;
  badge?: number;
  isActive: boolean;
  onClick: () => void;
  indent?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 w-full text-left text-xs py-1.5 rounded-md transition-colors',
        indent ? 'px-5' : 'px-3',
        isActive
          ? 'bg-accent-100/60 dark:bg-accent-900/20 text-accent-700 dark:text-accent-300 font-medium'
          : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800/50 hover:text-neutral-800 dark:hover:text-neutral-200'
      )}
    >
      <span className="shrink-0">{icon}</span>
      <span className="truncate flex-1">{label}</span>
      {badge !== undefined && (
        <span className="text-[10px] text-neutral-400 dark:text-neutral-500 tabular-nums">
          {badge}
        </span>
      )}
    </button>
  );
}

function SectionHeader({
  label,
  isExpanded,
  onToggle,
}: {
  label: string;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      aria-expanded={isExpanded}
      className="flex items-center gap-1.5 w-full px-3 py-1.5 text-left text-[10px] uppercase tracking-wider font-medium text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400 rounded transition-colors"
    >
      <ChevronIcon className={cn('w-3 h-3 transition-transform', isExpanded && 'rotate-90')} />
      {label}
    </button>
  );
}

function InquiryStatusIcon({ status }: { status: string }) {
  if (status === 'resolved') {
    return <CheckCircleIcon className="w-3.5 h-3.5 text-emerald-500" />;
  }
  if (status === 'investigating') {
    return <LoadingIcon className="w-3.5 h-3.5 text-accent-500" />;
  }
  return <CircleIcon className="w-3.5 h-3.5 text-neutral-300 dark:text-neutral-600" />;
}

function AssumptionStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'confirmed':
      return <CheckIcon className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />;
    case 'challenged':
      return <WarningIcon className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />;
    case 'refuted':
      return <XIcon className="w-3.5 h-3.5 text-red-500 shrink-0 mt-0.5" />;
    default: // untested
      return <QuestionIcon className="w-3.5 h-3.5 text-neutral-400 shrink-0 mt-0.5" />;
  }
}

// ─── Icons ────────────────────────────────────────

function HomeIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="9 22 9 12 15 12 15 22" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DocIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" strokeLinecap="round" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="17 8 12 3 7 8" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="12" y1="3" x2="12" y2="15" strokeLinecap="round" />
    </svg>
  );
}

function ResearchIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <path d="M21 21l-4.35-4.35" strokeLinecap="round" />
    </svg>
  );
}

function ReadinessIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 11.08V12a10 10 0 11-5.93-9.14" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="22 4 12 14.01 9 11.01" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="9 18 15 12 9 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CollapseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="11 17 6 12 11 7" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="18 17 13 12 18 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
    </svg>
  );
}

function LoadingIcon({ className }: { className?: string }) {
  return (
    <svg className={cn(className, 'animate-spin')} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 019.17 6" strokeLinecap="round" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="20 6 9 17 4 12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" strokeLinecap="round" />
      <line x1="12" y1="17" x2="12.01" y2="17" strokeLinecap="round" />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="18" y1="6" x2="6" y2="18" strokeLinecap="round" />
      <line x1="6" y1="6" x2="18" y2="18" strokeLinecap="round" />
    </svg>
  );
}

function QuestionIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="12" y1="17" x2="12.01" y2="17" strokeLinecap="round" />
    </svg>
  );
}

