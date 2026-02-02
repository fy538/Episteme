/**
 * Document Tree Navigator
 * 
 * Hierarchical view of all documents in a case:
 * - Case brief (pinned)
 * - Inquiries with their documents
 * - Project documents
 * - Uploaded documents
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import type { CaseDocument, Inquiry } from '@/lib/types/case';

interface DocumentTreeProps {
  caseId: string;
  caseBrief?: CaseDocument;
  inquiries: Inquiry[];
  inquiryDocuments: CaseDocument[];
  projectDocuments?: CaseDocument[];
  uploadedDocuments?: CaseDocument[];
  currentDocumentId?: string;
  onSelectDocument: (documentId: string) => void;
  onUploadDocument?: () => void;
}

export function DocumentTree({
  caseId,
  caseBrief,
  inquiries,
  inquiryDocuments,
  projectDocuments = [],
  uploadedDocuments = [],
  currentDocumentId,
  onSelectDocument,
  onUploadDocument,
}: DocumentTreeProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['case-brief', 'inquiries'])
  );

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  };

  const getDocumentIcon = (docType: string) => {
    switch (docType) {
      case 'case_brief':
        return '📋';
      case 'inquiry_brief':
        return '❓';
      case 'research':
        return '🔬';
      case 'debate':
        return '⚖️';
      case 'critique':
        return '🎯';
      case 'source':
        return '📄';
      case 'notes':
        return '📝';
      default:
        return '📄';
    }
  };

  const filterDocuments = (docs: CaseDocument[]) => {
    if (!searchTerm) return docs;
    return docs.filter(doc =>
      doc.title.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  const SectionHeader = ({ sectionId, title, count, icon }: {
    sectionId: string;
    title: string;
    count: number;
    icon: string;
  }) => {
    const isExpanded = expandedSections.has(sectionId);
    return (
      <button
        onClick={() => toggleSection(sectionId)}
        className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 rounded-lg transition-colors"
      >
        <svg
          className={cn(
            'w-4 h-4 transition-transform',
            isExpanded && 'rotate-90'
          )}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-lg">{icon}</span>
        <span className="flex-1 text-left">{title}</span>
        <span className="text-xs px-2 py-0.5 bg-neutral-100 rounded">
          {count}
        </span>
      </button>
    );
  };

  const DocumentItem = ({ doc }: { doc: CaseDocument }) => {
    const isCurrent = doc.id === currentDocumentId;
    return (
      <button
        onClick={() => onSelectDocument(doc.id)}
        className={cn(
          'w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-left',
          isCurrent
            ? 'bg-accent-50 text-accent-900'
            : 'hover:bg-neutral-50 text-neutral-700'
        )}
      >
        <span className="text-base">{getDocumentIcon(doc.document_type)}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{doc.title}</p>
          {doc.generated_by_ai && (
            <p className="text-xs text-neutral-500">AI-generated</p>
          )}
        </div>
        {isCurrent && (
          <svg className="w-4 h-4 text-accent-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        )}
      </button>
    );
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="p-4 border-b border-neutral-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-neutral-900">Documents</h3>
          {onUploadDocument && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onUploadDocument}
              className="text-accent-600"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </Button>
          )}
        </div>
        <Input
          type="text"
          placeholder="Search documents..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full text-sm"
        />
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {/* Case Brief (Pinned) */}
        {caseBrief && (
          <div className="mb-4">
            <DocumentItem doc={caseBrief} />
          </div>
        )}

        {/* Inquiries */}
        <div>
          <SectionHeader
            sectionId="inquiries"
            title="Inquiries"
            count={inquiries.length}
            icon="❓"
          />
          {expandedSections.has('inquiries') && (
            <div className="ml-4 mt-1 space-y-1">
              {inquiries.map(inquiry => {
                const docs = filterDocuments(
                  inquiryDocuments.filter(d => d.inquiry === inquiry.id)
                );
                const isExpanded = expandedSections.has(`inquiry-${inquiry.id}`);

                return (
                  <div key={inquiry.id}>
                    <button
                      onClick={() => toggleSection(`inquiry-${inquiry.id}`)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-neutral-50 rounded-lg transition-colors"
                    >
                      <svg
                        className={cn(
                          'w-3 h-3 transition-transform',
                          isExpanded && 'rotate-90'
                        )}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                      <span className="flex-1 text-left truncate">{inquiry.title}</span>
                      <span className="text-xs text-neutral-400">{docs.length}</span>
                    </button>
                    {isExpanded && (
                      <div className="ml-4 space-y-1">
                        {docs.map(doc => (
                          <DocumentItem key={doc.id} doc={doc} />
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Project Documents */}
        {projectDocuments.length > 0 && (
          <div>
            <SectionHeader
              sectionId="project-docs"
              title="Project Documents"
              count={projectDocuments.length}
              icon="📁"
            />
            {expandedSections.has('project-docs') && (
              <div className="ml-4 mt-1 space-y-1">
                {filterDocuments(projectDocuments).map(doc => (
                  <DocumentItem key={doc.id} doc={doc} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Uploaded Documents */}
        {uploadedDocuments.length > 0 && (
          <div>
            <SectionHeader
              sectionId="uploads"
              title="Uploaded"
              count={uploadedDocuments.length}
              icon="📤"
            />
            {expandedSections.has('uploads') && (
              <div className="ml-4 mt-1 space-y-1">
                {filterDocuments(uploadedDocuments).map(doc => (
                  <DocumentItem key={doc.id} doc={doc} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      {onUploadDocument && (
        <div className="p-4 border-t border-neutral-200 bg-neutral-50">
          <Button
            onClick={onUploadDocument}
            variant="outline"
            size="sm"
            className="w-full"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Upload Document
          </Button>
        </div>
      )}
    </div>
  );
}
