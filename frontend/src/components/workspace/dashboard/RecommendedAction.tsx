/**
 * Recommended Action Card
 *
 * The ONE action that matters most right now.
 * Displays differently based on action type (tension, blind spot, etc.)
 */

'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { IntelligenceItem } from '@/lib/types/intelligence';

interface RecommendedActionProps {
  item: IntelligenceItem;
  variant?: 'default' | 'detailed';
  /**
   * Called when user clicks the action button.
   * Receives the item so parent can decide what to do based on type.
   */
  onAction?: (item: IntelligenceItem) => void;
  onDismiss?: () => void;
  className?: string;
}

export function RecommendedAction({
  item,
  variant = 'default',
  onAction,
  onDismiss,
  className,
}: RecommendedActionProps) {
  // Get styles based on type
  const getTypeStyles = () => {
    switch (item.type) {
      case 'tension':
        return {
          icon: TensionIcon,
          iconBg: 'bg-warning-100 dark:bg-warning-900/30',
          iconColor: 'text-warning-600 dark:text-warning-400',
          border: 'border-warning-200 dark:border-warning-800',
          label: 'Tension',
        };
      case 'blind_spot':
        return {
          icon: BlindSpotIcon,
          iconBg: 'bg-accent-100 dark:bg-accent-900/30',
          iconColor: 'text-accent-600 dark:text-accent-400',
          border: 'border-accent-200 dark:border-accent-800',
          label: 'Blind Spot',
        };
      case 'explore':
        return {
          icon: ExploreIcon,
          iconBg: 'bg-primary-100 dark:bg-primary-900/30',
          iconColor: 'text-primary-600 dark:text-primary-400',
          border: 'border-primary-200 dark:border-primary-800',
          label: 'Worth Exploring',
        };
      case 'research_ready':
        return {
          icon: ResearchIcon,
          iconBg: 'bg-success-100 dark:bg-success-900/30',
          iconColor: 'text-success-600 dark:text-success-400',
          border: 'border-success-200 dark:border-success-800',
          label: 'Research Ready',
        };
      case 'ready':
        return {
          icon: ReadyIcon,
          iconBg: 'bg-success-100 dark:bg-success-900/30',
          iconColor: 'text-success-600 dark:text-success-400',
          border: 'border-success-200 dark:border-success-800',
          label: 'Ready for Review',
        };
      default:
        return {
          icon: DefaultIcon,
          iconBg: 'bg-neutral-100 dark:bg-neutral-800',
          iconColor: 'text-neutral-600 dark:text-neutral-400',
          border: 'border-neutral-200 dark:border-neutral-700',
          label: 'Action',
        };
    }
  };

  const styles = getTypeStyles();
  const Icon = styles.icon;

  // Build breadcrumb
  const breadcrumb = [item.projectTitle, item.caseTitle, item.inquiryTitle]
    .filter(Boolean)
    .join(' · ');

  // Get action button text
  const getActionText = () => {
    switch (item.type) {
      case 'tension':
        return 'Resolve This';
      case 'blind_spot':
        return 'Address This';
      case 'explore':
        return 'Explore';
      case 'research_ready':
        return 'Review Research';
      case 'ready':
        return 'Review Case';
      default:
        return 'Open';
    }
  };

  // Build link href
  const getHref = () => {
    if (item.caseId) {
      return `/workspace/cases/${item.caseId}`;
    }
    if (item.projectId) {
      return `/workspace/projects/${item.projectId}`;
    }
    return '/workspace';
  };

  return (
    <div
      className={cn(
        'rounded-xl border bg-white dark:bg-neutral-900 p-5 transition-all',
        styles.border,
        'hover:shadow-md',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className={cn('p-2.5 rounded-lg shrink-0', styles.iconBg)}>
          <Icon className={cn('w-5 h-5', styles.iconColor)} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Breadcrumb */}
          {breadcrumb && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-1">
              {breadcrumb}
            </p>
          )}

          {/* Title */}
          <h3 className="font-semibold text-primary-900 dark:text-primary-50 mb-1">
            {item.title}
          </h3>

          {/* Description */}
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            {item.description}
          </p>

          {/* Detailed variant: show tension sources */}
          {variant === 'detailed' && item.type === 'tension' && item.tension && (
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                  {item.tension.sourceA.name}
                </p>
                <p className="text-sm text-neutral-700 dark:text-neutral-300 line-clamp-2">
                  {item.tension.sourceA.content}
                </p>
                {item.tension.sourceA.implication && (
                  <p className="text-xs text-neutral-500 mt-1">
                    → {item.tension.sourceA.implication}
                  </p>
                )}
              </div>
              <div className="p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                  {item.tension.sourceB.name}
                </p>
                <p className="text-sm text-neutral-700 dark:text-neutral-300 line-clamp-2">
                  {item.tension.sourceB.content}
                </p>
                {item.tension.sourceB.implication && (
                  <p className="text-xs text-neutral-500 mt-1">
                    → {item.tension.sourceB.implication}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Detailed variant: show blind spot impact */}
          {variant === 'detailed' && item.type === 'blind_spot' && item.blindSpot && (
            <div className="mt-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
              <p className="text-sm text-neutral-700 dark:text-neutral-300">
                <span className="font-medium">Impact:</span> {item.blindSpot.impact}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 mt-4 pt-4 border-t border-neutral-100 dark:border-neutral-800">
        {onDismiss && (
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            Dismiss
          </Button>
        )}
        {onAction ? (
          // When onAction is provided, use it instead of navigation
          <Button
            size="sm"
            onClick={(e) => {
              e.preventDefault();
              onAction(item);
            }}
          >
            {getActionText()}
            <ArrowRightIcon className="w-4 h-4 ml-1" />
          </Button>
        ) : (
          // Fallback to navigation if no onAction provided
          <Link href={getHref()}>
            <Button size="sm">
              {getActionText()}
              <ArrowRightIcon className="w-4 h-4 ml-1" />
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}

// Icons
function TensionIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 9v4M12 17h.01" strokeLinecap="round" />
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    </svg>
  );
}

function BlindSpotIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
    </svg>
  );
}

function ExploreIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M16.24 7.76l-2.12 6.36-6.36 2.12 2.12-6.36 6.36-2.12z" />
    </svg>
  );
}

function ResearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" strokeLinecap="round" />
    </svg>
  );
}

function ReadyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 11.08V12a10 10 0 11-5.93-9.14" strokeLinecap="round" />
      <path d="M22 4L12 14.01l-3-3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DefaultIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" strokeLinecap="round" />
    </svg>
  );
}

function ArrowRightIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default RecommendedAction;
