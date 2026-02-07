/**
 * Insight Cards Grid
 *
 * 3-column grid of article cards or suggested prompt placeholders.
 * Articles come from useTodaysBrief; placeholders fill remaining slots.
 * Clicking a placeholder pre-fills the hero input.
 */

'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import type { BriefArticle } from '@/hooks/useTodaysBrief';

interface ArticleCarouselProps {
  articles: BriefArticle[];
  onPromptClick?: (prompt: string) => void;
  className?: string;
}

const typeLabels: Record<BriefArticle['type'], string> = {
  tension_digest: 'Tensions',
  progress_update: 'Progress',
  cross_case_pattern: 'Patterns',
};

const typeColors: Record<BriefArticle['type'], string> = {
  tension_digest: 'text-warning-600 dark:text-warning-400',
  progress_update: 'text-success-600 dark:text-success-400',
  cross_case_pattern: 'text-accent-600 dark:text-accent-400',
};

// Placeholder prompts when fewer than 3 articles
const PLACEHOLDER_PROMPTS = [
  {
    label: 'Explore',
    labelColor: 'text-accent-600 dark:text-accent-400',
    title: 'Compare my top options',
    subtitle: 'Weigh trade-offs across your active decisions',
    icon: LightbulbIcon,
    prompt: 'Compare my top options and help me weigh the trade-offs',
  },
  {
    label: 'Prioritize',
    labelColor: 'text-warning-600 dark:text-warning-400',
    title: 'What should I focus on?',
    subtitle: 'Surface the highest-impact next step',
    icon: TargetIcon,
    prompt: 'What should I prioritize right now across my cases?',
  },
  {
    label: 'Connect',
    labelColor: 'text-success-600 dark:text-success-400',
    title: 'Find cross-case patterns',
    subtitle: 'Discover shared evidence and themes',
    icon: LinkIcon,
    prompt: 'Are there patterns or connections across my cases?',
  },
];

export function ArticleCarousel({ articles, onPromptClick, className }: ArticleCarouselProps) {
  // Fill to 3 cards: articles first, then placeholders
  const placeholdersNeeded = Math.max(0, 3 - articles.length);
  const placeholders = PLACEHOLDER_PROMPTS.slice(0, placeholdersNeeded);

  return (
    <div className={cn('grid grid-cols-3 gap-3', className)}>
      {articles.map((article) => (
        <ArticleCard key={article.id} article={article} />
      ))}
      {placeholders.map((ph, i) => (
        <PlaceholderCard
          key={`ph-${i}`}
          placeholder={ph}
          onClick={() => onPromptClick?.(ph.prompt)}
        />
      ))}
    </div>
  );
}

function ArticleCard({ article }: { article: BriefArticle }) {
  return (
    <Link
      href={`/cases/${article.caseId}`}
      className={cn(
        'group flex flex-col h-[132px] p-4 rounded-lg transition-colors',
        'border border-neutral-200/60 dark:border-neutral-700/40',
        'hover:border-neutral-300/80 dark:hover:border-neutral-600/60',
        'bg-white dark:bg-neutral-900/50',
      )}
    >
      <span className={cn('text-[11px] font-medium uppercase tracking-wider', typeColors[article.type])}>
        {typeLabels[article.type]}
      </span>
      <h4 className="text-sm font-medium text-primary-900 dark:text-primary-50 mt-2 line-clamp-2 leading-snug">
        {article.title}
      </h4>
      <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
        {article.subtitle}
      </p>
      <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-auto line-clamp-2 leading-relaxed">
        {article.snippet}
      </p>
    </Link>
  );
}

function PlaceholderCard({
  placeholder,
  onClick,
}: {
  placeholder: typeof PLACEHOLDER_PROMPTS[number];
  onClick: () => void;
}) {
  const Icon = placeholder.icon;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'group flex flex-col h-[132px] p-4 rounded-lg transition-colors text-left',
        'border border-dashed border-neutral-200/80 dark:border-neutral-700/50',
        'hover:border-neutral-300 dark:hover:border-neutral-600',
        'hover:bg-neutral-50/80 dark:hover:bg-neutral-800/30',
      )}
    >
      <div className="flex items-center gap-1.5">
        <Icon className={cn('w-3 h-3', placeholder.labelColor)} />
        <span className={cn('text-[11px] font-medium uppercase tracking-wider', placeholder.labelColor)}>
          {placeholder.label}
        </span>
      </div>
      <h4 className="text-sm font-medium text-primary-900 dark:text-primary-50 mt-2 leading-snug">
        {placeholder.title}
      </h4>
      <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-auto leading-relaxed">
        {placeholder.subtitle}
      </p>
    </button>
  );
}

// --- Icons ---

function LightbulbIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 18h6M10 22h4" strokeLinecap="round" />
      <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A7 7 0 1 0 7.5 11.5c.76.76 1.23 1.52 1.41 2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function TargetIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  );
}

function LinkIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
