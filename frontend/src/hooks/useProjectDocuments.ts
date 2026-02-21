/**
 * useProjectDocuments — fetches project-scoped documents with auto-polling.
 *
 * Polls every 5 seconds while any document is still processing (chunking,
 * extracting, or integrating). Stops polling when all documents are in a
 * terminal state (completed or failed).
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { documentsAPI } from '@/lib/api/documents';
import type { UploadedDocument } from '@/lib/types/document';

export function useProjectDocuments(projectId: string | undefined) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['project-documents', projectId],
    queryFn: () => documentsAPI.listUploadedDocuments({ projectId: projectId! }),
    enabled: !!projectId,
    staleTime: 15_000,
    refetchInterval: (q) => {
      const docs = q.state.data;
      if (!docs) return false;
      const hasProcessing = docs.some(
        (d: UploadedDocument) =>
          d.processing_status === 'pending' ||
          d.processing_status === 'chunking' ||
          d.extraction_status === 'pending' ||
          d.extraction_status === 'extracting' ||
          d.extraction_status === 'integrating'
      );
      return hasProcessing ? 5_000 : false;
    },
  });

  return {
    documents: query.data ?? [],
    isLoading: query.isLoading,
    refetch: () =>
      queryClient.invalidateQueries({ queryKey: ['project-documents', projectId] }),
  };
}
