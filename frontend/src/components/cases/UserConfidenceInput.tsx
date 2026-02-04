/**
 * UserConfidenceInput - User's self-assessed confidence
 *
 * The user states their own confidence level.
 * This is their assessment, not a computed score.
 *
 * Includes "What would change your mind?" - a key epistemic question.
 */

'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useUserConfidence } from '@/hooks/useUserConfidence';
import { CheckIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

interface UserConfidenceInputProps {
  caseId: string;
  initialConfidence?: number | null;
  initialWhatWouldChange?: string;
  onConfidenceChange?: (confidence: number) => void;
  compact?: boolean;
}

export function UserConfidenceInput({
  caseId,
  initialConfidence,
  initialWhatWouldChange = '',
  onConfidenceChange,
  compact = false,
}: UserConfidenceInputProps) {
  const {
    confidence,
    whatWouldChangeMind,
    isSaving,
    setConfidence,
    setWhatWouldChangeMind,
    save,
  } = useUserConfidence({
    caseId,
    initialConfidence,
    initialWhatWouldChange,
  });

  const [localConfidence, setLocalConfidence] = useState<number>(confidence ?? 50);
  const [isEditing, setIsEditing] = useState(false);

  // Sync local state with hook state
  useEffect(() => {
    if (confidence !== null) {
      setLocalConfidence(confidence);
    }
  }, [confidence]);

  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      setLocalConfidence(value);
    },
    []
  );

  const handleSliderRelease = useCallback(() => {
    setConfidence(localConfidence, whatWouldChangeMind);
    onConfidenceChange?.(localConfidence);
  }, [localConfidence, whatWouldChangeMind, setConfidence, onConfidenceChange]);

  const handleTextChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setWhatWouldChangeMind(e.target.value);
    },
    [setWhatWouldChangeMind]
  );

  const handleTextBlur = useCallback(() => {
    // Save when user finishes editing text
    if (confidence !== null) {
      save();
    }
    setIsEditing(false);
  }, [confidence, save]);

  const getConfidenceLabel = (value: number): string => {
    if (value <= 20) return 'Very uncertain';
    if (value <= 40) return 'Somewhat uncertain';
    if (value <= 60) return 'Moderately confident';
    if (value <= 80) return 'Fairly confident';
    return 'Very confident';
  };

  const getConfidenceColor = (value: number): string => {
    if (value <= 30) return 'text-red-600';
    if (value <= 50) return 'text-amber-600';
    if (value <= 70) return 'text-yellow-600';
    return 'text-green-600';
  };

  // Compact mode
  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-sm text-neutral-500">Your confidence:</span>
        <div className="flex items-center gap-2">
          <input
            type="range"
            min={0}
            max={100}
            value={localConfidence}
            onChange={handleSliderChange}
            onMouseUp={handleSliderRelease}
            onTouchEnd={handleSliderRelease}
            className="w-24 h-1.5 bg-neutral-200 rounded-lg appearance-none cursor-pointer slider-thumb"
          />
          <span className={`text-sm font-medium w-8 ${getConfidenceColor(localConfidence)}`}>
            {localConfidence}
          </span>
        </div>
        {isSaving && <ArrowPathIcon className="w-4 h-4 text-neutral-400 animate-spin" />}
      </div>
    );
  }

  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-neutral-900">How confident are you?</h3>
        {isSaving && (
          <span className="flex items-center gap-1 text-xs text-neutral-400">
            <ArrowPathIcon className="w-3 h-3 animate-spin" />
            Saving...
          </span>
        )}
        {!isSaving && confidence !== null && (
          <span className="flex items-center gap-1 text-xs text-green-600">
            <CheckIcon className="w-3 h-3" />
            Saved
          </span>
        )}
      </div>

      {/* Slider */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm text-neutral-500">
          <span>Uncertain</span>
          <span>Very confident</span>
        </div>

        <div className="relative">
          <input
            type="range"
            min={0}
            max={100}
            value={localConfidence}
            onChange={handleSliderChange}
            onMouseUp={handleSliderRelease}
            onTouchEnd={handleSliderRelease}
            className="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer"
            style={{
              background: `linear-gradient(to right, #ef4444 0%, #f59e0b 25%, #eab308 50%, #84cc16 75%, #22c55e 100%)`,
            }}
          />
        </div>

        <div className="flex items-center justify-center gap-2">
          <span className={`text-2xl font-bold ${getConfidenceColor(localConfidence)}`}>
            {localConfidence}
          </span>
          <span className="text-sm text-neutral-500">{getConfidenceLabel(localConfidence)}</span>
        </div>
      </div>

      {/* What would change your mind */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-neutral-700">
          What would change your mind?
        </label>
        <textarea
          value={whatWouldChangeMind}
          onChange={handleTextChange}
          onFocus={() => setIsEditing(true)}
          onBlur={handleTextBlur}
          placeholder="e.g., Finding that market size is less than $50M, or discovering a competitor has already launched..."
          className="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-500 focus:border-transparent resize-none"
          rows={3}
        />
        <p className="text-xs text-neutral-400">
          This helps you stay open to updating your view as you learn more.
        </p>
      </div>
    </div>
  );
}

/**
 * Minimal confidence indicator showing user's stated confidence
 */
export function UserConfidenceBadge({
  confidence,
  showLabel = false,
}: {
  confidence: number | null;
  showLabel?: boolean;
}) {
  if (confidence === null) {
    return (
      <span className="text-sm text-neutral-400">Not assessed</span>
    );
  }

  const getColor = (value: number): string => {
    if (value <= 30) return 'bg-red-100 text-red-700';
    if (value <= 50) return 'bg-amber-100 text-amber-700';
    if (value <= 70) return 'bg-yellow-100 text-yellow-700';
    return 'bg-green-100 text-green-700';
  };

  return (
    <span className={`px-2 py-0.5 rounded-full text-sm font-medium ${getColor(confidence)}`}>
      {confidence}
      {showLabel && <span className="ml-1 text-xs opacity-75">confidence</span>}
    </span>
  );
}
