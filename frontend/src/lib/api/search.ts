/**
 * Unified Search API Client
 *
 * Provides semantic search across all content types:
 * - Inquiries
 * - Cases
 * - Documents
 */

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export type SearchResultType = 'inquiry' | 'case' | 'document';

export interface SearchResult {
  id: string;
  type: SearchResultType;
  title: string;
  subtitle: string;
  score: number;
  case_id: string | null;
  case_title: string | null;
  metadata: {
    confidence?: number;
    has_evidence?: boolean;
    status?: string;
    stakes?: string;
    document_type?: string;
    chunk_preview?: string;
    priority?: string;
    document_id?: string;
  };
}

export interface UnifiedSearchResponse {
  query: string;
  in_context: SearchResult[];
  other: SearchResult[];
  recent: SearchResult[];
  total_count: number;
}

export interface SearchContext {
  case_id?: string;
  project_id?: string;
}

export interface SearchOptions {
  types?: SearchResultType[];
  top_k?: number;
  threshold?: number;
}

/**
 * Perform unified semantic search
 */
export async function unifiedSearch(
  query: string,
  context?: SearchContext,
  options?: SearchOptions
): Promise<UnifiedSearchResponse> {
  const response = await fetch(`${BACKEND_URL}/api/search/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      query,
      context: context || {},
      types: options?.types,
      top_k: options?.top_k || 20,
      threshold: options?.threshold || 0.4,
    }),
  });

  if (!response.ok) {
    throw new Error('Search failed');
  }

  return response.json();
}

/**
 * Get recent items (for empty search state)
 */
export async function getRecentItems(context?: SearchContext): Promise<UnifiedSearchResponse> {
  return unifiedSearch('', context);
}

/**
 * Get icon for result type
 */
export function getResultTypeIcon(type: SearchResultType): string {
  switch (type) {
    case 'inquiry':
      return '🔬';
    case 'case':
      return '📁';
    case 'document':
      return '📄';
    default:
      return '📌';
  }
}

/**
 * Get label for result type
 */
export function getResultTypeLabel(type: SearchResultType): string {
  switch (type) {
    case 'inquiry':
      return 'Inquiry';
    case 'case':
      return 'Case';
    case 'document':
      return 'Document';
    default:
      return type;
  }
}

/**
 * Get navigation path for a search result
 */
export function getResultPath(result: SearchResult): string {
  switch (result.type) {
    case 'case':
      return `/cases/${result.id}`;
    case 'inquiry':
      return result.case_id
        ? `/cases/${result.case_id}?view=inquiry&inquiry=${result.id}`
        : `/inquiries`;
    case 'document':
      return result.case_id
        ? `/cases/${result.case_id}/documents/${result.id}`
        : `/`;
    default:
      return '/';
  }
}
