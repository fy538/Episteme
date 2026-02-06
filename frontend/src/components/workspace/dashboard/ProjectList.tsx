/**
 * Project List
 *
 * Shows projects with their cases and readiness status.
 * Cases are expandable to show inquiries.
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ReadinessMeter } from '@/components/ui/readiness-meter';
import type { Project } from '@/lib/types/project';
import type { Case, Inquiry } from '@/lib/types/case';

interface ProjectWithCases extends Project {
  cases: CaseWithInquiries[];
}

interface CaseWithInquiries extends Case {
  inquiries: Inquiry[];
  readinessScore: number;
  tensionsCount: number;
  blindSpotsCount: number;
}

interface ProjectListProps {
  projects: ProjectWithCases[];
  className?: string;
}

export function ProjectList({ projects, className }: ProjectListProps) {
  if (projects.length === 0) {
    return (
      <div className={cn('text-center py-12', className)}>
        <p className="text-neutral-500 dark:text-neutral-400 mb-4">
          No projects yet
        </p>
        <Button>Create Your First Project</Button>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} />
      ))}

      <Button variant="outline" className="w-full">
        <PlusIcon className="w-4 h-4 mr-2" />
        New Project
      </Button>
    </div>
  );
}

function ProjectCard({ project }: { project: ProjectWithCases }) {
  const [expanded, setExpanded] = useState(true); // Default expanded

  // Calculate project stats
  const totalCases = project.cases.length;
  const readyCases = project.cases.filter(c => c.readinessScore >= 90 && c.tensionsCount === 0).length;

  return (
    <div className="border border-neutral-200 dark:border-neutral-800 rounded-xl overflow-hidden">
      {/* Project Header */}
      <Link
        href={`/workspace/projects/${project.id}`}
        className="flex items-center justify-between p-4 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-100 dark:bg-accent-900/30 flex items-center justify-center">
            <FolderIcon className="w-4 h-4 text-accent-600 dark:text-accent-400" />
          </div>
          <div>
            <h3 className="font-semibold text-primary-900 dark:text-primary-50">
              {project.title}
            </h3>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              {readyCases}/{totalCases} cases ready
            </p>
          </div>
        </div>

        <button
          onClick={(e) => {
            e.preventDefault();
            setExpanded(!expanded);
          }}
          className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded"
        >
          <ChevronIcon
            className={cn(
              'w-5 h-5 text-neutral-400 transition-transform',
              expanded && 'rotate-90'
            )}
          />
        </button>
      </Link>

      {/* Cases */}
      {expanded && project.cases.length > 0 && (
        <div className="border-t border-neutral-100 dark:border-neutral-800">
          {project.cases.map((caseItem, index) => (
            <CaseRow
              key={caseItem.id}
              caseItem={caseItem}
              isLast={index === project.cases.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CaseRow({
  caseItem,
  isLast,
}: {
  caseItem: CaseWithInquiries;
  isLast: boolean;
}) {
  const [showInquiries, setShowInquiries] = useState(false);

  const isReady = caseItem.readinessScore >= 90 && caseItem.tensionsCount === 0;
  const resolvedInquiries = caseItem.inquiries.filter(i => i.status === 'resolved').length;

  return (
    <div
      className={cn(
        'border-b border-neutral-100 dark:border-neutral-800',
        isLast && 'border-b-0'
      )}
    >
      {/* Case Header */}
      <div className="flex items-center gap-3 px-4 py-3 pl-8">
        {/* Expand toggle */}
        {caseItem.inquiries.length > 0 ? (
          <button
            onClick={() => setShowInquiries(!showInquiries)}
            className="p-0.5 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded"
          >
            <ChevronIcon
              className={cn(
                'w-4 h-4 text-neutral-400 transition-transform',
                showInquiries && 'rotate-90'
              )}
            />
          </button>
        ) : (
          <div className="w-5" />
        )}

        {/* Case info */}
        <Link
          href={`/workspace/cases/${caseItem.id}`}
          className="flex-1 flex items-center justify-between hover:bg-neutral-50 dark:hover:bg-neutral-800/30 -mx-2 px-2 py-1 rounded transition-colors"
        >
          <div className="flex items-center gap-2">
            {isReady ? (
              <CheckCircleIcon className="w-4 h-4 text-success-500" />
            ) : (
              <CircleIcon className="w-4 h-4 text-neutral-300 dark:text-neutral-600" />
            )}
            <span className="text-sm font-medium text-primary-900 dark:text-primary-50">
              {caseItem.title}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Status indicators */}
            {caseItem.tensionsCount > 0 && (
              <span className="text-xs text-warning-600 dark:text-warning-400">
                {caseItem.tensionsCount} tension{caseItem.tensionsCount !== 1 ? 's' : ''}
              </span>
            )}
            {caseItem.blindSpotsCount > 0 && (
              <span className="text-xs text-accent-600 dark:text-accent-400">
                {caseItem.blindSpotsCount} blind spot{caseItem.blindSpotsCount !== 1 ? 's' : ''}
              </span>
            )}

            {/* Readiness */}
            <ReadinessMeter
              score={caseItem.readinessScore}
              inquiries={{
                total: caseItem.inquiries.length,
                resolved: resolvedInquiries,
              }}
              variant="minimal"
            />
          </div>
        </Link>
      </div>

      {/* Inquiries */}
      {showInquiries && caseItem.inquiries.length > 0 && (
        <div className="pl-16 pr-4 pb-3 space-y-1">
          {caseItem.inquiries.map((inquiry) => (
            <InquiryRow key={inquiry.id} inquiry={inquiry} caseId={caseItem.id} />
          ))}
        </div>
      )}
    </div>
  );
}

function InquiryRow({ inquiry, caseId }: { inquiry: Inquiry; caseId: string }) {
  const isResolved = inquiry.status === 'resolved';

  return (
    <Link
      href={`/workspace/cases/${caseId}?inquiry=${inquiry.id}`}
      className="flex items-center gap-2 py-1.5 px-2 -mx-2 rounded hover:bg-neutral-50 dark:hover:bg-neutral-800/30 transition-colors"
    >
      {isResolved ? (
        <CheckIcon className="w-3.5 h-3.5 text-success-500" />
      ) : (
        <CircleSmallIcon className="w-3.5 h-3.5 text-neutral-300 dark:text-neutral-600" />
      )}
      <span
        className={cn(
          'text-sm',
          isResolved
            ? 'text-neutral-500 dark:text-neutral-400'
            : 'text-primary-900 dark:text-primary-50'
        )}
      >
        {inquiry.title}
      </span>
      {inquiry.status === 'investigating' && (
        <span className="text-xs text-accent-600 dark:text-accent-400">
          investigating
        </span>
      )}
    </Link>
  );
}

// Icons
function FolderIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
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

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CircleSmallIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="4" />
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

export default ProjectList;
