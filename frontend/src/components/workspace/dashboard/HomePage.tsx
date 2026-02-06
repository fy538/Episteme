/**
 * Home Page
 *
 * The main dashboard view with:
 * - Collapsible sidebar (exhaustive project/case navigation)
 * - Main content (focused on what matters: actions, activity, recent cases)
 */

'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useIntelligence } from '@/hooks/useIntelligence';
import { DashboardSidebar } from './DashboardSidebar';
import { RecommendedAction } from './RecommendedAction';
import { NewActivityFeed } from './NewActivityFeed';
import { RecentCases } from './RecentCases';
import { QuickActions, ChatIcon, PlusIcon, UploadIcon } from './QuickActions';
import { TensionSlideOver } from '@/components/workspace/actions/TensionSlideOver';
import { BlindSpotModal } from '@/components/workspace/actions/BlindSpotModal';
import { NoProjectsEmpty } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';
import type { Project } from '@/lib/types/project';
import type { Case, Inquiry } from '@/lib/types/case';
import type { IntelligenceItem } from '@/lib/types/intelligence';

// Extended types for the project list
interface ProjectWithCases extends Project {
  cases: CaseWithInquiries[];
}

interface CaseWithInquiries extends Case {
  inquiries: Inquiry[];
  readinessScore: number;
  tensionsCount: number;
  blindSpotsCount: number;
}

interface HomePageProps {
  projects?: ProjectWithCases[];
  isLoading?: boolean;
  onCreateProject?: () => void;
  onCreateCase?: () => void;
  className?: string;
}

export function HomePage({
  projects = [],
  isLoading: propsLoading = false,
  onCreateProject,
  onCreateCase,
  className
}: HomePageProps) {
  const router = useRouter();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Modal/SlideOver state
  const [selectedItem, setSelectedItem] = useState<IntelligenceItem | null>(null);
  const [showTensionPanel, setShowTensionPanel] = useState(false);
  const [showBlindSpotModal, setShowBlindSpotModal] = useState(false);

  // Fetch intelligence for home scope
  const { topAction, activity, isLoading, dismissItem } = useIntelligence({
    scope: 'home',
  });

  // Flatten all cases for recent cases view
  const allCases = useMemo(() => {
    return projects.flatMap(p => p.cases);
  }, [projects]);

  // Format date
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  });

  // Count new activity
  const newActivityCount = activity.filter(a => a.isNew).length;

  // Quick actions
  const quickActions = [
    {
      icon: <ChatIcon />,
      label: 'Start Chat',
      onClick: () => router.push('/chat'),
    },
    {
      icon: <PlusIcon />,
      label: 'New Case',
      onClick: () => {
        if (onCreateCase) {
          onCreateCase();
        } else if (projects.length > 0) {
          // Default to first project
          router.push(`/workspace/projects/${projects[0].id}`);
        }
      },
    },
    {
      icon: <UploadIcon />,
      label: 'Upload',
      onClick: () => {
        // TODO: Open upload modal
        console.log('Upload clicked');
      },
    },
  ];

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
        const prompt = encodeURIComponent(item.exploration?.question || item.title);
        const chatUrl = item.caseId
          ? `/chat?case=${item.caseId}&prompt=${prompt}`
          : `/chat?prompt=${prompt}`;
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
      case 'continue':
        if (item.caseId) {
          router.push(`/workspace/cases/${item.caseId}`);
        }
        break;
      default:
        if (item.caseId) {
          router.push(`/workspace/cases/${item.caseId}`);
        } else if (item.projectId) {
          router.push(`/workspace/projects/${item.projectId}`);
        }
    }
  };

  // Tension resolution handlers
  const handleTensionResolve = (choice: 'A' | 'B' | 'neither') => {
    console.log('Resolved tension:', selectedItem?.id, 'with choice:', choice);
    setShowTensionPanel(false);
    setSelectedItem(null);
  };

  const handleTensionDismiss = () => {
    console.log('Dismissed tension:', selectedItem?.id);
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
      : `/chat?prompt=${prompt}`;
    router.push(chatUrl);
    setShowBlindSpotModal(false);
  };

  const handleBlindSpotAddInquiry = () => {
    console.log('Add inquiry for blind spot:', selectedItem?.id);
    setShowBlindSpotModal(false);
  };

  const handleBlindSpotMarkAddressed = () => {
    console.log('Mark blind spot addressed:', selectedItem?.id);
    setShowBlindSpotModal(false);
    setSelectedItem(null);
  };

  // Handle create project
  const handleCreateProject = () => {
    if (onCreateProject) {
      onCreateProject();
    } else {
      router.push('/workspace/projects/new');
    }
  };

  // Loading state
  if (propsLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  return (
    <div className={cn('flex h-screen bg-neutral-50 dark:bg-neutral-950', className)}>
      {/* Sidebar - exhaustive navigation */}
      <DashboardSidebar
        projects={projects}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        onCreateProject={handleCreateProject}
      />

      {/* Main content - focused on what matters */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto py-8 px-6">
          {/* Header */}
          <header className="flex items-center justify-between mb-8">
            <h1 className="text-2xl font-bold text-primary-900 dark:text-primary-50">
              Dashboard
            </h1>
            <span className="text-sm text-neutral-500 dark:text-neutral-400">
              {today}
            </span>
          </header>

          {/* Empty state when no projects */}
          {projects.length === 0 ? (
            <NoProjectsEmpty onCreate={handleCreateProject} />
          ) : (
            <>
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

              {/* Loading state for intelligence */}
              {isLoading && (
                <section className="mb-8">
                  <div className="h-24 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-neutral-100 dark:bg-neutral-900 animate-pulse" />
                </section>
              )}

              {/* While You Were Away */}
              {activity.length > 0 && (
                <section className="mb-8">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
                      While You Were Away
                    </h2>
                    {newActivityCount > 0 && (
                      <span className="text-xs font-medium text-accent-600 dark:text-accent-400">
                        {newActivityCount} new
                      </span>
                    )}
                  </div>
                  <div className="border border-neutral-200 dark:border-neutral-800 rounded-xl overflow-hidden bg-white dark:bg-neutral-900">
                    <NewActivityFeed items={activity} maxItems={4} />
                  </div>
                </section>
              )}

              {/* Quick Actions */}
              <section className="mb-8">
                <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
                  Quick Actions
                </h2>
                <QuickActions actions={quickActions} />
              </section>

              {/* Continue Working (Recent Cases) */}
              {allCases.length > 0 && (
                <section className="mb-8">
                  <h2 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
                    Continue Working
                  </h2>
                  <RecentCases cases={allCases} maxItems={5} />
                </section>
              )}
            </>
          )}
        </div>
      </main>

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

export default HomePage;
