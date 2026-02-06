/**
 * Blind Spot Modal
 *
 * Quick action modal for addressing blind spots.
 * Shows recommended action with alternatives.
 */

'use client';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { BlindSpotData } from '@/lib/types/intelligence';

interface BlindSpotModalProps {
  blindSpot: BlindSpotData;
  title: string;
  description: string;
  caseName?: string;
  inquiryName?: string;
  isOpen: boolean;
  onClose: () => void;
  onResearch: () => void;
  onDiscuss: () => void;
  onAddInquiry: () => void;
  onMarkAddressed: () => void;
}

export function BlindSpotModal({
  blindSpot,
  title,
  description,
  caseName,
  inquiryName,
  isOpen,
  onClose,
  onResearch,
  onDiscuss,
  onAddInquiry,
  onMarkAddressed,
}: BlindSpotModalProps) {
  if (!isOpen) return null;

  // Get recommended action text
  const getRecommendedText = () => {
    switch (blindSpot.suggestedAction) {
      case 'research':
        return {
          icon: ResearchIcon,
          title: `Research ${blindSpot.area}`,
          description: 'Generate research on this topic including benchmarks and best practices.',
          estimate: 'Estimated: 2-3 minutes',
          action: onResearch,
        };
      case 'discuss':
        return {
          icon: ChatIcon,
          title: 'Discuss with AI',
          description: 'Explore this topic through conversation to understand its implications.',
          estimate: 'Interactive',
          action: onDiscuss,
        };
      case 'add_inquiry':
        return {
          icon: InquiryIcon,
          title: 'Create new inquiry',
          description: 'Add this as a formal inquiry to investigate thoroughly.',
          estimate: 'Quick setup',
          action: onAddInquiry,
        };
    }
  };

  const recommended = getRecommendedText();
  const RecommendedIcon = recommended.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-white dark:bg-neutral-900 rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-neutral-200 dark:border-neutral-800">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-accent-100 dark:bg-accent-900/30">
              <BlindSpotIcon className="w-5 h-5 text-accent-600 dark:text-accent-400" />
            </div>
            <div>
              <h2 className="font-semibold text-primary-900 dark:text-primary-50">
                Blind Spot Detected
              </h2>
              {(caseName || inquiryName) && (
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
                  {[caseName, inquiryName].filter(Boolean).join(' · ')}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded"
          >
            <CloseIcon className="w-5 h-5 text-neutral-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5">
          {/* Blind spot description */}
          <div className="mb-5">
            <h3 className="font-medium text-primary-900 dark:text-primary-50 mb-1">
              {title}
            </h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              {description}
            </p>
          </div>

          {/* Impact */}
          <div className="mb-5 p-3 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
            <p className="text-sm">
              <span className="font-medium text-neutral-700 dark:text-neutral-300">Impact:</span>{' '}
              <span className="text-neutral-600 dark:text-neutral-400">{blindSpot.impact}</span>
            </p>
          </div>

          {/* Recommended Action */}
          <div className="mb-4">
            <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">
              Recommended
            </p>
            <button
              onClick={recommended.action}
              className="w-full p-4 border-2 border-accent-200 dark:border-accent-800 bg-accent-50/50 dark:bg-accent-900/10 rounded-xl text-left hover:border-accent-300 dark:hover:border-accent-700 transition-colors"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-accent-100 dark:bg-accent-900/30">
                  <RecommendedIcon className="w-5 h-5 text-accent-600 dark:text-accent-400" />
                </div>
                <div className="flex-1">
                  <h4 className="font-medium text-primary-900 dark:text-primary-50">
                    {recommended.title}
                  </h4>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-0.5">
                    {recommended.description}
                  </p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-500 mt-2">
                    {recommended.estimate}
                  </p>
                </div>
                <ArrowRightIcon className="w-5 h-5 text-accent-600 dark:text-accent-400 shrink-0" />
              </div>
            </button>
          </div>

          {/* Other Options */}
          <div>
            <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">
              Other Options
            </p>
            <div className="flex flex-wrap gap-2">
              {blindSpot.suggestedAction !== 'discuss' && (
                <Button variant="outline" size="sm" onClick={onDiscuss}>
                  <ChatIcon className="w-4 h-4 mr-1" />
                  Discuss
                </Button>
              )}
              {blindSpot.suggestedAction !== 'research' && (
                <Button variant="outline" size="sm" onClick={onResearch}>
                  <ResearchIcon className="w-4 h-4 mr-1" />
                  Research
                </Button>
              )}
              {blindSpot.suggestedAction !== 'add_inquiry' && (
                <Button variant="outline" size="sm" onClick={onAddInquiry}>
                  <InquiryIcon className="w-4 h-4 mr-1" />
                  Add Inquiry
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={onMarkAddressed}>
                <CheckIcon className="w-4 h-4 mr-1" />
                Mark Addressed
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Icons
function BlindSpotIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ResearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <path d="M21 21l-4.35-4.35" strokeLinecap="round" />
    </svg>
  );
}

function ChatIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z" />
    </svg>
  );
}

function InquiryIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01" strokeLinecap="round" strokeLinejoin="round" />
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

function ArrowRightIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default BlindSpotModal;
