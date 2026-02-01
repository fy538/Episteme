/**
 * Case Onboarding Component
 * 
 * Shows what was auto-created when a case is first opened.
 * Guides users through next steps.
 * 
 * Uses design system: Card, Button, Badge components with semantic colors.
 */

'use client';

import * as React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useCaseOnboarding } from '@/hooks/useCaseOnboarding';
import { useCreateInquiryFromAssumption } from '@/hooks/useInquiryDashboard';

interface CaseOnboardingProps {
  caseId: string;
  onStartInquiry?: (inquiryId: string) => void;
  onDismiss?: () => void;
}

export function CaseOnboarding({ caseId, onStartInquiry, onDismiss }: CaseOnboardingProps) {
  const { data: onboarding, isLoading } = useCaseOnboarding(caseId);
  const createFromAssumption = useCreateInquiryFromAssumption();

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-sm text-neutral-600">
            <span className="inline-flex gap-1">
              <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce [animation-delay:-0.2s]" />
              <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" />
              <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce [animation-delay:0.2s]" />
            </span>
            <span>Loading onboarding...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!onboarding) {
    return null;
  }

  const { auto_created, next_steps, first_time_user, summary } = onboarding;

  return (
    <Card className="mb-6">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>✓ Case Created Successfully</CardTitle>
            <CardDescription>
              {summary.from_conversation
                ? 'We analyzed your conversation and auto-created these items'
                : 'Your case workspace is ready'}
            </CardDescription>
          </div>
          {onDismiss && (
            <Button variant="ghost" size="sm" onClick={onDismiss}>
              Dismiss
            </Button>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Auto-Created Items */}
        <div>
          <h4 className="text-sm font-medium text-neutral-700 mb-3">
            🎯 What We Created for You
          </h4>
          
          <div className="space-y-3">
            {/* Inquiries */}
            {auto_created.inquiries && auto_created.inquiries.length > 0 && (
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-100 flex items-center justify-center">
                  <span className="text-xs font-medium text-primary-700">
                    {auto_created.inquiries.length}
                  </span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-neutral-900">
                    Key Inquiries
                  </p>
                  <ul className="mt-1 space-y-1">
                    {auto_created.inquiries.slice(0, 3).map((inquiry: any) => (
                      <li key={inquiry.id} className="text-sm text-neutral-600">
                        • {inquiry.title}
                      </li>
                    ))}
                    {auto_created.inquiries.length > 3 && (
                      <li className="text-sm text-neutral-500">
                        ... and {auto_created.inquiries.length - 3} more
                      </li>
                    )}
                  </ul>
                </div>
              </div>
            )}

            {/* Assumptions */}
            {auto_created.assumptions && auto_created.assumptions.length > 0 && (
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-warning-100 flex items-center justify-center">
                  <span className="text-xs font-medium text-warning-700">
                    {auto_created.assumptions.length}
                  </span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-neutral-900">
                    Untested Assumptions
                  </p>
                  <ul className="mt-1 space-y-1">
                    {auto_created.assumptions.slice(0, 2).map((assumption: string, idx: number) => (
                      <li key={idx} className="text-sm text-neutral-600">
                        • {assumption}
                      </li>
                    ))}
                    {auto_created.assumptions.length > 2 && (
                      <li className="text-sm text-neutral-500">
                        ... and {auto_created.assumptions.length - 2} more
                      </li>
                    )}
                  </ul>
                </div>
              </div>
            )}

            {/* Brief */}
            {auto_created.brief_exists && (
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-success-100 flex items-center justify-center">
                  <span className="text-xs font-medium text-success-700">✓</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-neutral-900">
                    Case Brief
                  </p>
                  <p className="text-sm text-neutral-600">
                    Draft outline pre-filled with conversation summary
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Next Steps */}
        {next_steps && next_steps.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-neutral-700 mb-3">
              📍 Suggested Next Steps
            </h4>
            
            <div className="space-y-2">
              {next_steps.map((step, idx) => (
                <div
                  key={step.action}
                  className="flex items-center justify-between p-3 bg-neutral-50 rounded-md border border-neutral-200"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-medium text-neutral-500">
                      {idx + 1}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-neutral-900">
                        {step.title}
                      </p>
                      <p className="text-xs text-neutral-600">
                        {step.description}
                      </p>
                    </div>
                  </div>
                  
                  {step.action === 'start_first_inquiry' && step.inquiry_id && onStartInquiry && (
                    <Button
                      size="sm"
                      onClick={() => onStartInquiry(step.inquiry_id!)}
                    >
                      Start
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* First-time user tip */}
        {first_time_user && (
          <div className="p-4 bg-primary-50 border border-primary-200 rounded-md">
            <p className="text-sm text-primary-900">
              <span className="font-medium">💡 First case tip:</span> Start by investigating your inquiries. 
              Add evidence as you research, and resolve when you have enough information to make a decision.
            </p>
          </div>
        )}
      </CardContent>

      {onDismiss && (
        <CardFooter>
          <Button variant="outline" className="w-full" onClick={onDismiss}>
            Got it, let me explore
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
