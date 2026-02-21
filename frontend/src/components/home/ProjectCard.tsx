/**
 * ProjectCard — summary card for the projects list page.
 *
 * Shows title, description, doc/case counts, hierarchy badge,
 * and relative last-activity time. Follows the cases list card
 * pattern from cases/page.tsx.
 */

'use client';

import { cn, formatRelativeTime } from '@/lib/utils';
import type { Project } from '@/lib/types/project';

interface ProjectCardProps {
  project: Project;
  onClick: () => void;
}

export function ProjectCard({ project, onClick }: ProjectCardProps) {
  const docCount = project.total_documents ?? 0;
  const caseCount = project.total_cases ?? 0;
  const hasMapped = project.has_hierarchy ?? false;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'h-full w-full text-left p-6 rounded-lg border group',
        'border-neutral-200 dark:border-neutral-800',
        'bg-white dark:bg-primary-900',
        'hover:border-accent-500 dark:hover:border-accent-600',
        'transition-all hover:shadow-md',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2',
      )}
    >
      {/* Hierarchy badge */}
      <div className="flex items-center gap-1.5 mb-3">
        <span
          className={cn(
            'w-2 h-2 rounded-full shrink-0',
            hasMapped ? 'bg-success-500' : 'bg-neutral-300 dark:bg-neutral-600',
          )}
        />
        <span
          className={cn(
            'text-xs font-medium',
            hasMapped
              ? 'text-success-600 dark:text-success-400'
              : 'text-neutral-400 dark:text-neutral-500',
          )}
        >
          {hasMapped ? 'Mapped' : 'Unmapped'}
        </span>
      </div>

      {/* Title */}
      <h3 className="font-semibold text-primary-900 dark:text-primary-50 mb-1 group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors line-clamp-2">
        {project.title}
      </h3>

      {/* Description */}
      {project.description && (
        <p className="text-sm text-primary-600 dark:text-primary-400 line-clamp-2 mb-3">
          {project.description}
        </p>
      )}

      {/* Stats row */}
      <div className="flex items-center gap-2 text-xs text-primary-500 dark:text-primary-500 mt-auto pt-3">
        <span className="tabular-nums">{docCount} {docCount === 1 ? 'doc' : 'docs'}</span>
        <span className="text-neutral-300 dark:text-neutral-600">&middot;</span>
        <span className="tabular-nums">{caseCount} {caseCount === 1 ? 'case' : 'cases'}</span>
      </div>

      {/* Last activity */}
      <div className="text-xs text-primary-500 dark:text-primary-500 mt-1">
        Updated {formatRelativeTime(project.updated_at)}
      </div>
    </button>
  );
}
