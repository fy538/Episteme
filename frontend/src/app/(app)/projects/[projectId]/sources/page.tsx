/**
 * Sources Page
 *
 * Route: /projects/[projectId]/sources
 *
 * Document management view: upload, status tracking, processing progress.
 * Thin data-fetching wrapper around the existing DocumentListView component.
 */

'use client';

import { useParams } from 'next/navigation';
import { Spinner } from '@/components/ui/spinner';
import { DocumentListView } from '@/components/documents/DocumentListView';
import { useProjectDocuments } from '@/hooks/useProjectDocuments';

export default function SourcesPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  const { documents, isLoading, refetch } = useProjectDocuments(projectId);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <DocumentListView
        caseId=""
        projectId={projectId}
        documents={documents}
        onRefresh={refetch}
      />
    </div>
  );
}
