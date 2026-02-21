/**
 * ConciergeCard
 *
 * Polymorphic card component for the project home concierge page.
 * Each card represents a system-recommended action or insight.
 *
 * Variants control visual styling:
 *   warning — amber (decision at risk)
 *   accent  — purple (worth exploring)
 *   info    — blue (needs attention, orientation shift)
 *   neutral — gray (resume work)
 *   action  — green (get started)
 */

'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import type { ConciergeCard as ConciergeCardType, ConciergeCardVariant } from '@/lib/types/concierge';

const variantStyles: Record<ConciergeCardVariant, { border: string; icon: string; bg: string }> = {
  warning: {
    border: 'border-warning-200 dark:border-warning-800',
    icon: 'text-warning-500',
    bg: 'hover:bg-warning-50 dark:hover:bg-warning-950/30',
  },
  accent: {
    border: 'border-accent-200 dark:border-accent-800',
    icon: 'text-accent-500',
    bg: 'hover:bg-accent-50 dark:hover:bg-accent-950/30',
  },
  info: {
    border: 'border-info-200 dark:border-info-800',
    icon: 'text-info-500',
    bg: 'hover:bg-info-50 dark:hover:bg-info-950/30',
  },
  neutral: {
    border: 'border-neutral-200 dark:border-neutral-700',
    icon: 'text-neutral-400',
    bg: 'hover:bg-neutral-50 dark:hover:bg-neutral-800/50',
  },
  action: {
    border: 'border-success-200 dark:border-success-800',
    icon: 'text-success-500',
    bg: 'hover:bg-success-50 dark:hover:bg-success-950/30',
  },
};

const typeIcons: Record<string, string> = {
  decision_at_risk: '⚠',
  worth_exploring: '💡',
  case_needs_attention: '◆',
  resume_work: '↩',
  orientation_shift: '🧭',
  get_started: '→',
};

interface ConciergeCardProps {
  card: ConciergeCardType;
  onClick?: () => void;
}

export function ConciergeCard({ card, onClick }: ConciergeCardProps) {
  const styles = variantStyles[card.variant];
  const icon = typeIcons[card.type] || '•';

  const content = (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-lg border transition-colors duration-150 cursor-pointer',
        styles.border,
        styles.bg,
        'bg-white dark:bg-neutral-900'
      )}
    >
      <span className={cn('text-lg shrink-0 mt-0.5', styles.icon)}>{icon}</span>
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
          {card.title}
        </h3>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 line-clamp-2">
          {card.subtitle}
        </p>
      </div>
      <ChevronRight className="w-4 h-4 text-neutral-300 dark:text-neutral-600 shrink-0 mt-1" />
    </div>
  );

  // Cards with href="#upload" are handled via onClick, not navigation
  if (card.href.startsWith('#') || onClick) {
    return (
      <button onClick={onClick} className="w-full text-left">
        {content}
      </button>
    );
  }

  return (
    <Link href={card.href} className="block">
      {content}
    </Link>
  );
}

function ChevronRight({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
