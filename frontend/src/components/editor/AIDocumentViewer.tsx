/**
 * AI Document Viewer - read-only view for AI-generated documents
 */

'use client';

import ReactMarkdown from 'react-markdown';
import type { CaseDocument } from '@/lib/types/case';

export function AIDocumentViewer({ document }: { document: CaseDocument }) {
  return (
    <div className="bg-white h-screen overflow-y-auto">
      {/* Header indicating read-only */}
      <div className="border-b border-neutral-200 px-6 py-4 bg-neutral-50 sticky top-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-neutral-900">
              {document.title}
            </h1>
            <p className="text-sm text-neutral-600 mt-1">
              AI-generated • Read-only (annotate to add your thoughts)
            </p>
          </div>
          <div className="flex gap-2">
            {document.agent_type && (
              <span className="text-xs px-2 py-1 bg-purple-100 text-purple-800 rounded font-medium">
                {document.agent_type}
              </span>
            )}
            {document.times_cited > 0 && (
              <span className="text-xs px-2 py-1 bg-accent-100 text-accent-800 rounded font-medium">
                Cited {document.times_cited}x
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-8 max-w-4xl mx-auto">
        <article className="prose prose-lg max-w-none prose-headings:text-neutral-900 prose-p:text-neutral-700">
          <ReactMarkdown>{document.content_markdown}</ReactMarkdown>
        </article>

        {/* Extracted structure preview (for debugging/transparency) */}
        {Object.keys(document.ai_structure).length > 0 && (
          <div className="mt-12 p-4 bg-neutral-50 rounded-lg border border-neutral-200">
            <details>
              <summary className="text-sm font-semibold text-neutral-700 cursor-pointer">
                Extracted Structure (click to expand)
              </summary>
              <pre className="mt-3 text-xs text-neutral-600 overflow-x-auto">
                {JSON.stringify(document.ai_structure, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>

      {/* Future: Annotation UI will go here */}
    </div>
  );
}
