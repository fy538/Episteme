/**
 * CopilotStatus - Central control for AI copilot features
 *
 * Shows:
 * - Current copilot status (active/idle)
 * - Pending suggestions count
 * - Toggle for different copilot modes
 * - Quick access to generate suggestions
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  SparklesIcon,
  Cog6ToothIcon,
  BoltIcon,
  PauseIcon,
} from '@heroicons/react/24/outline';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Switch } from '@/components/ui/switch';

interface CopilotStatusProps {
  isActive: boolean;
  pendingSuggestions: number;
  isAnalyzing: boolean;
  inlineEnabled: boolean;
  suggestionsEnabled: boolean;
  onToggleInline: (enabled: boolean) => void;
  onToggleSuggestions: (enabled: boolean) => void;
  onGenerateSuggestions: () => void;
  onOpenReviewPanel: () => void;
}

export function CopilotStatus({
  isActive,
  pendingSuggestions,
  isAnalyzing,
  inlineEnabled,
  suggestionsEnabled,
  onToggleInline,
  onToggleSuggestions,
  onGenerateSuggestions,
  onOpenReviewPanel,
}: CopilotStatusProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <button
          className={`
            flex items-center gap-2 px-3 py-1.5 rounded-full text-sm
            transition-colors border
            ${isActive
              ? 'bg-accent-50 border-accent-200 text-accent-700 hover:bg-accent-100'
              : 'bg-neutral-50 border-neutral-200 text-neutral-600 hover:bg-neutral-100'
            }
          `}
        >
          <SparklesIcon className={`w-4 h-4 ${isAnalyzing ? 'animate-pulse' : ''}`} />
          <span>Copilot</span>
          {pendingSuggestions > 0 && (
            <span className="px-1.5 py-0.5 bg-accent-500 text-white text-xs rounded-full">
              {pendingSuggestions}
            </span>
          )}
        </button>
      </PopoverTrigger>

      <PopoverContent className="w-72" align="end">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-neutral-900">AI Copilot</h3>
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                isActive
                  ? 'bg-success-100 text-success-700'
                  : 'bg-neutral-100 text-neutral-600'
              }`}
            >
              {isAnalyzing ? 'Analyzing...' : isActive ? 'Active' : 'Idle'}
            </span>
          </div>

          {/* Status */}
          {pendingSuggestions > 0 && (
            <div className="p-3 bg-accent-50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm text-accent-700">
                  {pendingSuggestions} suggestion{pendingSuggestions !== 1 ? 's' : ''} ready
                </span>
                <Button size="sm" variant="ghost" onClick={onOpenReviewPanel}>
                  Review
                </Button>
              </div>
            </div>
          )}

          {/* Settings */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-neutral-700">Inline suggestions</p>
                <p className="text-xs text-neutral-500">Ghost text as you type</p>
              </div>
              <Switch
                checked={inlineEnabled}
                onCheckedChange={onToggleInline}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-neutral-700">Brief suggestions</p>
                <p className="text-xs text-neutral-500">AI improvements for your brief</p>
              </div>
              <Switch
                checked={suggestionsEnabled}
                onCheckedChange={onToggleSuggestions}
              />
            </div>
          </div>

          {/* Actions */}
          <div className="pt-2 border-t space-y-2">
            <Button
              className="w-full justify-start"
              variant="ghost"
              size="sm"
              onClick={() => {
                onGenerateSuggestions();
                setIsOpen(false);
              }}
              disabled={isAnalyzing}
            >
              <BoltIcon className="w-4 h-4 mr-2" />
              {isAnalyzing ? 'Analyzing...' : 'Analyze Brief'}
            </Button>
          </div>

          {/* Keyboard shortcuts */}
          <div className="pt-2 border-t text-xs text-neutral-500">
            <p className="flex justify-between">
              <span>Generate suggestions</span>
              <kbd className="px-1.5 py-0.5 bg-neutral-100 rounded">⌘⇧S</kbd>
            </p>
            <p className="flex justify-between mt-1">
              <span>Accept inline</span>
              <kbd className="px-1.5 py-0.5 bg-neutral-100 rounded">Tab</kbd>
            </p>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

/**
 * Compact version for toolbar
 */
export function CopilotButton({
  pendingSuggestions,
  isAnalyzing,
  onClick,
}: {
  pendingSuggestions: number;
  isAnalyzing: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        relative p-2 rounded-lg transition-colors
        ${pendingSuggestions > 0
          ? 'bg-accent-100 text-accent-700 hover:bg-accent-200'
          : 'text-neutral-500 hover:bg-neutral-100'
        }
      `}
      title="AI Copilot"
    >
      <SparklesIcon className={`w-5 h-5 ${isAnalyzing ? 'animate-pulse' : ''}`} />
      {pendingSuggestions > 0 && (
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-accent-500 text-white text-xs rounded-full flex items-center justify-center">
          {pendingSuggestions}
        </span>
      )}
    </button>
  );
}
