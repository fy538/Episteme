/**
 * Project Home Page
 *
 * The main view for a single project showing:
 * - ONE recommended action (most important case)
 * - ONE exploration prompt (cross-case connection)
 * - New activity for this project
 * - Cases with readiness indicators
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useIntelligence } from '@/hooks/useIntelligence';
import { RecommendedAction } from '@/components/workspace/dashboard/RecommendedAction';
import { NewActivityFeed } from '@/components/workspace/dashboard/NewActivityFeed';
import { ReadinessMeter } from '@/components/ui/readiness-meter';
import { TensionSlideOver } from '@/components/workspace/actions/TensionSlideOver';
import { BlindSpotModal } from '@/components/workspace/actions/BlindSpotModal';
import { NoCasesEmpty } from '@/components/ui/empty-state';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { Project } from '@/lib/types/project';
import type { Case, Inquiry } from '@/lib/types/case';
import type { IntelligenceItem } from '@/lib/types/intelligence';

interface CaseWithInquiries extends Case {
  inquiries: Inquiry[];
  readinessScore: number;
  tensionsCount: number;
  blindSpotsCount: number;
}

interface ProjectHomePageProps {
  project: Project;
  cases: CaseWithInquiries[];
  onCreateCase?: () => void;
  onStartChat?: () => void;
  onOpenSettings?: () => void;
  className?: string;
}

export function ProjectHomePage({
  project,
  cases,
  onCreateCase,
  onStartChat,
  onOpenSettings,
  className,
}: ProjectHomePageProps) {
  const router = useRouter();

  // Modal/SlideOver state
  const [selectedItem, setSelectedItem] = useState<IntelligenceItem | null>(null);
  const [showTensionPanel, setShowTensionPanel] = useState(false);
  const [showBlindSpotModal, setShowBlindSpotModal] = useState(false);

  // Fetch intelligence for project scope
  const { topAction, exploration, activity, isLoading, dismissItem } = useIntelligence({
    scope: 'project',
    projectId: project.id,
  });

  // Calculate project stats
  const readyCases = cases.filter(c => c.readinessScore >= 90 && c.tensionsCount === 0).length;
  const newActivityCount = activity.filter(a => a.isNew).length;

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
        const chatUrl = item.caseId
          ? `/chat?case=${item.caseId}&prompt=${prompt}`
          : `/chat?project=${project.id}&prompt=${prompt}`;
        router.push(chatUrl);
        break;
      case 'research_ready':
        if (item.caseId) {
          router.push(`/workspace/cases/${item.caseId}/research`);
        }
        break;
      case 'ready':
        if (item.caseId) {
          router.push(`/workspace/cases/${item.caseId}/brief`);
        }
        break;
      default:
        // Default: navigate to the relevant case
        if (item.caseId) {
          router.push(`/workspace/cases/${item.caseId}`);
        }
    }
  };

  // Handle exploration click
  const handleExploreClick = (item: IntelligenceItem) => {
    const prompt = encodeURIComponent(item.exploration?.question || item.title);
    const chatUrl = item.caseId
      ? `/chat?case=${item.caseId}&prompt=${prompt}`
      : `/chat?project=${project.id}&prompt=${prompt}`;
    router.push(chatUrl);
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
    setShowBlindSpotModal(false);
    if (selectedItem?.caseId) {
      router.push(`/workspace/cases/${selectedItem.caseId}/research?topic=${encodeURIComponent(selectedItem?.blindSpot?.area || '')}`);
    }
  };

  const handleBlindSpotDiscuss = () => {
    console.log('Discuss blind spot:', selectedItem?.id);
    const prompt = encodeURIComponent(`Help me understand ${selectedItem?.blindSpot?.area || selectedItem?.title}`);
    const chatUrl = selectedItem?.caseId
      ? `/chat?case=${selectedItem.caseId}&prompt=${prompt}`
      : `/chat?project=${project.id}&prompt=${prompt}`;
    router.push(chatUrl);
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

  return (
    <div className={cn('max-w-3xl mx-auto py-8 px-4', className)}>
      {/* Header */}
      <header className="mb-6">
        {/* Breadcrumb */}
        <Link
          href="/workspace"
          className="text-sm text-neutral-500 dark:text-neutral-400 hover:text-accent-600 dark:hover:text-accent-400 mb-2 inline-flex items-center gap-1"
        >
          <ChevronLeftIcon className="w-4 h-4" />
          Home
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-primary-900 dark:text-primary-50">
              {project.title}
            </h1>
            {project.description && (
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                {project.description}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={onOpenSettings} title="Settings">
              <SettingsIcon className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon" onClick={onStartChat} title="New Chat">
              <ChatIcon className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Recommended Action */}
      {topAction && !isLoading && (
        <section className="mb-8">
          <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
            Recommended Action
          </h2>
          <RecommendedAction
            item={topAction}
            onAction={handleActionClick}
            onDismiss={() => dismissItem(topAction.id)}
          />
        </section>
      )}

      {/* Worth Exploring */}
      {exploration && (
        <section className="mb-8">
          <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
            Worth Exploring
          </h2>
          <ExplorationCard item={exploration} onExplore={handleExploreClick} />
        </section>
      )}

      {/* New Activity */}
      {activity.length > 0 && (
        <section className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
              New This Week
            </h2>
            {newActivityCount > 0 && (
              <span className="text-xs font-medium text-accent-600 dark:text-accent-400">
                {newActivityCount} new
              </span>
            )}
          </div>
          <div className="border border-neutral-200 dark:border-neutral-800 rounded-xl overflow-hidden">
            <NewActivityFeed items={activity} maxItems={3} />
          </div>
        </section>
      )}

      {/* Cases */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
            Cases
          </h2>
          {cases.length > 0 && (
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              {readyCases}/{cases.length} ready
            </span>
          )}
        </div>

        {cases.length === 0 ? (
          <NoCasesEmpty onCreate={onCreateCase || (() => {})} />
        ) : (
          <>
            <div className="space-y-3">
              {cases.map((caseItem) => (
                <CaseCard key={caseItem.id} caseItem={caseItem} />
              ))}
            </div>

            <Button variant="outline" className="w-full mt-4" onClick={onCreateCase}>
              <PlusIcon className="w-4 h-4 mr-2" />
              New Case
            </Button>
          </>
        )}
      </section>

      {/* Tension Slide Over */}
      {selectedItem?.tension && (
        <TensionSlideOver
          tension={selectedItem.tension}
          title={selectedItem.title}
          caseName={selectedItem.caseTitle}
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
          caseName={selectedItem.caseTitle}
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
    </div>
  );
}

// Exploration card component
function ExplorationCard({
  item,
  onExplore
}: {
  item: IntelligenceItem;
  onExplore: (item: IntelligenceItem) => void;
}) {
  return (
    <div className="p-4 border border-primary-200 dark:border-primary-800 rounded-xl bg-primary-50/50 dark:bg-primary-900/10">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30">
          <ExploreIcon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-primary-900 dark:text-primary-50 mb-1">
            "{item.exploration?.question || item.title}"
          </p>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            {item.exploration?.context || item.description}
          </p>
          <Button
            size="sm"
            variant="ghost"
            className="mt-2 -ml-2"
            onClick={() => onExplore(item)}
          >
            Explore →
          </Button>
        </div>
      </div>
    </div>
  );
}

// Case card component
function CaseCard({ caseItem }: { caseItem: CaseWithInquiries }) {
  const [expanded, setExpanded] = useState(false);

  const isReady = caseItem.readinessScore >= 90 && caseItem.tensionsCount === 0;
  const resolvedInquiries = caseItem.inquiries.filter(i => i.status === 'resolved').length;

  return (
    <div className="border border-neutral-200 dark:border-neutral-800 rounded-xl overflow-hidden">
      {/* Case Header */}
      <div className="flex items-center gap-3 p-4">
        {/* Expand toggle */}
        {caseItem.inquiries.length > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-0.5 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded"
          >
            <ChevronIcon
              className={cn(
                'w-4 h-4 text-neutral-400 transition-transform',
                expanded && 'rotate-90'
              )}
            />
          </button>
        )}

        {/* Case info */}
        <Link
          href={`/workspace/cases/${caseItem.id}`}
          className="flex-1 flex items-center justify-between hover:opacity-80 transition-opacity"
        >
          <div className="flex items-center gap-3">
            {isReady ? (
              <CheckCircleIcon className="w-5 h-5 text-success-500" />
            ) : (
              <CircleIcon className="w-5 h-5 text-neutral-300 dark:text-neutral-600" />
            )}
            <div>
              <h3 className="font-medium text-primary-900 dark:text-primary-50">
                {caseItem.title}
              </h3>
              <div className="flex items-center gap-2 mt-0.5">
                {caseItem.tensionsCount > 0 && (
                  <span className="text-xs text-warning-600 dark:text-warning-400">
                    {caseItem.tensionsCount} tension{caseItem.tensionsCount !== 1 ? 's' : ''}
                  </span>
                )}
                {caseItem.blindSpotsCount > 0 && (
                  <span className="text-xs text-accent-600 dark:text-accent-400">
                    {caseItem.blindSpotsCount} blind spot{caseItem.blindSpotsCount !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
            </div>
          </div>

          <ReadinessMeter
            score={caseItem.readinessScore}
            inquiries={{
              total: caseItem.inquiries.length,
              resolved: resolvedInquiries,
            }}
            variant="minimal"
          />
        </Link>
      </div>

      {/* Expanded Inquiries */}
      {expanded && caseItem.inquiries.length > 0 && (
        <div className="px-4 pb-4 pt-0 ml-9 space-y-1">
          {caseItem.inquiries.map((inquiry) => (
            <Link
              key={inquiry.id}
              href={`/workspace/cases/${caseItem.id}?inquiry=${inquiry.id}`}
              className="flex items-center gap-2 py-1.5 px-2 -mx-2 rounded hover:bg-neutral-50 dark:hover:bg-neutral-800/30 transition-colors"
            >
              {inquiry.status === 'resolved' ? (
                <CheckIcon className="w-3.5 h-3.5 text-success-500" />
              ) : (
                <CircleSmallIcon className="w-3.5 h-3.5 text-neutral-300 dark:text-neutral-600" />
              )}
              <span
                className={cn(
                  'text-sm',
                  inquiry.status === 'resolved'
                    ? 'text-neutral-500 dark:text-neutral-400'
                    : 'text-primary-900 dark:text-primary-50'
                )}
              >
                {inquiry.title}
              </span>
            </Link>
          ))}
        </div>
      )}
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

function ChevronIcon({ className }: { className?: string }) {
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

function ExploreIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M16.24 7.76l-2.12 6.36-6.36 2.12 2.12-6.36 6.36-2.12z" />
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

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CircleSmallIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="4" />
    </svg>
  );
}

export default ProjectHomePage;
