/**
 * BlindSpotPrompts - AI suggestions framed as prompts for reflection
 *
 * Not deficiencies to fix. Not scores to improve.
 * Just questions to consider.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  LightBulbIcon,
  XMarkIcon,
  ArrowPathIcon,
  PlusCircleIcon,
  MagnifyingGlassIcon,
  DocumentPlusIcon,
} from '@heroicons/react/24/outline';
import { casesAPI } from '@/lib/api/cases';
import type { BlindSpotPrompt } from '@/lib/types/case';
import { Button } from '@/components/ui/button';

interface BlindSpotPromptsProps {
  caseId: string;
  onCreateInquiry?: (text: string) => void;
  onInvestigate?: (signalId: string, text: string) => void;
  onAddEvidence?: (text: string) => void;
  maxPrompts?: number;
}

export function BlindSpotPrompts({
  caseId,
  onCreateInquiry,
  onInvestigate,
  onAddEvidence,
  maxPrompts = 5,
}: BlindSpotPromptsProps) {
  const [prompts, setPrompts] = useState<BlindSpotPrompt[]>([]);
  const [dismissedIds, setDismissedIds] = useState<Set<number>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPrompts = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await casesAPI.getBlindSpotPrompts(caseId);
      setPrompts(result.prompts || []);
      setDismissedIds(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load suggestions');
    } finally {
      setIsLoading(false);
    }
  }, [caseId]);

  // Load on mount
  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  const handleDismiss = useCallback((index: number) => {
    setDismissedIds((prev) => new Set([...prev, index]));
  }, []);

  const handleAction = useCallback(
    (prompt: BlindSpotPrompt, index: number) => {
      switch (prompt.action) {
        case 'create_inquiry':
          onCreateInquiry?.(prompt.text);
          break;
        case 'investigate':
          onInvestigate?.(prompt.signal_id || '', prompt.text);
          break;
        case 'add_evidence':
          onAddEvidence?.(prompt.text);
          break;
      }
      // Dismiss after action
      handleDismiss(index);
    },
    [onCreateInquiry, onInvestigate, onAddEvidence, handleDismiss]
  );

  const visiblePrompts = prompts.filter((_, i) => !dismissedIds.has(i)).slice(0, maxPrompts);

  if (isLoading) {
    return (
      <div className="bg-white border border-neutral-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-sm text-neutral-500">
          <ArrowPathIcon className="w-4 h-4 animate-spin" />
          Thinking about what you might be missing...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border border-neutral-200 rounded-lg p-4">
        <div className="text-sm text-red-500">{error}</div>
        <Button onClick={loadPrompts} size="sm" variant="ghost" className="mt-2">
          Try again
        </Button>
      </div>
    );
  }

  if (visiblePrompts.length === 0) {
    return (
      <div className="bg-white border border-neutral-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <LightBulbIcon className="w-4 h-4" />
            <span>No blind spots detected right now</span>
          </div>
          <Button onClick={loadPrompts} size="sm" variant="ghost">
            <ArrowPathIcon className="w-4 h-4 mr-1" />
            Refresh
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-neutral-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <LightBulbIcon className="w-5 h-5 text-amber-500" />
          <h3 className="font-medium text-neutral-900">Consider</h3>
        </div>
        <Button onClick={loadPrompts} size="sm" variant="ghost" disabled={isLoading}>
          <ArrowPathIcon className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Prompts */}
      <div className="divide-y divide-neutral-100">
        {visiblePrompts.map((prompt, index) => (
          <PromptCard
            key={index}
            prompt={prompt}
            onDismiss={() => handleDismiss(prompts.indexOf(prompt))}
            onAction={() => handleAction(prompt, prompts.indexOf(prompt))}
          />
        ))}
      </div>
    </div>
  );
}

interface PromptCardProps {
  prompt: BlindSpotPrompt;
  onDismiss: () => void;
  onAction: () => void;
}

function PromptCard({ prompt, onDismiss, onAction }: PromptCardProps) {
  const getIcon = () => {
    switch (prompt.type) {
      case 'alternative':
        return <LightBulbIcon className="w-4 h-4 text-blue-500" />;
      case 'assumption':
        return <MagnifyingGlassIcon className="w-4 h-4 text-amber-500" />;
      case 'evidence_gap':
        return <DocumentPlusIcon className="w-4 h-4 text-purple-500" />;
      default:
        return <LightBulbIcon className="w-4 h-4 text-neutral-400" />;
    }
  };

  const getActionLabel = () => {
    switch (prompt.action) {
      case 'create_inquiry':
        return 'Investigate';
      case 'investigate':
        return 'Validate';
      case 'add_evidence':
        return 'Find evidence';
      default:
        return 'Act';
    }
  };

  const getTypeLabel = () => {
    switch (prompt.type) {
      case 'alternative':
        return 'Alternative';
      case 'assumption':
        return 'Assumption';
      case 'evidence_gap':
        return 'Evidence gap';
      default:
        return '';
    }
  };

  return (
    <div className="p-4 hover:bg-neutral-50 transition-colors">
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="flex-shrink-0 mt-0.5">{getIcon()}</div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-neutral-700">{prompt.text}</p>
          <span className="text-xs text-neutral-400 mt-1">{getTypeLabel()}</span>
        </div>

        {/* Dismiss */}
        <button
          onClick={onDismiss}
          className="flex-shrink-0 p-1 text-neutral-300 hover:text-neutral-500 transition-colors"
        >
          <XMarkIcon className="w-4 h-4" />
        </button>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-3 ml-7">
        <Button onClick={onDismiss} size="sm" variant="ghost">
          I've considered this
        </Button>
        <Button onClick={onAction} size="sm" variant="outline">
          <PlusCircleIcon className="w-4 h-4 mr-1" />
          {getActionLabel()}
        </Button>
      </div>
    </div>
  );
}

/**
 * Compact blind spot indicator for headers
 */
export function BlindSpotIndicator({
  caseId,
}: {
  caseId: string;
}) {
  const [count, setCount] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const result = await casesAPI.getBlindSpotPrompts(caseId);
        setCount(result.prompts?.length || 0);
      } catch {
        setCount(null);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [caseId]);

  if (isLoading) {
    return <div className="w-16 h-5 bg-neutral-100 rounded animate-pulse" />;
  }

  if (count === null || count === 0) {
    return null;
  }

  return (
    <span className="flex items-center gap-1 text-sm text-amber-600">
      <LightBulbIcon className="w-4 h-4" />
      {count} to consider
    </span>
  );
}
