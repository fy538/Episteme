/**
 * Expanded Case Card
 * Shows case with nested inquiries and conversations
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { Case, Inquiry } from '@/lib/types/case';
import type { ChatThread } from '@/lib/types/chat';
import { cn } from '@/lib/utils';

interface CaseCardExpandedProps {
  case: Case;
  inquiries: Inquiry[];
  threads: ChatThread[];
  onOpenCase: () => void;
  onCreateInquiry?: () => void;
  onStartChat?: () => void;
  onUploadDoc?: () => void;
}

export function CaseCardExpanded({
  case: caseData,
  inquiries,
  threads,
  onOpenCase,
  onCreateInquiry,
  onStartChat,
  onUploadDoc,
}: CaseCardExpandedProps) {
  const [showInquiries, setShowInquiries] = useState(false);
  const [showThreads, setShowThreads] = useState(false);

  const confidenceLevel = caseData.user_confidence != null ? caseData.user_confidence : 0;
  const isHighConfidence = confidenceLevel >= 70;
  const isMediumConfidence = confidenceLevel >= 40 && confidenceLevel < 70;

  return (
    <Card className="hover:border-accent-500 dark:hover:border-accent-600 transition-colors">
      <CardContent className="pt-6 space-y-4">
        {/* Case Header */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-lg text-primary-900 dark:text-primary-50">
              {caseData.title}
            </h3>
            <Badge variant={caseData.status === 'active' ? 'success' : 'neutral'}>
              {caseData.status}
            </Badge>
          </div>

          {/* Confidence Bar */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-2 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden">
              <div 
                className={cn(
                  'h-full transition-all',
                  isHighConfidence ? 'bg-success-600' :
                  isMediumConfidence ? 'bg-warning-600' :
                  'bg-error-600'
                )}
                style={{ width: `${confidenceLevel}%` }}
              />
            </div>
            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 w-12">
              {confidenceLevel}%
            </span>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="flex items-center gap-4 text-xs text-neutral-600 dark:text-neutral-400">
          <div className="flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{inquiries.length} inquiries</span>
          </div>
          <div className="flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <span>{threads.length} conversations</span>
          </div>
        </div>

        {/* Expandable Inquiries */}
        {inquiries.length > 0 && (
          <div>
            <button
              onClick={() => setShowInquiries(!showInquiries)}
              className="flex items-center gap-2 text-sm font-medium text-primary-900 dark:text-primary-50 hover:text-accent-600 transition-colors"
            >
              <svg 
                className={cn('w-4 h-4 transition-transform', showInquiries && 'rotate-90')}
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              Inquiries ({inquiries.length})
            </button>
            
            {showInquiries && (
              <div className="mt-2 pl-6 space-y-1.5">
                {inquiries.map((inq) => (
                  <div
                    key={inq.id}
                    className="p-2 rounded border border-neutral-200 dark:border-neutral-700 text-sm"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="flex-1 truncate text-primary-900 dark:text-primary-50">
                        {inq.title}
                      </span>
                      <Badge 
                        variant={inq.status === 'resolved' ? 'success' : inq.status === 'investigating' ? 'default' : 'warning'}
                        className="text-xs shrink-0"
                      >
                        {inq.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Expandable Conversations */}
        {threads.length > 0 && (
          <div>
            <button
              onClick={() => setShowThreads(!showThreads)}
              className="flex items-center gap-2 text-sm font-medium text-primary-900 dark:text-primary-50 hover:text-accent-600 transition-colors"
            >
              <svg 
                className={cn('w-4 h-4 transition-transform', showThreads && 'rotate-90')}
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              Conversations ({threads.length})
            </button>
            
            {showThreads && (
              <div className="mt-2 pl-6 space-y-1.5">
                {threads.map((thread) => (
                  <Link
                    key={thread.id}
                    href={`/?thread=${thread.id}`}
                    className="block p-2 rounded border border-neutral-200 dark:border-neutral-700 hover:border-accent-500 transition-colors text-sm"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="flex-1 truncate text-primary-900 dark:text-primary-50">
                        {thread.title}
                      </span>
                      <span className="text-xs text-neutral-600 dark:text-neutral-400 shrink-0">
                        {thread.message_count || 0} msgs
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2 border-t border-neutral-200 dark:border-neutral-700">
          <Button size="sm" variant="default" onClick={onOpenCase}>
            Open Case
          </Button>
          {onStartChat && (
            <Button size="sm" variant="outline" onClick={onStartChat}>
              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              Chat
            </Button>
          )}
          {onCreateInquiry && (
            <Button size="sm" variant="outline" onClick={onCreateInquiry}>
              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Inquiry
            </Button>
          )}
          {onUploadDoc && (
            <Button size="sm" variant="outline" onClick={onUploadDoc}>
              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              Upload
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
