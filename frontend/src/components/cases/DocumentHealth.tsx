/**
 * DocumentHealth - Shows document quality metrics from background analysis
 *
 * Displays:
 * - Health score with visual indicator
 * - Issue breakdown by severity
 * - Evidence coverage metrics
 * - Quick actions for improvements
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  HeartIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline';

interface HealthIssue {
  type: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  location: string;
}

interface HealthMetrics {
  claim_count: number;
  linked_claim_count: number;
  assumption_count: number;
  validated_assumption_count: number;
}

interface DocumentHealthProps {
  healthScore: number;
  issues: HealthIssue[];
  metrics: HealthMetrics;
  evidenceCoverage: number;
  lastAnalyzedAt: string | null;
  isAnalyzing: boolean;
  onRefresh: () => void;
  onViewIssue?: (issue: HealthIssue) => void;
  compact?: boolean;
}

export function DocumentHealth({
  healthScore,
  issues,
  metrics,
  evidenceCoverage,
  lastAnalyzedAt,
  isAnalyzing,
  onRefresh,
  onViewIssue,
  compact = false,
}: DocumentHealthProps) {
  const [expanded, setExpanded] = useState(false);

  const { color, bgColor, label } = getHealthStyle(healthScore);

  const highIssues = issues.filter((i) => i.severity === 'high');
  const mediumIssues = issues.filter((i) => i.severity === 'medium');
  const lowIssues = issues.filter((i) => i.severity === 'low');

  if (compact) {
    return (
      <button
        onClick={() => setExpanded(!expanded)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${bgColor} ${color} transition-colors hover:opacity-90`}
      >
        <HeartIcon className="w-4 h-4" />
        <span className="font-medium">{healthScore}</span>
        {issues.length > 0 && (
          <span className="text-xs opacity-75">({issues.length} issues)</span>
        )}
      </button>
    );
  }

  return (
    <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className={`px-4 py-3 ${bgColor} flex items-center justify-between`}>
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-full bg-white/50`}>
            <HeartIcon className={`w-5 h-5 ${color}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className={`text-2xl font-bold ${color}`}>{healthScore}</span>
              <span className={`text-sm font-medium ${color}`}>{label}</span>
            </div>
            {lastAnalyzedAt && (
              <p className="text-xs text-neutral-500">
                Analyzed {formatTime(lastAnalyzedAt)}
              </p>
            )}
          </div>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={onRefresh}
          disabled={isAnalyzing}
        >
          <ArrowPathIcon
            className={`w-4 h-4 ${isAnalyzing ? 'animate-spin' : ''}`}
          />
        </Button>
      </div>

      {/* Metrics */}
      <div className="px-4 py-3 grid grid-cols-2 gap-4 border-b">
        <div>
          <p className="text-xs text-neutral-500">Evidence Coverage</p>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-2 bg-neutral-100 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  evidenceCoverage >= 0.7
                    ? 'bg-success-500'
                    : evidenceCoverage >= 0.4
                    ? 'bg-warning-500'
                    : 'bg-error-500'
                }`}
                style={{ width: `${evidenceCoverage * 100}%` }}
              />
            </div>
            <span className="text-sm font-medium">
              {Math.round(evidenceCoverage * 100)}%
            </span>
          </div>
        </div>
        <div>
          <p className="text-xs text-neutral-500">Claims</p>
          <p className="text-sm font-medium mt-1">
            {metrics.linked_claim_count}/{metrics.claim_count} linked
          </p>
        </div>
        <div>
          <p className="text-xs text-neutral-500">Assumptions</p>
          <p className="text-sm font-medium mt-1">
            {metrics.validated_assumption_count}/{metrics.assumption_count} validated
          </p>
        </div>
        <div>
          <p className="text-xs text-neutral-500">Issues</p>
          <p className="text-sm font-medium mt-1">{issues.length} found</p>
        </div>
      </div>

      {/* Issues */}
      {issues.length > 0 && (
        <div className="px-4 py-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center justify-between w-full text-sm font-medium text-neutral-700"
          >
            <span>Issues by Severity</span>
            {expanded ? (
              <ChevronUpIcon className="w-4 h-4" />
            ) : (
              <ChevronDownIcon className="w-4 h-4" />
            )}
          </button>

          {/* Issue summary badges */}
          <div className="flex gap-2 mt-2">
            {highIssues.length > 0 && (
              <Badge variant="error" className="text-xs">
                {highIssues.length} High
              </Badge>
            )}
            {mediumIssues.length > 0 && (
              <Badge variant="neutral" className="text-xs bg-warning-100 text-warning-700">
                {mediumIssues.length} Medium
              </Badge>
            )}
            {lowIssues.length > 0 && (
              <Badge variant="neutral" className="text-xs">
                {lowIssues.length} Low
              </Badge>
            )}
          </div>

          {/* Expanded issue list */}
          {expanded && (
            <div className="mt-3 space-y-2">
              {issues.map((issue, idx) => (
                <button
                  key={idx}
                  onClick={() => onViewIssue?.(issue)}
                  className="w-full text-left p-2 rounded border border-neutral-100 hover:border-neutral-300 transition-colors"
                >
                  <div className="flex items-start gap-2">
                    {issue.severity === 'high' ? (
                      <XCircleIcon className="w-4 h-4 text-error-500 flex-shrink-0 mt-0.5" />
                    ) : issue.severity === 'medium' ? (
                      <ExclamationTriangleIcon className="w-4 h-4 text-warning-500 flex-shrink-0 mt-0.5" />
                    ) : (
                      <CheckCircleIcon className="w-4 h-4 text-neutral-400 flex-shrink-0 mt-0.5" />
                    )}
                    <div>
                      <p className="text-sm text-neutral-800">{issue.message}</p>
                      <p className="text-xs text-neutral-500 mt-0.5">
                        {issue.location}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* No issues state */}
      {issues.length === 0 && (
        <div className="px-4 py-6 text-center">
          <CheckCircleIcon className="w-8 h-8 text-success-500 mx-auto mb-2" />
          <p className="text-sm text-neutral-600">No issues found</p>
        </div>
      )}
    </div>
  );
}

/**
 * Compact health badge for headers
 */
export function HealthBadge({
  score,
  onClick,
}: {
  score: number;
  onClick?: () => void;
}) {
  const { color, bgColor } = getHealthStyle(score);

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${bgColor} ${color} hover:opacity-90 transition-opacity`}
    >
      <HeartIcon className="w-3.5 h-3.5" />
      {score}
    </button>
  );
}

// Helpers

function getHealthStyle(score: number) {
  if (score >= 80) {
    return {
      color: 'text-success-700',
      bgColor: 'bg-success-50',
      label: 'Excellent',
    };
  } else if (score >= 60) {
    return {
      color: 'text-success-600',
      bgColor: 'bg-success-50',
      label: 'Good',
    };
  } else if (score >= 40) {
    return {
      color: 'text-warning-700',
      bgColor: 'bg-warning-50',
      label: 'Needs Work',
    };
  } else {
    return {
      color: 'text-error-700',
      bgColor: 'bg-error-50',
      label: 'Critical',
    };
  }
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  return date.toLocaleDateString();
}
