/**
 * Inquiry List Component
 * Shows all inquiries grouped by status
 */

'use client';

import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import type { Inquiry } from '@/lib/types/case';
import type { Case } from '@/lib/types/case';

interface InquiryListProps {
  inquiries: Inquiry[];
  cases: Case[];
  onCreateInquiry?: () => void;
}

export function InquiryList({
  inquiries,
  cases,
  onCreateInquiry,
}: InquiryListProps) {
  const openInquiries = inquiries.filter(i => i.status === 'open');
  const investigatingInquiries = inquiries.filter(i => i.status === 'investigating');
  const resolvedInquiries = inquiries.filter(i => i.status === 'resolved');

  const getCaseName = (caseId: string) => {
    const foundCase = cases.find(c => c.id === caseId);
    return foundCase?.title || 'Unknown Case';
  };

  const renderInquiryCard = (inquiry: Inquiry) => (
    <Card key={inquiry.id} className="hover:border-accent-500 dark:hover:border-accent-600 transition-colors">
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-sm text-primary-900 dark:text-primary-50 mb-1">
              {inquiry.title}
            </h4>
            <div className="flex items-center gap-2 mb-2">
              <Badge 
                variant={
                  inquiry.status === 'resolved' ? 'success' : 
                  inquiry.status === 'investigating' ? 'default' : 
                  'warning'
                }
                className="text-xs"
              >
                {inquiry.status}
              </Badge>
              {inquiry.case && (
                <Link 
                  href={`/cases/${inquiry.case}`}
                  className="text-xs text-accent-600 hover:text-accent-700 hover:underline"
                >
                  {getCaseName(inquiry.case)}
                </Link>
              )}
            </div>
            {inquiry.status === 'resolved' && inquiry.conclusion_confidence != null && (
              <p className="text-xs text-success-700 dark:text-success-400">
                Resolved with {Math.round(inquiry.conclusion_confidence * 100)}% confidence
              </p>
            )}
          </div>
          
          {inquiry.status === 'investigating' && (
            <Spinner size="sm" className="text-accent-600 shrink-0" />
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700">
          {inquiry.status === 'open' && (
            <Button size="sm" variant="default">
              Start Investigation
            </Button>
          )}
          {inquiry.status === 'investigating' && (
            <Button size="sm" variant="default">
              View Progress
            </Button>
          )}
          {inquiry.status === 'resolved' && (
            <Button size="sm" variant="default">
              View Findings
            </Button>
          )}
          <Button size="sm" variant="outline">
            Chat About This
          </Button>
          {!inquiry.case && (
            <Button size="sm" variant="outline">
              Link to Case
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-primary-900 dark:text-primary-50">
          All Inquiries ({inquiries.length})
        </h3>
        {onCreateInquiry && (
          <Button onClick={onCreateInquiry}>
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Inquiry
          </Button>
        )}
      </div>

      {inquiries.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12 text-neutral-500 dark:text-neutral-400">
            <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="mb-4">No inquiries in this project</p>
            {onCreateInquiry && (
              <Button onClick={onCreateInquiry}>
                Create First Inquiry
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Open Inquiries */}
          {openInquiries.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-error-700 dark:text-error-400 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-error-600 rounded-full"></span>
                Open ({openInquiries.length})
              </h4>
              <div className="space-y-2">
                {openInquiries.map(renderInquiryCard)}
              </div>
            </div>
          )}

          {/* Investigating */}
          {investigatingInquiries.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-accent-700 dark:text-accent-400 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-accent-600 rounded-full animate-pulse"></span>
                Investigating ({investigatingInquiries.length})
              </h4>
              <div className="space-y-2">
                {investigatingInquiries.map(renderInquiryCard)}
              </div>
            </div>
          )}

          {/* Resolved */}
          {resolvedInquiries.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-success-700 dark:text-success-400 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-success-600 rounded-full"></span>
                Resolved ({resolvedInquiries.length})
              </h4>
              <div className="space-y-2">
                {resolvedInquiries.map(renderInquiryCard)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
