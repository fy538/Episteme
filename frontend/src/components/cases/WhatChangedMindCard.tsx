'use client';

import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { casesAPI } from '@/lib/api/cases';

type ResponseOption = 'updated_view' | 'proceeding_anyway' | 'not_materialized';

interface WhatChangedMindCardProps {
  caseId: string;
  originalText: string;
  existingResponse?: string;
  onResponded?: () => void;
}

const RESPONSE_OPTIONS: { value: ResponseOption; label: string; icon: string }[] = [
  { value: 'updated_view', label: 'Yes, and I updated my view', icon: '\u2705' },
  { value: 'proceeding_anyway', label: 'Yes, but I\'m proceeding anyway', icon: '\u26A0\uFE0F' },
  { value: 'not_materialized', label: 'No, none of this materialized', icon: '\u2796' },
];

const RESPONSE_LABELS: Record<string, { label: string; color: string }> = {
  'updated_view': { label: 'You updated your view', color: 'text-success-600 dark:text-success-400' },
  'proceeding_anyway': { label: 'Acknowledged but proceeding', color: 'text-warning-600 dark:text-warning-400' },
  'not_materialized': { label: 'None materialized', color: 'text-neutral-500 dark:text-neutral-400' },
};

export function WhatChangedMindCard({
  caseId,
  originalText,
  existingResponse,
  onResponded,
}: WhatChangedMindCardProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [savedResponse, setSavedResponse] = useState(existingResponse || '');
  const [error, setError] = useState('');

  const handleRespond = useCallback(async (response: ResponseOption) => {
    setIsSaving(true);
    setError('');
    try {
      await casesAPI.saveWhatChangedMindResponse(caseId, response);
      setSavedResponse(response);
      onResponded?.();
    } catch (err) {
      setError('Failed to save response. Please try again.');
    } finally {
      setIsSaving(false);
    }
  }, [caseId, onResponded]);

  // Already responded — show compact summary
  if (savedResponse) {
    const responseInfo = RESPONSE_LABELS[savedResponse];
    return (
      <div className="p-3 rounded-lg border border-neutral-200/80 dark:border-neutral-800/80 bg-neutral-50/50 dark:bg-neutral-900/30">
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-1">Earlier, you said this would change your mind:</p>
        <p className="text-sm text-neutral-700 dark:text-neutral-300 italic mb-2">&ldquo;{originalText}&rdquo;</p>
        {responseInfo && (
          <p className={`text-xs font-medium ${responseInfo.color}`}>
            {responseInfo.label}
          </p>
        )}
      </div>
    );
  }

  // Not yet responded — show the prompt
  return (
    <div className="p-4 rounded-lg border border-info-200/80 dark:border-info-800/80 bg-info-50/50 dark:bg-info-900/20 space-y-3">
      <div>
        <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
          Earlier, you said this would change your mind:
        </p>
        <p className="text-sm text-neutral-700 dark:text-neutral-300 italic mt-1">
          &ldquo;{originalText}&rdquo;
        </p>
      </div>

      <p className="text-sm text-neutral-600 dark:text-neutral-400">
        Has any of this happened?
      </p>

      <div className="flex flex-col gap-2">
        {RESPONSE_OPTIONS.map(opt => (
          <Button
            key={opt.value}
            variant="outline"
            onClick={() => handleRespond(opt.value)}
            disabled={isSaving}
            aria-label={opt.label}
            className="flex items-center gap-2 px-3 py-2 h-auto text-sm text-left justify-start"
          >
            <span>{opt.icon}</span>
            <span>{opt.label}</span>
          </Button>
        ))}
      </div>

      {error && (
        <p className="text-xs text-error-500 mt-2" role="alert">{error}</p>
      )}
    </div>
  );
}
