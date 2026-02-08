/**
 * SkillPicker — choose a skill pack or individual skill before case creation.
 *
 * Shown as the first step of the scaffolding flow. The user can:
 * 1. Pick a starter pack (e.g. "Consulting Starter Pack")
 * 2. Pick an individual skill
 * 3. "Start from scratch" — skip directly to the Socratic interview
 */

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { skillPacksAPI, skillsAPI } from '@/lib/api/skills';
import type { SkillPackListItem, Skill } from '@/lib/types/skill';

interface SkillPickerProps {
  /** Called when user selects a pack */
  onSelectPack: (slug: string) => void;
  /** Called when user selects an individual skill */
  onSelectSkill: (skillId: string) => void;
  /** Called when user skips (start from scratch) */
  onSkip: () => void;
  className?: string;
}

const INITIAL_SKILLS_SHOWN = 6;

export function SkillPicker({
  onSelectPack,
  onSelectSkill,
  onSkip,
  className,
}: SkillPickerProps) {
  const [showAllSkills, setShowAllSkills] = useState(false);

  const packsQuery = useQuery({
    queryKey: ['skill-packs'],
    queryFn: () => skillPacksAPI.list(),
    staleTime: 60_000,
  });

  const skillsQuery = useQuery({
    queryKey: ['skills-active'],
    queryFn: async () => {
      const all = await skillsAPI.list();
      return all.filter((s: Skill) => s.status === 'active');
    },
    staleTime: 60_000,
  });

  const loading = packsQuery.isLoading || skillsQuery.isLoading;
  const error = packsQuery.error || skillsQuery.error;
  const packs = packsQuery.data ?? [];
  const skills = skillsQuery.data ?? [];

  if (loading) {
    return (
      <div
        className={cn('flex items-center justify-center py-12', className)}
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
          <LoadingDots />
          <span>Loading templates...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={cn('flex flex-col items-center gap-3 py-12', className)}
        role="alert"
      >
        <p className="text-sm text-red-500">
          {(error as Error).message || 'Failed to load templates'}
        </p>
        <button
          onClick={onSkip}
          className="text-sm text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400 rounded"
        >
          Start from scratch instead
        </button>
      </div>
    );
  }

  const hasPacks = packs.length > 0;
  const hasSkills = skills.length > 0;
  const isEmpty = !hasPacks && !hasSkills;

  const visibleSkills = showAllSkills ? skills : skills.slice(0, INITIAL_SKILLS_SHOWN);
  const hasMoreSkills = skills.length > INITIAL_SKILLS_SHOWN;

  return (
    <div className={cn('flex flex-col gap-4 py-4', className)}>
      {/* Header */}
      <div className="text-center px-4">
        <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">
          Start with a template
        </h3>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
          Choose a starter pack or skill to pre-configure your case, or skip to start fresh.
        </p>
      </div>

      {/* Empty state */}
      {isEmpty && (
        <div className="text-center px-4 py-6">
          <p className="text-xs text-neutral-400 dark:text-neutral-500">
            No templates available yet. Start from scratch to create your first case.
          </p>
        </div>
      )}

      {/* Packs */}
      {hasPacks && (
        <div className="flex flex-col gap-2 px-4" role="group" aria-label="Starter Packs">
          <span className="text-[10px] uppercase tracking-wider font-medium text-neutral-400 dark:text-neutral-500">
            Starter Packs
          </span>
          {packs.map(pack => (
            <button
              key={pack.slug}
              onClick={() => onSelectPack(pack.slug)}
              aria-label={`Use ${pack.name} with ${pack.skill_count} skills`}
              className="flex items-start gap-3 p-3 text-left rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 hover:border-accent-300 dark:hover:border-accent-700 hover:bg-accent-50/30 dark:hover:bg-accent-900/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400 transition-colors group"
            >
              <span className="text-lg leading-none mt-0.5" aria-hidden="true">{pack.icon || '\uD83D\uDCE6'}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200 group-hover:text-accent-700 dark:group-hover:text-accent-300 transition-colors">
                    {pack.name}
                  </span>
                  <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
                    {pack.skill_count} skill{pack.skill_count !== 1 ? 's' : ''}
                  </span>
                </div>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 line-clamp-2">
                  {pack.skill_names.join(' + ')}
                </p>
              </div>
              <span className="text-xs font-medium text-accent-500 dark:text-accent-400 opacity-0 group-hover:opacity-100 transition-opacity self-center" aria-hidden="true">
                Use
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Individual Skills */}
      {hasSkills && (
        <div className="flex flex-col gap-2 px-4" role="group" aria-label="Individual Skills">
          <span className="text-[10px] uppercase tracking-wider font-medium text-neutral-400 dark:text-neutral-500">
            Individual Skills
          </span>
          <div className="grid grid-cols-1 gap-1.5">
            {visibleSkills.map(skill => (
              <button
                key={skill.id}
                onClick={() => onSelectSkill(skill.id)}
                aria-label={`Use ${skill.name}${skill.domain ? ` (${skill.domain})` : ''}`}
                className="flex items-center gap-2 px-3 py-2 text-left rounded-lg border border-neutral-200/60 dark:border-neutral-800/60 hover:border-accent-300 dark:hover:border-accent-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400 transition-colors group"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-neutral-300 dark:bg-neutral-600 group-hover:bg-accent-400 transition-colors flex-shrink-0" aria-hidden="true" />
                <span className="text-sm text-neutral-700 dark:text-neutral-300 group-hover:text-accent-700 dark:group-hover:text-accent-300 transition-colors truncate flex-1">
                  {skill.name}
                </span>
                {skill.domain && (
                  <span className="text-[10px] text-neutral-400 dark:text-neutral-500 flex-shrink-0">
                    {skill.domain}
                  </span>
                )}
              </button>
            ))}
          </div>
          {hasMoreSkills && !showAllSkills && (
            <button
              onClick={() => setShowAllSkills(true)}
              className="text-xs text-neutral-500 dark:text-neutral-400 hover:text-accent-600 dark:hover:text-accent-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400 rounded py-1 transition-colors"
            >
              Show {skills.length - INITIAL_SKILLS_SHOWN} more skills
            </button>
          )}
        </div>
      )}

      {/* Divider + Start from scratch */}
      <div className="flex items-center gap-3 px-4" aria-hidden="true">
        <div className="flex-1 border-t border-neutral-200 dark:border-neutral-800" />
        <span className="text-[10px] text-neutral-400 dark:text-neutral-500">or</span>
        <div className="flex-1 border-t border-neutral-200 dark:border-neutral-800" />
      </div>

      <div className="px-4">
        <button
          onClick={onSkip}
          className="w-full py-2.5 text-sm font-medium text-neutral-600 dark:text-neutral-400 rounded-xl border border-dashed border-neutral-300 dark:border-neutral-700 hover:border-neutral-400 dark:hover:border-neutral-600 hover:text-neutral-800 dark:hover:text-neutral-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400 transition-colors"
        >
          Start from scratch
        </button>
      </div>
    </div>
  );
}

function LoadingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden="true">
      <span className="w-1 h-1 rounded-full bg-neutral-400 animate-bounce [animation-delay:0ms]" />
      <span className="w-1 h-1 rounded-full bg-neutral-400 animate-bounce [animation-delay:150ms]" />
      <span className="w-1 h-1 rounded-full bg-neutral-400 animate-bounce [animation-delay:300ms]" />
    </span>
  );
}

export default SkillPicker;
