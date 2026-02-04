/**
 * EvidenceLandscape - Shows evidence counts without computing scores
 *
 * Replaces ConfidenceBreakdown. Shows what you have:
 * - Evidence counts by direction
 * - Assumption status
 * - Inquiry status
 *
 * No percentages. No scores. Just the facts.
 */

'use client';

import { useState } from 'react';
import {
  ChevronDownIcon,
  ChevronUpIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/react/24/outline';
import { useEvidenceLandscape } from '@/hooks/useEvidenceLandscape';

interface EvidenceLandscapeProps {
  caseId: string;
  compact?: boolean;
  onAssumptionClick?: (assumptionId: string) => void;
  onInquiryClick?: (inquiryId: string) => void;
}

export function EvidenceLandscape({
  caseId,
  compact = false,
  onAssumptionClick,
  onInquiryClick,
}: EvidenceLandscapeProps) {
  const [expanded, setExpanded] = useState(!compact);
  const { landscape, isLoading, error, totalEvidence, hasContradictions } =
    useEvidenceLandscape({ caseId, autoRefresh: true });

  if (isLoading) {
    return <div className="animate-pulse bg-neutral-100 rounded-lg p-4 h-20" />;
  }

  if (error || !landscape) {
    return (
      <div className="text-sm text-neutral-500 p-4">
        {error || 'Unable to load evidence landscape'}
      </div>
    );
  }

  // Compact mode - just a summary
  if (compact && !expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="flex items-center gap-3 px-3 py-2 rounded-lg bg-neutral-50 hover:bg-neutral-100 transition-colors text-sm"
      >
        <span className="text-neutral-600">{totalEvidence} evidence</span>
        <span className="text-neutral-400">|</span>
        <span className="text-neutral-600">
          {landscape.assumptions.untested} untested assumptions
        </span>
        <span className="text-neutral-400">|</span>
        <span className="text-neutral-600">
          {landscape.inquiries.open + landscape.inquiries.investigating} open inquiries
        </span>
        <ChevronDownIcon className="w-4 h-4 text-neutral-400 ml-auto" />
      </button>
    );
  }

  return (
    <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => compact && setExpanded(!expanded)}
        className={`w-full flex items-center justify-between p-4 ${
          compact ? 'hover:bg-neutral-50 cursor-pointer' : ''
        }`}
      >
        <h3 className="font-medium text-neutral-900">Evidence Landscape</h3>
        {compact && <ChevronUpIcon className="w-4 h-4 text-neutral-400" />}
      </button>

      {/* Evidence Section */}
      <div className="border-t px-4 py-3">
        <h4 className="text-sm font-medium text-neutral-700 mb-2">Evidence</h4>
        <div className="space-y-2">
          <EvidenceBar
            label="Supporting"
            count={landscape.evidence.supporting}
            total={totalEvidence}
            color="bg-green-500"
          />
          <EvidenceBar
            label="Contradicting"
            count={landscape.evidence.contradicting}
            total={totalEvidence}
            color="bg-red-500"
          />
          <EvidenceBar
            label="Neutral"
            count={landscape.evidence.neutral}
            total={totalEvidence}
            color="bg-neutral-400"
          />
        </div>
      </div>

      {/* Assumptions Section */}
      <div className="border-t px-4 py-3">
        <h4 className="text-sm font-medium text-neutral-700 mb-2">Assumptions</h4>
        <div className="flex items-center gap-4 text-sm mb-2">
          <div className="flex items-center gap-1.5">
            <CheckCircleIcon className="w-4 h-4 text-green-500" />
            <span className="text-neutral-600">
              Validated: <span className="font-medium">{landscape.assumptions.validated}</span>
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <QuestionMarkCircleIcon className="w-4 h-4 text-amber-500" />
            <span className="text-neutral-600">
              Untested: <span className="font-medium">{landscape.assumptions.untested}</span>
            </span>
          </div>
        </div>

        {/* Untested assumptions list */}
        {landscape.assumptions.untested_list.length > 0 && (
          <div className="mt-2 space-y-1">
            {landscape.assumptions.untested_list.slice(0, 5).map((assumption) => (
              <button
                key={assumption.id}
                onClick={() => onAssumptionClick?.(assumption.id)}
                className="w-full text-left text-sm text-neutral-600 hover:text-neutral-900 py-1 px-2 rounded hover:bg-neutral-50 flex items-start gap-2"
              >
                <span className="text-amber-500 mt-0.5">?</span>
                <span className="line-clamp-1">{assumption.text}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Inquiries Section */}
      <div className="border-t px-4 py-3">
        <h4 className="text-sm font-medium text-neutral-700 mb-2">Inquiries</h4>
        <div className="flex items-center gap-3 text-sm">
          <StatusPill
            count={landscape.inquiries.open}
            label="open"
            color="bg-neutral-200 text-neutral-700"
          />
          <StatusPill
            count={landscape.inquiries.investigating}
            label="investigating"
            color="bg-blue-100 text-blue-700"
          />
          <StatusPill
            count={landscape.inquiries.resolved}
            label="resolved"
            color="bg-green-100 text-green-700"
          />
        </div>
      </div>

      {/* Unlinked Claims Warning */}
      {landscape.unlinked_claims.length > 0 && (
        <div className="border-t px-4 py-3 bg-amber-50">
          <div className="flex items-center gap-2 text-sm text-amber-700 mb-2">
            <ExclamationCircleIcon className="w-4 h-4" />
            <span className="font-medium">Claims without evidence</span>
          </div>
          <ul className="text-sm text-amber-800 space-y-1">
            {landscape.unlinked_claims.slice(0, 3).map((claim, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-amber-500">&bull;</span>
                <span className="line-clamp-1">{claim.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function EvidenceBar({
  label,
  count,
  total,
  color,
}: {
  label: string;
  count: number;
  total: number;
  color: string;
}) {
  const width = total > 0 ? (count / total) * 100 : 0;

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-neutral-600 w-24">{label}</span>
      <div className="flex-1 h-2 bg-neutral-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} transition-all`}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="text-sm font-medium text-neutral-700 w-6 text-right">{count}</span>
    </div>
  );
}

function StatusPill({
  count,
  label,
  color,
}: {
  count: number;
  label: string;
  color: string;
}) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {count} {label}
    </span>
  );
}

/**
 * Compact evidence summary for headers/toolbars
 */
export function EvidenceSummaryBadge({
  caseId,
}: {
  caseId: string;
}) {
  const { landscape, isLoading, totalEvidence } = useEvidenceLandscape({ caseId });

  if (isLoading || !landscape) {
    return <div className="w-24 h-6 bg-neutral-100 rounded animate-pulse" />;
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-neutral-600">{totalEvidence} evidence</span>
      {landscape.assumptions.untested > 0 && (
        <>
          <span className="text-neutral-300">|</span>
          <span className="text-amber-600">{landscape.assumptions.untested} untested</span>
        </>
      )}
    </div>
  );
}
