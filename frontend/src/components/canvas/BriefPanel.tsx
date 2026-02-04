/**
 * BriefPanel - Slide-in panel for viewing/editing the brief
 *
 * Features:
 * - Slides in from the right
 * - Shows brief content with inline annotations
 * - Claims linked to evidence
 * - AI suggestions in margins
 */

'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  XMarkIcon,
  PencilIcon,
  SparklesIcon,
  LinkIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { Streamdown } from 'streamdown';
import remarkGfm from 'remark-gfm';
import type { CaseDocument } from '@/lib/types/case';

interface BriefPanelProps {
  isOpen: boolean;
  onClose: () => void;
  brief: CaseDocument | null;
  claims?: Array<{
    id: string;
    text: string;
    is_substantiated: boolean;
    confidence: number;
  }>;
  onEdit: () => void;
  onCreateInquiry: (text: string) => void;
}

export function BriefPanel({
  isOpen,
  onClose,
  brief,
  claims = [],
  onEdit,
  onCreateInquiry,
}: BriefPanelProps) {
  const [selectedText, setSelectedText] = useState<string | null>(null);

  // Handle text selection
  useEffect(() => {
    const handleSelection = () => {
      const selection = window.getSelection();
      if (selection && selection.toString().length > 10) {
        setSelectedText(selection.toString());
      } else {
        setSelectedText(null);
      }
    };

    document.addEventListener('mouseup', handleSelection);
    return () => document.removeEventListener('mouseup', handleSelection);
  }, []);

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/10 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div
        className={`
          fixed top-0 right-0 h-full w-full max-w-2xl
          bg-white shadow-2xl z-50
          transform transition-transform duration-300 ease-out
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-neutral-200 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">
              {brief?.title || 'Decision Brief'}
            </h2>
            <p className="text-sm text-neutral-500">
              {claims.filter(c => c.is_substantiated).length}/{claims.length} claims substantiated
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={onEdit}>
              <PencilIcon className="w-4 h-4 mr-1" />
              Edit
            </Button>
            <button
              onClick={onClose}
              className="p-2 text-neutral-400 hover:text-neutral-600 rounded-lg hover:bg-neutral-100"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto h-[calc(100%-80px)]">
          {brief ? (
            <div className="relative">
              {/* Main content */}
              <div className="px-8 py-6">
                <article className="prose prose-neutral max-w-none">
                  <Streamdown remarkPlugins={[remarkGfm]}>
                    {brief.content_markdown || ''}
                  </Streamdown>
                </article>
              </div>

              {/* Margin annotations */}
              <MarginAnnotations
                claims={claims}
                onCreateInquiry={onCreateInquiry}
              />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-neutral-500">
              <p>No brief available</p>
            </div>
          )}

          {/* Selection action bar */}
          {selectedText && (
            <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
              <div className="bg-neutral-900 text-white rounded-xl shadow-xl px-4 py-2 flex items-center gap-3">
                <span className="text-sm text-neutral-300">
                  "{selectedText.slice(0, 30)}..."
                </span>
                <div className="w-px h-6 bg-neutral-700" />
                <button
                  onClick={() => {
                    onCreateInquiry(selectedText);
                    setSelectedText(null);
                  }}
                  className="text-sm font-medium text-indigo-400 hover:text-indigo-300"
                >
                  Create Inquiry
                </button>
                <button
                  onClick={() => setSelectedText(null)}
                  className="text-neutral-500 hover:text-white"
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

/**
 * Margin annotations showing evidence links and issues
 */
function MarginAnnotations({
  claims,
  onCreateInquiry,
}: {
  claims: Array<{
    id: string;
    text: string;
    is_substantiated: boolean;
    confidence: number;
  }>;
  onCreateInquiry: (text: string) => void;
}) {
  // Group claims by substantiation status
  const unsubstantiated = claims.filter(c => !c.is_substantiated);

  if (unsubstantiated.length === 0) return null;

  return (
    <div className="absolute top-6 right-0 w-64 pr-4">
      <div className="sticky top-20">
        {/* Unsubstantiated claims summary */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <ExclamationTriangleIcon className="w-4 h-4 text-amber-600" />
            <span className="text-sm font-medium text-amber-800">
              {unsubstantiated.length} unverified claims
            </span>
          </div>
          <div className="space-y-2">
            {unsubstantiated.slice(0, 3).map(claim => (
              <button
                key={claim.id}
                onClick={() => onCreateInquiry(claim.text)}
                className="w-full text-left text-xs text-amber-700 hover:text-amber-900 p-1.5 rounded hover:bg-amber-100 transition-colors"
              >
                <span className="line-clamp-2">"{claim.text}"</span>
                <span className="text-amber-500 mt-0.5 block">→ Investigate</span>
              </button>
            ))}
            {unsubstantiated.length > 3 && (
              <p className="text-xs text-amber-600 text-center">
                +{unsubstantiated.length - 3} more
              </p>
            )}
          </div>
        </div>

        {/* Legend */}
        <div className="text-xs text-neutral-500 space-y-1">
          <div className="flex items-center gap-2">
            <CheckCircleIcon className="w-3.5 h-3.5 text-green-500" />
            <span>Substantiated</span>
          </div>
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="w-3.5 h-3.5 text-amber-500" />
            <span>Needs evidence</span>
          </div>
          <div className="flex items-center gap-2">
            <LinkIcon className="w-3.5 h-3.5 text-blue-500" />
            <span>Has inquiry</span>
          </div>
        </div>
      </div>
    </div>
  );
}
