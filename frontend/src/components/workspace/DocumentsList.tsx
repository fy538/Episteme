/**
 * Documents List Component
 * Shows all documents organized by case
 */

'use client';

import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { Case } from '@/lib/types/case';

interface Document {
  id: string;
  title: string;
  document_type: string;
  case?: string;
  created_at: string;
}

interface DocumentsListProps {
  cases: Case[];
  onUploadDocument?: () => void;
}

export function DocumentsList({
  cases,
  onUploadDocument,
}: DocumentsListProps) {
  // Mock documents for now - will be loaded from API later
  const mockDocuments: Document[] = [
    { id: '1', title: 'Main Brief', document_type: 'case_brief', case: cases[0]?.id, created_at: new Date().toISOString() },
    { id: '2', title: 'Standing Doctrine Research', document_type: 'research', case: cases[0]?.id, created_at: new Date().toISOString() },
    { id: '3', title: 'FDA Statute Text', document_type: 'source', case: cases[0]?.id, created_at: new Date().toISOString() },
  ];

  const documentsByCase = cases.map(c => ({
    case: c,
    documents: mockDocuments.filter(d => d.case === c.id),
  }));

  const unlinkedDocs = mockDocuments.filter(d => !d.case);

  const getDocTypeColor = (type: string) => {
    switch (type) {
      case 'case_brief': return 'default';
      case 'research': return 'success';
      case 'source': return 'warning';
      case 'notes': return 'neutral';
      default: return 'neutral';
    }
  };

  const formatDocType = (type: string) => {
    return type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-primary-900 dark:text-primary-50">
          All Documents ({mockDocuments.length})
        </h3>
        {onUploadDocument && (
          <Button onClick={onUploadDocument}>
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Upload Document
          </Button>
        )}
      </div>

      {mockDocuments.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12 text-neutral-500 dark:text-neutral-400">
            <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            <p className="mb-4">No documents in this project</p>
            {onUploadDocument && (
              <Button onClick={onUploadDocument}>
                Upload First Document
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Documents by Case */}
          {documentsByCase.map(({ case: caseData, documents }) => (
            documents.length > 0 && (
              <Card key={caseData.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      <svg className="w-5 h-5 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                      {caseData.title}
                      <Badge variant="neutral" className="text-xs ml-2">
                        {documents.length} docs
                      </Badge>
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1.5">
                    {documents.map((doc) => (
                      <Link
                        key={doc.id}
                        href={`/cases/${doc.case}/documents/${doc.id}`}
                        className="block p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 hover:border-accent-500 dark:hover:border-accent-600 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <svg className="w-5 h-5 text-neutral-600 dark:text-neutral-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                          </svg>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-sm text-primary-900 dark:text-primary-50 truncate">
                              {doc.title}
                            </h4>
                            <Badge variant={getDocTypeColor(doc.document_type)} className="mt-1 text-xs">
                              {formatDocType(doc.document_type)}
                            </Badge>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )
          ))}

          {/* Unlinked Documents */}
          {unlinkedDocs.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <svg className="w-5 h-5 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  Unlinked Documents
                  <Badge variant="neutral" className="text-xs ml-2">
                    {unlinkedDocs.length}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1.5">
                  {unlinkedDocs.map((doc) => (
                    <div
                      key={doc.id}
                      className="p-3 rounded-lg border border-neutral-200 dark:border-neutral-800"
                    >
                      <div className="flex items-center gap-3">
                        <svg className="w-5 h-5 text-neutral-600 dark:text-neutral-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                        </svg>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-sm text-primary-900 dark:text-primary-50 truncate">
                            {doc.title}
                          </h4>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant={getDocTypeColor(doc.document_type)} className="text-xs">
                              {formatDocType(doc.document_type)}
                            </Badge>
                            <Button size="sm" variant="outline">
                              Link to Case
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
