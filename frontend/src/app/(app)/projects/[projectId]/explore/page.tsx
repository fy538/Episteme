/**
 * Explore Page
 *
 * Route: /projects/[projectId]/explore
 *
 * The project's thinking space: orientation analysis (editorial lens) on top,
 * thematic landscape (themes → topics → chunks) below. An optional full-viewport
 * knowledge graph overlay is accessible via a header button.
 *
 * All components and hooks already exist — this page composes them together.
 */

'use client';

import { useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { OrientationView } from '@/components/workspace/project/OrientationView';
import { ProjectLandscapeView } from '@/components/workspace/project/ProjectLandscapeView';
import { GraphOverlay } from '@/components/graph/GraphOverlay';
import { Spinner } from '@/components/ui/spinner';
import { Button } from '@/components/ui/button';
import { useProjectHierarchy } from '@/hooks/useProjectHierarchy';
import { useProjectOrientation } from '@/hooks/useProjectOrientation';
import { useProjectInsights } from '@/hooks/useProjectInsights';
import { useProjectGraph } from '@/hooks/useProjectGraph';
import { chatAPI } from '@/lib/api/chat';
import { graphAPI } from '@/lib/api/graph';

export default function ExplorePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  // ─── Data hooks ───
  const {
    hierarchy,
    isLoading: isHierarchyLoading,
    isBuilding,
    isFailed,
    rebuild,
    isRebuilding,
  } = useProjectHierarchy(projectId);

  const {
    orientation,
    isLoading: isOrientationLoading,
    isGenerating,
    regenerate,
    generateAngle,
    generatingAngleId,
    researchGap,
  } = useProjectOrientation(projectId);

  const {
    insights,
    acknowledge,
    dismiss,
    updatingInsightId,
  } = useProjectInsights(projectId);

  const { data: graphData } = useProjectGraph(projectId);

  // ─── Graph overlay ───
  const [showGraph, setShowGraph] = useState(false);

  // ─── Callbacks ───

  /** Discuss a finding → create chat thread, link insight, navigate */
  const handleDiscuss = useCallback(
    async (insightId: string, title: string, body: string) => {
      try {
        const thread = await chatAPI.createThread(projectId);
        // Link the insight to the thread (silently catch errors)
        try {
          await graphAPI.linkInsightThread(projectId, insightId, thread.id);
        } catch {
          // Non-critical — chat still works without the link
        }
        if (typeof window !== 'undefined') {
          sessionStorage.setItem(
            'episteme_initial_message',
            JSON.stringify({
              threadId: thread.id,
              content: `Let's discuss: ${title}\n\n${body}`,
            })
          );
        }
        router.push(`/projects/${projectId}/chat?thread=${thread.id}`);
      } catch (err) {
        console.error('Failed to create discussion thread:', err);
      }
    },
    [projectId, router]
  );

  /** Open case → navigate to cases page */
  const handleOpenCase = useCallback(() => {
    router.push(`/projects/${projectId}/cases`);
  }, [projectId, router]);

  // ─── Loading state (initial fetch) ───
  const isInitialLoading =
    isHierarchyLoading && !hierarchy && isOrientationLoading && !orientation;

  if (isInitialLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  // ─── Empty state (no data at all) ───
  const hasNoData =
    !hierarchy && !orientation && !isBuilding && !isGenerating;

  if (hasNoData) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center mx-auto">
            <CompassIcon className="w-6 h-6 text-neutral-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Nothing to explore yet
            </p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1 max-w-xs mx-auto">
              Upload documents to build your knowledge base, then explore themes and insights here.
            </p>
          </div>
          <Link
            href={`/projects/${projectId}/sources`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-accent-600 hover:text-accent-700 border border-accent-200 dark:border-accent-800 rounded-lg hover:bg-accent-50 dark:hover:bg-accent-950/30 transition-colors"
          >
            Go to Sources
          </Link>
        </div>
      </div>
    );
  }

  // ─── Main content ───
  const hasGraphNodes = graphData && graphData.nodes.length > 0;

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            Explore
          </h1>
          {hasGraphNodes && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowGraph(true)}
              className="inline-flex items-center gap-1.5 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
            >
              <GraphIcon className="w-3.5 h-3.5" />
              View graph
            </Button>
          )}
        </div>

        {/* Orientation section (editorial analysis) */}
        <OrientationView
          orientation={orientation}
          isGenerating={isGenerating}
          hierarchy={hierarchy}
          onDiscuss={handleDiscuss}
          onResearch={researchGap}
          onGenerateAngle={generateAngle}
          onRegenerateOrientation={() => regenerate()}
          generatingAngleId={generatingAngleId}
        />

        {/* Landscape section (themes → topics → chunks) */}
        {(hierarchy || isBuilding) && (
          <ProjectLandscapeView
            hierarchy={hierarchy!}
            insights={insights}
            isBuilding={isBuilding}
            isFailed={isFailed}
            onOpenCase={handleOpenCase}
            onAcknowledgeInsight={acknowledge}
            onDismissInsight={dismiss}
            onRebuild={() => rebuild()}
            isRebuilding={isRebuilding}
            updatingInsightId={updatingInsightId}
          />
        )}
      </div>

      {/* Graph overlay (full-viewport, on demand) */}
      {graphData && (
        <GraphOverlay
          isOpen={showGraph}
          onClose={() => setShowGraph(false)}
          graphNodes={graphData.nodes}
          graphEdges={graphData.edges}
          projectId={projectId}
          focusedNodeId={null}
          backendClusters={graphData.clusters}
          clusterQuality={graphData.cluster_quality}
          totalNodeCount={graphData.total_node_count}
          truncated={graphData.truncated}
        />
      )}
    </div>
  );
}

// ─── Icons ──────────────────────────────────────────

function CompassIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="12" cy="12" r="10" />
      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function GraphIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="6" cy="6" r="2" />
      <circle cx="18" cy="6" r="2" />
      <circle cx="12" cy="18" r="2" />
      <path d="M7.5 7.5l3 7.5M16.5 7.5l-3 7.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
