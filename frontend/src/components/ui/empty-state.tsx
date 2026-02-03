/**
 * Empty State Component
 * Beautiful, actionable empty states for when there's no content
 */

'use client';

import { motion } from 'framer-motion';
import { Button } from './button';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import {
  NoConversationsIllustration,
  NoCasesIllustration,
  NoProjectsIllustration,
  NoInquiriesIllustration,
  NoSearchResultsIllustration,
} from '@/components/illustrations/EmptyStateIllustrations';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  illustration?: React.ReactNode;
  compact?: boolean;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  illustration,
  compact = false,
}: EmptyStateProps) {
  const prefersReducedMotion = useReducedMotion();

  const content = (
    <div className={`text-center ${compact ? 'py-8' : 'py-16'}`}>
      {/* Illustration or Icon */}
      {illustration ? (
        <div className="mb-6 flex justify-center">{illustration}</div>
      ) : icon ? (
        <div className="mb-4 flex justify-center">
          <div className="rounded-full bg-neutral-100 dark:bg-neutral-800 p-4 text-neutral-400 dark:text-neutral-500">
            {icon}
          </div>
        </div>
      ) : (
        <div className="mb-4 flex justify-center">
          <svg
            className="h-16 w-16 text-neutral-300 dark:text-neutral-700"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
            />
          </svg>
        </div>
      )}

      {/* Title */}
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
        {title}
      </h3>

      {/* Description */}
      {description && (
        <p className="text-sm text-neutral-600 dark:text-neutral-400 max-w-sm mx-auto mb-6">
          {description}
        </p>
      )}

      {/* Actions */}
      {(action || secondaryAction) && (
        <div className="flex items-center justify-center gap-3">
          {action && (
            <Button onClick={action.onClick}>{action.label}</Button>
          )}
          {secondaryAction && (
            <Button variant="outline" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );

  if (prefersReducedMotion) {
    return content;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      {content}
    </motion.div>
  );
}

// Preset empty states for common scenarios
export function NoConversationsEmpty({ onCreate }: { onCreate: () => void }) {
  return (
    <EmptyState
      illustration={<NoConversationsIllustration />}
      title="No conversations yet"
      description="Start a conversation to explore ideas and structure your thinking"
      action={{ label: 'New Conversation', onClick: onCreate }}
    />
  );
}

export function NoCasesEmpty({ onCreate }: { onCreate: () => void }) {
  return (
    <EmptyState
      illustration={<NoCasesIllustration />}
      title="No cases yet"
      description="Cases help you organize complex decisions and validate assumptions"
      action={{ label: 'Create Case', onClick: onCreate }}
    />
  );
}

export function NoProjectsEmpty({ onCreate }: { onCreate: () => void }) {
  return (
    <EmptyState
      illustration={<NoProjectsIllustration />}
      title="No projects yet"
      description="Projects help you organize related cases and conversations"
      action={{ label: 'Create Project', onClick: onCreate }}
    />
  );
}

export function NoInquiriesEmpty({ onCreate }: { onCreate: () => void }) {
  return (
    <EmptyState
      illustration={<NoInquiriesIllustration />}
      title="No inquiries yet"
      description="Inquiries help you systematically investigate important questions"
      action={{ label: 'Create Inquiry', onClick: onCreate }}
      compact
    />
  );
}

export function NoSearchResultsEmpty({ query }: { query: string }) {
  return (
    <EmptyState
      illustration={<NoSearchResultsIllustration />}
      title={`No results for "${query}"`}
      description="Try adjusting your search terms or filters"
      compact
    />
  );
}
