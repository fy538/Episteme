'use client';

import { useState } from 'react';
import { casesAPI } from '@/lib/api/cases';
import type { ResolutionType, DecisionRecord } from '@/lib/types/case';

interface ResolutionTypeOption {
  type: ResolutionType;
  label: string;
  description: string;
  icon: string;
}

const RESOLUTION_TYPES: ResolutionTypeOption[] = [
  {
    type: 'resolved',
    label: "I've landed",
    description: 'Got an answer — decision or understanding',
    icon: '✓',
  },
  {
    type: 'closed',
    label: 'Close without resolving',
    description: 'Shelved, moot, or needs reframing',
    icon: '—',
  },
];

const RESOLVED_LABELS: Record<ResolutionType, string> = {
  resolved: 'Case resolved',
  closed: 'Case closed',
};

interface ResolutionTypePickerProps {
  caseId: string;
  onResolved?: (record: DecisionRecord) => void;
  /** Controls visual weight — prominent for synthesizing stage CTA, subtle for header menu */
  isProminent?: boolean;
}

export function ResolutionTypePicker({
  caseId,
  onResolved,
  isProminent = false,
}: ResolutionTypePickerProps) {
  const [isResolving, setIsResolving] = useState(false);
  const [selectedType, setSelectedType] = useState<ResolutionType | null>(null);
  const [resolved, setResolved] = useState(false);
  const [error, setError] = useState('');

  const handleResolve = async (type: ResolutionType) => {
    setIsResolving(true);
    setSelectedType(type);
    setError('');

    try {
      const record = await casesAPI.resolveCase(caseId, type);
      setResolved(true);
      // Brief success state before propagating
      setTimeout(() => onResolved?.(record), 600);
    } catch {
      setError('Failed to resolve case. Please try again.');
      setSelectedType(null);
    } finally {
      setIsResolving(false);
    }
  };

  // Success state — brief green confirmation
  if (resolved && selectedType) {
    const label = RESOLVED_LABELS[selectedType];
    return (
      <div className={`flex items-center gap-2 ${isProminent ? 'justify-center py-4' : 'py-1'}`}>
        <span className="text-emerald-500 text-lg animate-bounce">✓</span>
        <span className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
          {label}
        </span>
      </div>
    );
  }

  if (isProminent) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Ready to resolve this case?
        </p>
        <div className="space-y-2">
          {RESOLUTION_TYPES.map((option) => {
            const isSelected = selectedType === option.type;
            return (
              <button
                key={option.type}
                onClick={() => handleResolve(option.type)}
                disabled={isResolving}
                className={`
                  flex flex-col items-start gap-1 rounded-lg border p-3 text-left
                  transition-all hover:border-zinc-400 dark:hover:border-zinc-500
                  ${isSelected && isResolving
                    ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-950'
                    : 'border-zinc-200 dark:border-zinc-700'
                  }
                  ${isResolving && !isSelected
                    ? 'opacity-50 cursor-not-allowed'
                    : 'cursor-pointer'
                  }
                `}
              >
                <span className="flex items-center gap-1.5 text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {isSelected && isResolving ? (
                    <span className="inline-block w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <span>{option.icon}</span>
                  )}
                  {isSelected && isResolving ? 'Resolving...' : option.label}
                </span>
                {!(isSelected && isResolving) && (
                  <span className="text-xs text-zinc-500 dark:text-zinc-400">
                    {option.description}
                  </span>
                )}
              </button>
            );
          })}
        </div>
        {error && (
          <div className="flex items-center justify-between">
            <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
            <button
              onClick={() => setError('')}
              className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>
    );
  }

  // Subtle / compact variant for header/menu
  return (
    <div className="space-y-1">
      <p className="text-xs text-zinc-400 dark:text-zinc-500 font-medium uppercase tracking-wide">
        Resolve
      </p>
      <div className="flex flex-wrap gap-1.5">
        {RESOLUTION_TYPES.map((option) => {
          const isSelected = selectedType === option.type;
          return (
            <button
              key={option.type}
              onClick={() => handleResolve(option.type)}
              disabled={isResolving}
              title={option.description}
              className={`
                inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs
                transition-all hover:border-zinc-400 dark:hover:border-zinc-500
                ${isSelected && isResolving
                  ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-950'
                  : 'border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400'
                }
                ${isResolving && !isSelected
                  ? 'opacity-50 cursor-not-allowed'
                  : 'cursor-pointer hover:text-zinc-900 dark:hover:text-zinc-200'
                }
              `}
            >
              {isSelected && isResolving ? (
                <span className="inline-block w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              ) : (
                <span>{option.icon}</span>
              )}
              {isSelected && isResolving ? 'Resolving...' : option.label}
            </button>
          );
        })}
      </div>
      {error && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
          <button
            onClick={() => setError('')}
            className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
