/**
 * Case Home Page
 *
 * The main view for a single case showing:
 * - Readiness meter (prominent)
 * - ONE recommended action
 * - Inquiries list with status
 * - Case brief (AI summary, editable)
 * - Sources with linkage
 * - Recent chat
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useIntelligence } from '@/hooks/useIntelligence';
import { useCaseReadiness } from '@/hooks/useCaseReadiness';
import { ReadinessMeter } from '@/components/ui/readiness-meter';
import { RecommendedAction } from '@/components/workspace/dashboard/RecommendedAction';
import { TensionSlideOver } from '@/components/workspace/actions/TensionSlideOver';
import { BlindSpotModal } from '@/components/workspace/actions/BlindSpotModal';
import { BriefContextModal } from '@/components/workspace/actions/BriefContextModal';
import { IntelligentBrief } from '@/components/workspace/case/IntelligentBrief';
import { NoInquiriesEmpty } from '@/components/ui/empty-state';
import { Button } from '@/components/ui/button';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { MessageInput } from '@/components/chat/MessageInput';
import { cn } from '@/lib/utils';
import type { Case, Inquiry } from '@/lib/types/case';
import type { IntelligenceItem, BriefContextSettings } from '@/lib/types/intelligence';

interface Source {
  id: string;
  name: string;
  type: 'document' | 'research';
  linkedInquiries: number;
  isNew?: boolean;
}

interface CaseHomePageProps {
  caseData: Case;
  inquiries: Inquiry[];
  projectTitle?: string;
  sources?: Source[];
  lastChatMessage?: {
    content: string;
    timestamp: string;
  };
  onStartChat?: () => void;
  onOpenBrief?: () => void;
  onOpenSettings?: () => void;
  onUploadSource?: () => void;
  onGenerateResearch?: () => void;
  onAddInquiry?: () => void;
  onDelete?: () => void;
  className?: string;
}

// Default empty — real sources should come from API via props
const defaultSources: Source[] = [];

// Brief summary is now handled by IntelligentBrief component

export function CaseHomePage({
  caseData,
  inquiries,
  projectTitle,
  sources = defaultSources,
  lastChatMessage,
  onStartChat,
  onOpenBrief,
  onOpenSettings,
  onUploadSource,
  onGenerateResearch,
  onAddInquiry,
  onDelete,
  className,
}: CaseHomePageProps) {
  const router = useRouter();

  // Modal/SlideOver state
  const [selectedItem, setSelectedItem] = useState<IntelligenceItem | null>(null);
  const [showTensionPanel, setShowTensionPanel] = useState(false);
  const [showBlindSpotModal, setShowBlindSpotModal] = useState(false);
  const [showBriefContextModal, setShowBriefContextModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Fetch intelligence and readiness
  const { topAction, dismissItem } = useIntelligence({
    scope: 'case',
    caseId: caseData.id,
  });

  const readiness = useCaseReadiness({ caseId: caseData.id });

  // Group inquiries by status
  const resolvedInquiries = inquiries.filter(i => i.status === 'resolved');
  const activeInquiries = inquiries.filter(i => i.status !== 'resolved');

  // Handle action click from RecommendedAction
  const handleActionClick = (item: IntelligenceItem) => {
    setSelectedItem(item);

    switch (item.type) {
      case 'tension':
        setShowTensionPanel(true);
        break;
      case 'blind_spot':
        setShowBlindSpotModal(true);
        break;
      case 'explore':
        // Navigate to chat with pre-filled prompt
        const prompt = encodeURIComponent(item.exploration?.question || item.title);
        router.push(`/?case=${caseData.id}&prompt=${prompt}`);
        break;
      case 'research_ready':
        // Navigate to document viewer or research page
        router.push(`/cases/${caseData.id}/research`);
        break;
      case 'ready':
        // Navigate to brief editor
        router.push(`/cases/${caseData.id}/brief`);
        break;
      default:
        // Default: navigate to case detail
        router.push(`/cases/${caseData.id}`);
    }
  };

  // Tension resolution handlers
  const handleTensionResolve = (choice: 'A' | 'B' | 'neither') => {
    console.log('Resolved tension:', selectedItem?.id, 'with choice:', choice);
    // TODO: Call API to resolve tension
    setShowTensionPanel(false);
    setSelectedItem(null);
  };

  const handleTensionDismiss = () => {
    console.log('Dismissed tension:', selectedItem?.id);
    // TODO: Call API to mark as unresolved
    setShowTensionPanel(false);
    setSelectedItem(null);
  };

  // Blind spot handlers
  const handleBlindSpotResearch = () => {
    console.log('Research blind spot:', selectedItem?.id);
    // TODO: Trigger research generation
    setShowBlindSpotModal(false);
    router.push(`/cases/${caseData.id}/research?topic=${encodeURIComponent(selectedItem?.blindSpot?.area || '')}`);
  };

  const handleBlindSpotDiscuss = () => {
    console.log('Discuss blind spot:', selectedItem?.id);
    const prompt = encodeURIComponent(`Help me understand ${selectedItem?.blindSpot?.area || selectedItem?.title}`);
    router.push(`/?case=${caseData.id}&prompt=${prompt}`);
    setShowBlindSpotModal(false);
  };

  const handleBlindSpotAddInquiry = () => {
    console.log('Add inquiry for blind spot:', selectedItem?.id);
    // TODO: Open create inquiry modal or navigate
    setShowBlindSpotModal(false);
  };

  const handleBlindSpotMarkAddressed = () => {
    console.log('Mark blind spot addressed:', selectedItem?.id);
    // TODO: Call API to mark as addressed
    setShowBlindSpotModal(false);
    setSelectedItem(null);
  };

  // Brief context handlers
  const handleBriefRegenerate = (settings: BriefContextSettings) => {
    console.log('Regenerate brief with settings:', settings);
    // TODO: Call API to regenerate brief
    setShowBriefContextModal(false);
  };

  return (
    <div className={cn('max-w-3xl mx-auto py-8 px-4', className)}>
      {/* Header */}
      <header className="mb-6">
        {/* Breadcrumb */}
        {projectTitle && (
          <Link
            href={`/projects/${caseData.project}`}
            className="text-sm text-neutral-500 dark:text-neutral-400 hover:text-accent-600 dark:hover:text-accent-400 mb-2 inline-flex items-center gap-1"
          >
            <ChevronLeftIcon className="w-4 h-4" />
            {projectTitle}
          </Link>
        )}

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-primary-900 dark:text-primary-50">
              {caseData.title}
            </h1>
            {caseData.decision_question && (
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                {caseData.decision_question}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={onOpenSettings} title="Settings">
              <SettingsIcon className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon" onClick={onOpenBrief} title="Case Brief">
              <DocumentIcon className="w-5 h-5" />
            </Button>
            {onDelete && (
              <Button variant="ghost" size="icon" onClick={() => setShowDeleteConfirm(true)} title="Archive case">
                <TrashIcon className="w-5 h-5" />
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Inline chat input */}
      <div className="mb-6 rounded-lg border border-neutral-200/60 dark:border-neutral-700/50 overflow-hidden">
        <MessageInput
          variant="hero"
          onSend={(content) => {
            const prompt = encodeURIComponent(content);
            router.push(`/cases/${caseData.id}?prompt=${prompt}`);
          }}
          placeholder="Continue working on this case..."
        />
      </div>

      {/* Readiness Meter */}
      <section className="mb-8 p-4 border border-neutral-200/80 dark:border-neutral-800/80 rounded-md bg-neutral-50/50 dark:bg-neutral-900/50">
        <ReadinessMeter
          score={readiness.score}
          inquiries={readiness.inquiries}
          tensionsCount={readiness.tensionsCount}
          blindSpotsCount={readiness.blindSpotsCount}
          variant="full"
        />
      </section>

      {/* Recommended Action */}
      {topAction && (
        <section className="mb-8">
          <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
            Recommended Action
          </h2>
          <RecommendedAction
            item={topAction}
            variant="detailed"
            onAction={handleActionClick}
            onDismiss={() => dismissItem(topAction.id)}
          />
        </section>
      )}

      {/* Inquiries */}
      <section className="mb-8">
        <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
          Inquiries
        </h2>
        {inquiries.length === 0 ? (
          <NoInquiriesEmpty onCreate={onAddInquiry || (() => {})} />
        ) : (
          <>
            <div className="space-y-2">
              {inquiries.map((inquiry) => (
                <InquiryRow key={inquiry.id} inquiry={inquiry} caseId={caseData.id} />
              ))}
            </div>
            <Button variant="ghost" size="sm" className="mt-3" onClick={onAddInquiry}>
              <PlusIcon className="w-4 h-4 mr-1" />
              Add Inquiry
            </Button>
          </>
        )}
      </section>

      {/* Intelligent Brief */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
            Case Brief
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowBriefContextModal(true)}
              className="text-xs text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300"
            >
              Context
            </button>
            <Link
              href={`/cases/${caseData.id}/brief`}
              className="text-xs text-accent-600 dark:text-accent-400 hover:underline"
            >
              Full editor →
            </Link>
          </div>
        </div>
        <IntelligentBrief
          caseId={caseData.id}
          caseData={caseData}
          inquiries={inquiries}
          onNavigateToInquiry={(inquiryId) => {
            router.push(`/cases/${caseData.id}?inquiry=${inquiryId}`);
          }}
          onStartChat={onStartChat}
          onOpenBriefEditor={() => {
            router.push(`/cases/${caseData.id}/brief`);
          }}
        />
      </section>

      {/* Sources */}
      <section className="mb-8">
        <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
          Sources & Research
        </h2>
        <div className="space-y-1">
          {sources.map((source) => (
            <SourceRow key={source.id} source={source} />
          ))}
        </div>
        <div className="flex items-center gap-2 mt-3">
          <Button variant="ghost" size="sm" onClick={onUploadSource}>
            <UploadIcon className="w-4 h-4 mr-1" />
            Upload Source
          </Button>
          <Button variant="ghost" size="sm" onClick={onGenerateResearch}>
            <SparklesIcon className="w-4 h-4 mr-1" />
            Generate Research
          </Button>
        </div>
      </section>

      {/* Recent Chat — only shown when real data is provided */}
      {lastChatMessage && (
        <section>
          <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
            Recent Chat
          </h2>
          <div className="p-4 border border-neutral-200/80 dark:border-neutral-800/80 rounded-md">
            <p className="text-sm text-neutral-700 dark:text-neutral-300 line-clamp-2">
              &ldquo;{lastChatMessage.content}&rdquo;
            </p>
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-neutral-100 dark:border-neutral-800">
              <span className="text-xs text-neutral-500 dark:text-neutral-400">
                {lastChatMessage.timestamp}
              </span>
              <Button size="sm" onClick={onStartChat}>
                Continue →
              </Button>
            </div>
          </div>
        </section>
      )}

      {/* Tension Slide Over */}
      {selectedItem?.tension && (
        <TensionSlideOver
          tension={selectedItem.tension}
          title={selectedItem.title}
          caseName={caseData.title}
          inquiryName={selectedItem.inquiryTitle}
          isOpen={showTensionPanel}
          onClose={() => {
            setShowTensionPanel(false);
            setSelectedItem(null);
          }}
          onResolve={handleTensionResolve}
          onDismiss={handleTensionDismiss}
        />
      )}

      {/* Blind Spot Modal */}
      {selectedItem?.blindSpot && (
        <BlindSpotModal
          blindSpot={selectedItem.blindSpot}
          title={selectedItem.title}
          description={selectedItem.description}
          caseName={caseData.title}
          inquiryName={selectedItem.inquiryTitle}
          isOpen={showBlindSpotModal}
          onClose={() => {
            setShowBlindSpotModal(false);
            setSelectedItem(null);
          }}
          onResearch={handleBlindSpotResearch}
          onDiscuss={handleBlindSpotDiscuss}
          onAddInquiry={handleBlindSpotAddInquiry}
          onMarkAddressed={handleBlindSpotMarkAddressed}
        />
      )}

      {/* Brief Context Modal */}
      <BriefContextModal
        inquiries={inquiries}
        sources={sources}
        isOpen={showBriefContextModal}
        onClose={() => setShowBriefContextModal(false)}
        onRegenerate={handleBriefRegenerate}
      />

      {/* Delete Confirm Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={() => {
          setShowDeleteConfirm(false);
          onDelete?.();
        }}
        title="Archive case"
        description={`"${caseData.title}" will be archived. You can restore it later.`}
        confirmLabel="Archive"
        variant="danger"
      />
    </div>
  );
}

// Inquiry row component
function InquiryRow({ inquiry, caseId }: { inquiry: Inquiry; caseId: string }) {
  const isResolved = inquiry.status === 'resolved';

  return (
    <Link
      href={`/cases/${caseId}?inquiry=${inquiry.id}`}
      className="flex items-center justify-between p-3 border border-neutral-200 dark:border-neutral-800 rounded-lg hover:border-accent-300 dark:hover:border-accent-700 transition-colors"
    >
      <div className="flex items-center gap-3">
        {isResolved ? (
          <CheckCircleIcon className="w-5 h-5 text-success-500" />
        ) : inquiry.status === 'investigating' ? (
          <LoadingIcon className="w-5 h-5 text-accent-500" />
        ) : (
          <CircleIcon className="w-5 h-5 text-neutral-300 dark:text-neutral-600" />
        )}
        <span className={cn(
          'text-sm font-medium',
          isResolved
            ? 'text-neutral-500 dark:text-neutral-400'
            : 'text-primary-900 dark:text-primary-50'
        )}>
          {inquiry.title}
        </span>
      </div>

      <div className="flex items-center gap-2">
        {!isResolved && (
          <span className="text-xs text-neutral-500 dark:text-neutral-400">
            {inquiry.status === 'investigating' ? 'Investigating' : 'Open'}
          </span>
        )}
        <ChevronRightIcon className="w-4 h-4 text-neutral-400" />
      </div>
    </Link>
  );
}

// Source row component
function SourceRow({ source }: { source: Source }) {
  return (
    <div className="flex items-center justify-between py-2 px-3 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 rounded-lg transition-colors">
      <div className="flex items-center gap-2">
        {source.type === 'document' ? (
          <DocumentSmallIcon className="w-4 h-4 text-neutral-400" />
        ) : (
          <SparklesIcon className="w-4 h-4 text-accent-500" />
        )}
        <span className="text-sm text-primary-900 dark:text-primary-50">
          {source.name}
        </span>
        {source.isNew && (
          <span className="text-xs bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400 px-1.5 py-0.5 rounded">
            NEW
          </span>
        )}
      </div>
      <span className="text-xs text-neutral-500 dark:text-neutral-400">
        → {source.linkedInquiries} inquir{source.linkedInquiries !== 1 ? 'ies' : 'y'}
      </span>
    </div>
  );
}

// Icons
function ChevronLeftIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="3 6 5 6 21 6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
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

function DocumentIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" strokeLinecap="round" />
    </svg>
  );
}

function DocumentSmallIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <path d="M14 2v6h6" strokeLinecap="round" />
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function EditIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
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

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3zM5 19l.5 1.5L7 21l-1.5.5L5 23l-.5-1.5L3 21l1.5-.5L5 19zM19 10l.5 1.5L21 12l-1.5.5L19 14l-.5-1.5L17 12l1.5-.5L19 10z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
    </svg>
  );
}

function LoadingIcon({ className }: { className?: string }) {
  return (
    <svg className={cn(className, 'animate-spin')} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 019.17 6" strokeLinecap="round" />
    </svg>
  );
}

export default CaseHomePage;
