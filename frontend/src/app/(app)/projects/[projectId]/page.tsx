/**
 * Project Dashboard
 *
 * Unified scroll layout with AI summary, graph overlay, inline chat,
 * action items, documents, and case overview.
 *
 * No tabs — one continuous page. Graph opens as a full-viewport overlay.
 * Chat opens in a right panel (like the case workspace) instead of navigating away.
 */

'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Spinner } from '@/components/ui/spinner';
import { Button } from '@/components/ui/button';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { ProjectSummaryView } from '@/components/workspace/project/ProjectSummaryView';
import { GraphOverlay } from '@/components/graph/GraphOverlay';
import { ChatPanel } from '@/components/workspace/ChatPanel';
import { MessageInput } from '@/components/chat/MessageInput';
import { ScaffoldingChat } from '@/components/workspace/case/ScaffoldingChat';
import { DocumentUpload } from '@/components/documents/DocumentUpload';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { NetworkErrorBanner } from '@/components/ui/network-error-banner';
import { useProjectDashboard } from '@/hooks/useProjectDashboard';
import { useProjectGraph } from '@/hooks/useProjectGraph';
import { useProjectSummary } from '@/hooks/useProjectSummary';
import { useProjectChat } from '@/hooks/useProjectChat';
import { projectsAPI } from '@/lib/api/projects';
import { documentsAPI } from '@/lib/api/documents';
import { cn } from '@/lib/utils';
import type { CaseStage } from '@/lib/types/plan';
import type { UploadedDocument } from '@/lib/types/document';
import { getDocumentPipelineStatus } from '@/lib/types/document';
import type {
  ProjectCaseSummary,
  ProjectStats,
  ProjectActionItem,
} from '@/hooks/useProjectDashboard';

export default function ProjectDashboard() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;

  // ─── Data hooks ───
  const { project, cases, stats, actionItems, isLoading, error } = useProjectDashboard(projectId);
  const { data: graphData } = useProjectGraph(projectId);
  const { summary, isStale, isGenerating, regenerate } = useProjectSummary(projectId);
  const { data: documents = [], refetch: refetchDocs } = useQuery({
    queryKey: ['project-documents', projectId],
    queryFn: () => documentsAPI.listUploadedDocuments({ projectId }),
    staleTime: 30_000,
  });

  // ─── Chat panel ───
  const {
    threadId: chatThreadId,
    isChatOpen,
    isChatCollapsed,
    isCreatingThread,
    openChat,
    toggleChat,
    closeChat,
  } = useProjectChat(projectId);
  const [pendingInitialMessage, setPendingInitialMessage] = useState<string | null>(null);

  // ─── Graph overlay ───
  const [showGraphOverlay, setShowGraphOverlay] = useState(false);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);

  // ─── Scaffolding modal (for "New Case" from existing cases list) ───
  const [showScaffolding, setShowScaffolding] = useState(false);

  // ─── Documents upload ───
  const [showUpload, setShowUpload] = useState(false);

  // ─── Delete confirm ───
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // ─── Derived ───
  const hasSummary = summary && summary.status !== 'none';
  const hasGraphData = graphData && graphData.nodes.length > 0;
  const hasCases = cases.length > 0;

  // ─── Handlers ───
  const handleCitationClick = useCallback((nodeId: string) => {
    setFocusedNodeId(nodeId);
    setShowGraphOverlay(true);
  }, []);

  const handleOpenGraph = useCallback(() => {
    setFocusedNodeId(null);
    setShowGraphOverlay(true);
  }, []);

  const handleCaseCreated = useCallback((caseId: string) => {
    setShowScaffolding(false);
    router.push(`/cases/${caseId}/overview`);
  }, [router]);

  const handleDelete = useCallback(async () => {
    setShowDeleteConfirm(false);
    await projectsAPI.deleteProject(projectId);
    router.push('/');
  }, [projectId, router]);

  const handleChatSend = useCallback(async (content: string) => {
    setPendingInitialMessage(content);
    await openChat(content);
  }, [openChat]);

  const handleInitialMessageSent = useCallback(() => {
    setPendingInitialMessage(null);
  }, []);

  // Cmd+/ to toggle chat panel, Escape to close scaffolding modal
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        if (isChatOpen) {
          toggleChat();
        }
      }
      if (e.key === 'Escape' && showScaffolding) {
        e.preventDefault();
        setShowScaffolding(false);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isChatOpen, toggleChat, showScaffolding]);

  // ─── Loading / Not Found ───
  if (isLoading && !project) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-neutral-500">Project not found</p>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="relative flex flex-col h-full bg-neutral-50 dark:bg-primary-950">
        <NetworkErrorBanner
          isVisible={!!error}
          onRetry={() => window.location.reload()}
        />

        {/* Two-column layout: main scroll + optional chat panel */}
        <div className="flex flex-1 min-h-0">
          {/* ─── Main scroll content ─── */}
          <main className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">

              {/* Header */}
              <header>
                <Link
                  href="/"
                  className="text-sm text-neutral-500 dark:text-neutral-400 hover:text-accent-600 dark:hover:text-accent-400 mb-2 inline-flex items-center gap-1"
                >
                  <ChevronLeftIcon className="w-4 h-4" />
                  Home
                </Link>

                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h1 className="text-2xl font-bold text-primary-900 dark:text-primary-50">
                      {project.title}
                    </h1>
                    {project.description && (
                      <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                        {project.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button variant="ghost" size="icon" onClick={() => setShowDeleteConfirm(true)} title="Archive project">
                      <TrashIcon className="w-5 h-5" />
                    </Button>
                  </div>
                </div>
              </header>

              {/* Stats bar */}
              {!isLoading && stats.totalCases > 0 && (
                <div className="flex items-center gap-4 px-1">
                  <StatPill
                    label="Cases"
                    value={`${stats.readyCases}/${stats.totalCases} ready`}
                    variant={stats.readyCases === stats.totalCases ? 'success' : 'default'}
                  />
                  {stats.totalInquiries > 0 && (
                    <StatPill
                      label="Inquiries"
                      value={`${stats.resolvedInquiries}/${stats.totalInquiries} resolved`}
                      variant={stats.resolvedInquiries === stats.totalInquiries ? 'success' : 'default'}
                    />
                  )}
                  {stats.highRiskUntested > 0 && (
                    <StatPill
                      label="Assumptions"
                      value={`${stats.highRiskUntested} high-risk untested`}
                      variant="warning"
                    />
                  )}
                </div>
              )}

              {/* AI Summary */}
              {hasSummary && (
                <ProjectSummaryView
                  summary={summary}
                  isStale={isStale}
                  isGenerating={isGenerating}
                  onRegenerate={() => regenerate()}
                  onCitationClick={handleCitationClick}
                  graphNodes={graphData?.nodes}
                />
              )}

              {/* Graph CTA */}
              {hasGraphData && (
                <button
                  onClick={handleOpenGraph}
                  className={cn(
                    'flex items-center gap-3 w-full p-4 rounded-lg border',
                    'border-neutral-200/80 dark:border-neutral-800/80',
                    'hover:border-accent-300 dark:hover:border-accent-700',
                    'hover:bg-accent-50/30 dark:hover:bg-accent-900/10',
                    'transition-all duration-150 text-left group'
                  )}
                >
                  <div className="w-8 h-8 rounded-md bg-accent-100 dark:bg-accent-900/40 flex items-center justify-center shrink-0">
                    <GraphIcon className="w-4 h-4 text-accent-600 dark:text-accent-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-primary-900 dark:text-primary-100">
                      View Knowledge Graph
                    </p>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">
                      {graphData.nodes.length} nodes &middot; {graphData.edges.length} connections
                    </p>
                  </div>
                  <ChevronIcon className="w-4 h-4 text-neutral-400 group-hover:text-accent-500 transition-colors shrink-0" />
                </button>
              )}

              {/* Scoped chat input */}
              <div className="rounded-lg border border-neutral-200/60 dark:border-neutral-700/50 overflow-hidden">
                <MessageInput
                  variant="hero"
                  onSend={handleChatSend}
                  disabled={isCreatingThread}
                  placeholder={`Ask about ${project.title}...`}
                />
              </div>

              {/* Action items */}
              {!isLoading && actionItems.length > 0 && (
                <section>
                  <SectionTitle>Next Steps</SectionTitle>
                  <div className="space-y-2">
                    {actionItems.map((item) => (
                      <ActionItemRow key={item.id} item={item} />
                    ))}
                  </div>
                </section>
              )}

              {/* Documents / Sources */}
              {(documents.length > 0 || showUpload) && (
                <section>
                  <div className="flex items-center justify-between mb-3">
                    <SectionTitle noMargin>Sources</SectionTitle>
                    <button
                      onClick={() => setShowUpload(!showUpload)}
                      className="text-xs text-accent-600 dark:text-accent-400 hover:text-accent-700 dark:hover:text-accent-300"
                    >
                      {showUpload ? 'Done' : '+ Upload'}
                    </button>
                  </div>

                  {showUpload && (
                    <div className="mb-3">
                      <DocumentUpload
                        projectId={projectId}
                        caseId=""
                        compact
                        onUploaded={() => {/* refetch deferred to onAllComplete */}}
                        onAllComplete={() => {
                          refetchDocs();
                          setShowUpload(false);
                        }}
                      />
                    </div>
                  )}

                  {documents.length > 0 && (
                    <div className="space-y-1.5">
                      {documents.map((doc) => (
                        <CompactDocRow key={doc.id} doc={doc} />
                      ))}
                    </div>
                  )}
                </section>
              )}

              {/* Upload CTA when no documents yet */}
              {documents.length === 0 && !showUpload && !isLoading && (
                <button
                  onClick={() => setShowUpload(true)}
                  className={cn(
                    'flex items-center gap-3 w-full p-4 rounded-lg border border-dashed',
                    'border-neutral-300 dark:border-neutral-700',
                    'hover:border-accent-300 dark:hover:border-accent-700',
                    'hover:bg-accent-50/30 dark:hover:bg-accent-900/10',
                    'transition-all duration-150 text-left'
                  )}
                >
                  <UploadIcon className="w-4 h-4 text-neutral-400" />
                  <span className="text-sm text-neutral-500 dark:text-neutral-400">
                    Upload documents to build project context
                  </span>
                </button>
              )}

              {/* Cases section — or inline scaffolding when empty */}
              {!hasCases && !isLoading ? (
                <section>
                  <SectionTitle>Get Started</SectionTitle>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-3">
                    Describe a decision you&apos;re working through. We&apos;ll help you structure it into an investigation.
                  </p>
                  <div className="rounded-lg border border-neutral-200/80 dark:border-neutral-700/80 overflow-hidden h-[50vh]">
                    <ScaffoldingChat
                      projectId={projectId}
                      onCaseCreated={handleCaseCreated}
                    />
                  </div>
                </section>
              ) : (
                <section>
                  <div className="flex items-center justify-between mb-3">
                    <SectionTitle noMargin>Cases</SectionTitle>
                    {hasCases && (
                      <span className="text-xs text-neutral-500 dark:text-neutral-400">
                        {stats.readyCases}/{stats.totalCases} ready
                      </span>
                    )}
                  </div>

                  <div className="space-y-3">
                    {cases.map((caseItem) => (
                      <ProjectCaseCard key={caseItem.id} caseItem={caseItem} />
                    ))}
                  </div>

                  <Button
                    variant="outline"
                    className="w-full mt-4"
                    onClick={() => setShowScaffolding(true)}
                  >
                    <PlusIcon className="w-4 h-4 mr-2" />
                    New Case
                  </Button>
                </section>
              )}
            </div>
          </main>

          {/* ─── Right: Chat Panel ─── */}
          {isChatOpen && chatThreadId && (
            isChatCollapsed ? (
              <aside className="w-10 border-l border-neutral-200/60 dark:border-neutral-800/60 bg-white dark:bg-neutral-950 shrink-0 flex flex-col items-center pt-3">
                <button
                  onClick={toggleChat}
                  className="p-1.5 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
                  title="Expand chat"
                >
                  <ChatBubbleIcon className="w-4 h-4 text-neutral-500" />
                </button>
              </aside>
            ) : (
              <aside className="w-[380px] border-l border-neutral-200/60 dark:border-neutral-800/60 shrink-0 flex flex-col bg-white dark:bg-neutral-950">
                {/* Chat header with collapse button */}
                <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-200/60 dark:border-neutral-800/60 shrink-0">
                  <span className="text-xs font-medium text-neutral-600 dark:text-neutral-300">
                    Chat
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={toggleChat}
                      className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
                      title="Collapse chat"
                    >
                      <PanelCollapseIcon className="w-3.5 h-3.5 text-neutral-400" />
                    </button>
                    <button
                      onClick={closeChat}
                      className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
                      title="Close chat"
                    >
                      <CloseIcon className="w-3.5 h-3.5 text-neutral-400" />
                    </button>
                  </div>
                </div>
                <div className="flex-1 min-h-0">
                  <ChatPanel
                    threadId={chatThreadId}
                    variant="panel"
                    contextLabel={project.title}
                    hideCollapse
                    initialMessage={pendingInitialMessage ?? undefined}
                    onInitialMessageSent={handleInitialMessageSent}
                  />
                </div>
              </aside>
            )
          )}
        </div>

        {/* ─── Graph Overlay ─── */}
        {hasGraphData && (
          <GraphOverlay
            isOpen={showGraphOverlay}
            onClose={() => setShowGraphOverlay(false)}
            graphNodes={graphData.nodes}
            graphEdges={graphData.edges}
            projectId={projectId}
            focusedNodeId={focusedNodeId}
            backendClusters={graphData.clusters}
            clusterQuality={graphData.cluster_quality}
          />
        )}

        {/* ─── Scaffolding Chat Modal (for "New Case" when cases exist) ─── */}
        {showScaffolding && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowScaffolding(false)}>
            <div className="bg-white dark:bg-neutral-900 border border-neutral-200/80 dark:border-neutral-700/80 rounded-lg shadow-lg w-full max-w-2xl mx-4 h-[70vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
              <ScaffoldingChat
                projectId={projectId}
                onCaseCreated={handleCaseCreated}
                onCancel={() => setShowScaffolding(false)}
              />
            </div>
          </div>
        )}

        {/* Delete Confirm */}
        <ConfirmDialog
          isOpen={showDeleteConfirm}
          onClose={() => setShowDeleteConfirm(false)}
          onConfirm={handleDelete}
          title="Archive project"
          description={`"${project.title}" and all its cases will be archived. You can restore it later.`}
          confirmLabel="Archive"
          variant="danger"
        />
      </div>
    </ErrorBoundary>
  );
}

// ═══════════════════════════════════════════════════════════════
// Sub-components
// ═══════════════════════════════════════════════════════════════

function SectionTitle({ children, noMargin }: { children: React.ReactNode; noMargin?: boolean }) {
  return (
    <h2 className={cn(
      'text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide',
      !noMargin && 'mb-3'
    )}>
      {children}
    </h2>
  );
}

function StatPill({
  label,
  value,
  variant = 'default',
}: {
  label: string;
  value: string;
  variant?: 'default' | 'success' | 'warning';
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-neutral-500 dark:text-neutral-400">{label}</span>
      <span
        className={cn(
          'text-xs font-medium tabular-nums',
          variant === 'success' && 'text-success-600 dark:text-success-400',
          variant === 'warning' && 'text-warning-600 dark:text-warning-400',
          variant === 'default' && 'text-primary-900 dark:text-primary-100'
        )}
      >
        {value}
      </span>
    </div>
  );
}

// ─── Action Items ───

const ACTION_TYPE_CONFIG: Record<ProjectActionItem['type'], { icon: string; color: string }> = {
  resolve_inquiry: { icon: '\u26a1', color: 'text-warning-600 dark:text-warning-400' },
  untested_assumptions: { icon: '\u26a0\ufe0f', color: 'text-warning-600 dark:text-warning-400' },
  resume_investigating: { icon: '\u2192', color: 'text-accent-600 dark:text-accent-400' },
  criteria_progress: { icon: '\u2713', color: 'text-success-600 dark:text-success-400' },
  start_investigation: { icon: '\u2022', color: 'text-neutral-500 dark:text-neutral-400' },
};

function ActionItemRow({ item }: { item: ProjectActionItem }) {
  const config = ACTION_TYPE_CONFIG[item.type] ?? ACTION_TYPE_CONFIG.start_investigation;

  return (
    <Link
      href={item.href}
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border',
        'border-neutral-200/80 dark:border-neutral-800/80',
        'hover:border-accent-300 dark:hover:border-accent-700',
        'hover:bg-accent-50/30 dark:hover:bg-accent-900/10',
        'transition-all duration-150'
      )}
    >
      <span className="text-sm shrink-0">{config.icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-primary-900 dark:text-primary-50 truncate">
          {item.title}
        </p>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate">
          {item.caseTitle}
        </p>
      </div>
      <ChevronIcon className="w-4 h-4 text-neutral-400 shrink-0" />
    </Link>
  );
}

// ─── Case Card ───

const STAGE_CONFIG: Record<CaseStage, { label: string; dotColor: string }> = {
  exploring: { label: 'Exploring', dotColor: 'bg-neutral-400' },
  investigating: { label: 'Investigating', dotColor: 'bg-info-500' },
  synthesizing: { label: 'Synthesizing', dotColor: 'bg-warning-500' },
  ready: { label: 'Ready', dotColor: 'bg-success-500' },
};

function ProjectCaseCard({ caseItem }: { caseItem: ProjectCaseSummary }) {
  const stage = STAGE_CONFIG[caseItem.stage];

  return (
    <Link
      href={`/cases/${caseItem.id}`}
      className={cn(
        'block rounded-lg border p-4',
        'border-neutral-200/80 dark:border-neutral-800/80',
        'hover:border-accent-300 dark:hover:border-accent-700',
        'hover:bg-accent-50/30 dark:hover:bg-accent-900/10',
        'transition-all duration-150 group'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            {caseItem.isReady ? (
              <CheckCircleIcon className="w-4 h-4 text-success-500 shrink-0" />
            ) : (
              <div className={cn('w-2 h-2 rounded-full shrink-0', stage.dotColor)} />
            )}
            <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
              {stage.label}
            </span>
          </div>

          <h3 className="text-sm font-medium text-primary-900 dark:text-primary-100 truncate">
            {caseItem.title}
          </h3>

          <div className="flex items-center gap-3 mt-1.5 text-xs text-neutral-500 dark:text-neutral-400">
            {caseItem.inquiries.total > 0 && (
              <span className="tabular-nums">
                {caseItem.inquiries.resolved}/{caseItem.inquiries.total} inquiries
              </span>
            )}
            {caseItem.assumptions.highRiskUntested > 0 && (
              <span className="text-warning-600 dark:text-warning-400">
                {caseItem.assumptions.highRiskUntested} untested
              </span>
            )}
            <span>{formatRelativeTime(caseItem.updatedAt)}</span>
          </div>
        </div>

        <span
          className={cn(
            'text-xs font-medium px-2.5 py-1 rounded-md shrink-0',
            'text-accent-700 dark:text-accent-300',
            'bg-accent-100 dark:bg-accent-900/40',
            'opacity-0 group-hover:opacity-100 transition-opacity duration-150'
          )}
        >
          Open
        </span>
      </div>
    </Link>
  );
}

// ─── Compact Document Row ───

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500',
  processing: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
  extracting: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400',
  completed: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400',
  failed: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
};

function CompactDocRow({ doc }: { doc: UploadedDocument }) {
  const status = getDocumentPipelineStatus(doc);
  const styles = STATUS_STYLES[status] ?? STATUS_STYLES.pending;

  return (
    <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-neutral-100/50 dark:hover:bg-neutral-800/30 transition-colors">
      <FileTypeIcon fileType={doc.file_type} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-neutral-700 dark:text-neutral-300 truncate">{doc.title}</p>
      </div>
      <span className={cn('text-[10px] px-1.5 py-0.5 rounded-full uppercase shrink-0', styles)}>
        {status}
      </span>
    </div>
  );
}

function FileTypeIcon({ fileType }: { fileType: string }) {
  const type = fileType?.toLowerCase() || '';
  const config =
    type === 'pdf' ? { label: 'PDF', bg: 'bg-red-50 dark:bg-red-950/30', text: 'text-red-600 dark:text-red-400' } :
    type === 'docx' || type === 'doc' ? { label: 'DOC', bg: 'bg-blue-50 dark:bg-blue-950/30', text: 'text-blue-600 dark:text-blue-400' } :
    { label: type.toUpperCase() || 'TXT', bg: 'bg-neutral-100 dark:bg-neutral-800', text: 'text-neutral-500 dark:text-neutral-400' };

  return (
    <div className={cn('h-6 w-6 rounded flex items-center justify-center shrink-0', config.bg)}>
      <span className={cn('text-[8px] font-bold', config.text)}>{config.label}</span>
    </div>
  );
}

// ─── Utils ───

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);

  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ─── Icons ───

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

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="3 6 5 6 21 6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" strokeLinecap="round" strokeLinejoin="round" />
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

function GraphIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="6" cy="6" r="2" /><circle cx="18" cy="6" r="2" />
      <circle cx="6" cy="18" r="2" /><circle cx="18" cy="18" r="2" />
      <path d="M8 6h8M6 8v8M18 8v8M8 18h8" strokeLinecap="round" />
    </svg>
  );
}

function ChatBubbleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PanelCollapseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M15 3v18" />
      <path d="M10 15l3-3-3-3" strokeLinecap="round" strokeLinejoin="round" />
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

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="17 8 12 3 7 8" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="12" y1="3" x2="12" y2="15" strokeLinecap="round" />
    </svg>
  );
}
