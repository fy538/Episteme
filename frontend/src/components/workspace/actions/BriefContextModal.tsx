/**
 * Brief Context Modal
 *
 * Settings for AI-generated brief - what to include, focus type, custom instructions.
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { BriefContextSettings } from '@/lib/types/intelligence';
import type { Inquiry } from '@/lib/types/case';

interface Source {
  id: string;
  name: string;
  linkedInquiries: number;
}

interface BriefContextModalProps {
  inquiries: Inquiry[];
  sources: Source[];
  currentSettings?: Partial<BriefContextSettings>;
  isOpen: boolean;
  onClose: () => void;
  onRegenerate: (settings: BriefContextSettings) => void;
}

export function BriefContextModal({
  inquiries,
  sources,
  currentSettings,
  isOpen,
  onClose,
  onRegenerate,
}: BriefContextModalProps) {
  const [selectedInquiries, setSelectedInquiries] = useState<string[]>(
    currentSettings?.inquiryIds || inquiries.map(i => i.id)
  );
  const [selectedSources, setSelectedSources] = useState<string[]>(
    currentSettings?.sourceIds || sources.map(s => s.id)
  );
  const [focus, setFocus] = useState<BriefContextSettings['focus']>(
    currentSettings?.focus || 'balanced'
  );
  const [customInstructions, setCustomInstructions] = useState(
    currentSettings?.customInstructions || ''
  );

  if (!isOpen) return null;

  const toggleInquiry = (id: string) => {
    setSelectedInquiries(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const toggleSource = (id: string) => {
    setSelectedSources(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  const handleRegenerate = () => {
    onRegenerate({
      inquiryIds: selectedInquiries,
      sourceIds: selectedSources,
      focus,
      customInstructions: customInstructions || undefined,
    });
    onClose();
  };

  const focusOptions: { value: BriefContextSettings['focus']; label: string; description: string }[] = [
    { value: 'balanced', label: 'Balanced overview', description: 'Cover all aspects equally' },
    { value: 'risk', label: 'Risk-focused', description: 'Emphasize risks and concerns' },
    { value: 'recommendation', label: 'Recommendation-focused', description: 'Lead with the recommendation' },
    { value: 'executive', label: 'Executive summary', description: 'Shorter, high-level overview' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 max-h-[90vh] bg-white dark:bg-neutral-900 rounded-lg shadow-lg overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-neutral-200 dark:border-neutral-800 shrink-0">
          <div>
            <h2 className="font-semibold text-primary-900 dark:text-primary-50">
              Brief Context Settings
            </h2>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
              Customize what the AI considers
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded"
          >
            <CloseIcon className="w-5 h-5 text-neutral-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-5 space-y-6">
          {/* Inquiries */}
          <section>
            <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
              Inquiries
            </h3>
            <div className="space-y-2">
              {inquiries.map((inquiry) => (
                <label
                  key={inquiry.id}
                  className="flex items-center gap-3 p-2 -mx-2 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800/50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedInquiries.includes(inquiry.id)}
                    onChange={() => toggleInquiry(inquiry.id)}
                    className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-accent-600 focus:ring-accent-500"
                  />
                  <span className="flex-1 text-sm text-primary-900 dark:text-primary-50">
                    {inquiry.title}
                  </span>
                  {inquiry.status === 'resolved' && (
                    <CheckIcon className="w-4 h-4 text-success-500" />
                  )}
                </label>
              ))}
            </div>
          </section>

          {/* Sources */}
          <section>
            <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
              Sources
            </h3>
            <div className="space-y-2">
              {sources.map((source) => (
                <label
                  key={source.id}
                  className="flex items-center gap-3 p-2 -mx-2 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800/50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedSources.includes(source.id)}
                    onChange={() => toggleSource(source.id)}
                    className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-accent-600 focus:ring-accent-500"
                  />
                  <span className="flex-1 text-sm text-primary-900 dark:text-primary-50">
                    {source.name}
                  </span>
                  {source.linkedInquiries === 0 && (
                    <span className="text-xs text-neutral-400 dark:text-neutral-500">
                      not linked
                    </span>
                  )}
                </label>
              ))}
            </div>
          </section>

          {/* Focus */}
          <section>
            <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
              Focus
            </h3>
            <div className="space-y-2">
              {focusOptions.map((option) => (
                <label
                  key={option.value}
                  className={cn(
                    'flex items-start gap-3 p-3 rounded-lg border-2 cursor-pointer transition-colors',
                    focus === option.value
                      ? 'border-accent-500 bg-accent-50/50 dark:bg-accent-900/10'
                      : 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'
                  )}
                >
                  <input
                    type="radio"
                    name="focus"
                    value={option.value}
                    checked={focus === option.value}
                    onChange={() => setFocus(option.value)}
                    className="mt-0.5 w-4 h-4 border-neutral-300 dark:border-neutral-600 text-accent-600 focus:ring-accent-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-primary-900 dark:text-primary-50">
                      {option.label}
                    </span>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                      {option.description}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </section>

          {/* Custom Instructions */}
          <section>
            <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
              Custom Instructions
            </h3>
            <textarea
              value={customInstructions}
              onChange={(e) => setCustomInstructions(e.target.value)}
              placeholder="Focus on valuation implications. This is for the board..."
              rows={3}
              className="w-full text-sm px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-900 focus:outline-none focus:ring-2 focus:ring-accent-500 resize-none"
            />
          </section>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-5 border-t border-neutral-200 dark:border-neutral-800 shrink-0">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleRegenerate}>
            <RefreshIcon className="w-4 h-4 mr-2" />
            Regenerate Brief
          </Button>
        </div>
      </div>
    </div>
  );
}

// Icons
function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M23 4v6h-6M1 20v-6h6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default BriefContextModal;
