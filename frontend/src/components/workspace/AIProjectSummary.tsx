/**
 * AI Project Summary Component
 * Shows AI-generated summary of project with action buttons
 */

'use client';

import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

interface AIProjectSummaryProps {
  projectName?: string;
  onCreateCase?: () => void;
  onCreateInquiry?: () => void;
  onUploadDocument?: () => void;
  onAskAI?: () => void;
}

export function AIProjectSummary({
  projectName,
  onCreateCase,
  onCreateInquiry,
  onUploadDocument,
  onAskAI,
}: AIProjectSummaryProps) {
  return (
    <Card className="bg-gradient-to-br from-accent-50 to-primary-50 dark:from-accent-900/20 dark:to-primary-900/20 border-accent-200 dark:border-accent-800">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <svg className="w-6 h-6 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          AI Project Summary
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* AI-Generated Summary (placeholder) */}
        <div className="text-sm text-neutral-800 dark:text-neutral-200 leading-relaxed">
          <p className="mb-3">
            Your {projectName || 'project'} has 3 active cases with an average confidence of 85%. 
            I'm currently researching 2 questions in the background and have identified a gap in 
            your standing evidence that needs attention.
          </p>
          <p className="mb-3">
            Your strongest argument is the preemption analysis (92% confidence), supported by 
            strong Supreme Court precedent. However, your standing argument needs additional 
            evidence for the redressability element - currently only 1 case supports this where 
            precedent typically requires 2-3.
          </p>
          <p>
            I've validated 5 of your 7 assumptions. The remaining 2 assumptions about notice 
            requirements and statute scope are queued for research.
          </p>
        </div>

        {/* AI Suggestions */}
        <div className="p-3 rounded-lg bg-white/50 dark:bg-primary-900/30 border border-accent-200 dark:border-accent-700">
          <p className="text-sm font-medium text-accent-900 dark:text-accent-100 mb-2">
            AI Suggests:
          </p>
          <ul className="text-xs text-neutral-700 dark:text-neutral-300 space-y-1">
            <li>• Create inquiry about notice requirement scope</li>
            <li>• Upload your motion draft for gap analysis</li>
            <li>• Start conversation about damages methodology</li>
          </ul>
        </div>

        {/* Action Bar */}
        <div className="flex items-center gap-2 pt-2 border-t border-accent-200 dark:border-accent-700">
          {onCreateCase && (
            <Button size="sm" variant="default" onClick={onCreateCase}>
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Case
            </Button>
          )}
          {onCreateInquiry && (
            <Button size="sm" variant="default" onClick={onCreateInquiry}>
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Inquiry
            </Button>
          )}
          {onUploadDocument && (
            <Button size="sm" variant="outline" onClick={onUploadDocument}>
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              Upload
            </Button>
          )}
          {onAskAI && (
            <Button size="sm" variant="outline" onClick={onAskAI}>
              Ask AI About This
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
