/**
 * EmptyGraphState — Shown in CaseGraphView when no graph data exists.
 *
 * Simple centered prompt encouraging the user to upload documents
 * and run extraction. Provides action buttons for common next steps.
 */

'use client';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { SearchIcon } from '@/components/ui/icons';

interface EmptyGraphStateProps {
  caseId: string;
  onReExtract?: () => void;
  onViewDocuments?: () => void;
  className?: string;
}

export function EmptyGraphState({
  caseId,
  onReExtract,
  onViewDocuments,
  className,
}: EmptyGraphStateProps) {
  return (
    <div className={cn('flex items-center justify-center h-full', className)}>
      <div className="text-center max-w-md">
        {/* Icon */}
        <div className="mx-auto mb-4 w-12 h-12 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center">
          <SearchIcon className="w-6 h-6 text-neutral-400 dark:text-neutral-500" />
        </div>

        {/* Title */}
        <h3 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">
          No evidence graph yet
        </h3>

        {/* Description */}
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">
          Add documents to your project and run extraction to build a graph of
          claims, evidence, and assumptions for this case.
        </p>

        {/* Actions */}
        <div className="flex items-center justify-center gap-3">
          {onViewDocuments && (
            <Button variant="outline" size="sm" onClick={onViewDocuments}>
              View Documents
            </Button>
          )}
          {onReExtract && (
            <Button variant="default" size="sm" onClick={onReExtract}>
              Run Extraction
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
