/**
 * Uploaded source document (projects.Document model).
 *
 * Distinct from WorkingDocument which represents generated outputs (briefs, research).
 * This represents uploaded PDFs, DOCX files, and pasted text that feed the
 * chunking → embedding → graph extraction pipeline.
 */

export interface UploadedDocument {
  id: string;
  title: string;
  source_type: 'upload' | 'url' | 'text';
  file_type: string;
  file_size: number | null;
  processing_status: 'pending' | 'chunking' | 'indexed' | 'failed';
  extraction_status: 'pending' | 'extracting' | 'extracted' | 'integrating' | 'completed' | 'integration_failed' | 'failed';
  extraction_error: string;
  chunk_count: number;
  indexed_at: string | null;
  project: string;
  case: string | null;
  scope: 'project' | 'case';
  created_at: string;
  updated_at: string;
}

/** Combined status for display — considers both processing and extraction */
export type DocumentPipelineStatus =
  | 'pending'
  | 'processing'
  | 'extracting'
  | 'completed'
  | 'failed';

export function getDocumentPipelineStatus(doc: UploadedDocument): DocumentPipelineStatus {
  if (doc.processing_status === 'failed' || doc.extraction_status === 'failed') return 'failed';
  // 'extracted' = Phase 1 done (structure visible), 'completed' = Phase 2 done (integrated)
  // Both count as "completed" from the user's perspective
  if (doc.extraction_status === 'extracted' || doc.extraction_status === 'completed') return 'completed';
  // integration_failed is non-critical — structure is still available
  if (doc.extraction_status === 'integration_failed') return 'completed';
  if (doc.extraction_status === 'extracting' || doc.extraction_status === 'integrating') return 'extracting';
  if (doc.processing_status === 'chunking' || doc.processing_status === 'indexed') return 'processing';
  return 'pending';
}
