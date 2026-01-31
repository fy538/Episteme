/**
 * Document tree - hierarchical navigation
 */

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { CaseDocument } from '@/lib/types/case';

export function DocumentTree({ 
  documents, 
  caseId 
}: { 
  documents: CaseDocument[];
  caseId: string;
}) {
  const pathname = usePathname();

  // Group by type
  const briefs = documents.filter(d => 
    d.document_type === 'case_brief' || d.document_type === 'inquiry_brief'
  );
  const research = documents.filter(d => d.document_type === 'research');
  const debates = documents.filter(d => d.document_type === 'debate');
  const critiques = documents.filter(d => d.document_type === 'critique');
  const notes = documents.filter(d => d.document_type === 'notes');

  return (
    <div className="space-y-6">
      {/* Briefs */}
      {briefs.length > 0 && (
        <DocumentSection
          title="Briefs"
          documents={briefs}
          caseId={caseId}
          currentPath={pathname}
        />
      )}

      {/* Research */}
      {research.length > 0 && (
        <DocumentSection
          title={`Research (${research.length})`}
          documents={research}
          caseId={caseId}
          currentPath={pathname}
        />
      )}

      {/* Debates */}
      {debates.length > 0 && (
        <DocumentSection
          title={`Debates (${debates.length})`}
          documents={debates}
          caseId={caseId}
          currentPath={pathname}
        />
      )}

      {/* Critiques */}
      {critiques.length > 0 && (
        <DocumentSection
          title={`Critiques (${critiques.length})`}
          documents={critiques}
          caseId={caseId}
          currentPath={pathname}
        />
      )}

      {/* Notes */}
      {notes.length > 0 && (
        <DocumentSection
          title="Notes"
          documents={notes}
          caseId={caseId}
          currentPath={pathname}
        />
      )}
    </div>
  );
}

function DocumentSection({
  title,
  documents,
  caseId,
  currentPath,
}: {
  title: string;
  documents: CaseDocument[];
  caseId: string;
  currentPath: string;
}) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2 px-2">
        {title}
      </h3>
      <div className="space-y-1">
        {documents.map(doc => (
          <DocumentLink
            key={doc.id}
            doc={doc}
            caseId={caseId}
            isActive={currentPath.includes(doc.id)}
          />
        ))}
      </div>
    </div>
  );
}

function DocumentLink({ 
  doc, 
  caseId,
  isActive 
}: { 
  doc: CaseDocument; 
  caseId: string;
  isActive: boolean;
}) {
  return (
    <Link
      href={`/cases/${caseId}/documents/${doc.id}`}
      className={`block px-2 py-2 text-sm rounded transition-colors ${
        isActive 
          ? 'bg-blue-50 border border-blue-200' 
          : 'hover:bg-gray-100 border border-transparent'
      }`}
    >
      <div className="font-medium text-gray-900 truncate">
        {doc.title}
      </div>
      <div className="flex items-center gap-2 mt-1">
        {doc.edit_friction === 'low' && (
          <span className="text-xs text-green-600">• Editable</span>
        )}
        {doc.generated_by_ai && (
          <span className="text-xs text-purple-600">• AI</span>
        )}
        {doc.times_cited > 0 && (
          <span className="text-xs text-gray-500">
            {doc.times_cited} citations
          </span>
        )}
      </div>
    </Link>
  );
}
