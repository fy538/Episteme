/**
 * Assumption Highlighter Component
 * 
 * Visually highlights assumptions from case brief with quick actions.
 * Shows validation status and related inquiries.
 * 
 * Uses design system: Warning colors for untested, success for validated.
 */

'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useCreateInquiryFromAssumption } from '@/hooks/useInquiryDashboard';

interface Assumption {
  text: string;
  has_inquiry: boolean;
  inquiry_id: string | null;
  inquiry_title: string | null;
  inquiry_status: string | null;
  related_signals_count: number;
  validated: boolean;
}

interface AssumptionHighlighterProps {
  assumptions: Assumption[];
  caseId: string;
  onInquiryCreated?: (inquiryId: string) => void;
  onViewInquiry?: (inquiryId: string) => void;
}

export function AssumptionHighlighter({
  assumptions,
  caseId,
  onInquiryCreated,
  onViewInquiry,
}: AssumptionHighlighterProps) {
  const createFromAssumption = useCreateInquiryFromAssumption();
  const [creatingFor, setCreatingFor] = React.useState<string | null>(null);

  if (!assumptions || assumptions.length === 0) {
    return null;
  }

  const handleCreateInquiry = async (assumptionText: string) => {
    setCreatingFor(assumptionText);
    
    try {
      const inquiry = await createFromAssumption.mutateAsync({
        caseId,
        assumptionText,
        autoGenerateTitle: true,
      });
      
      if (onInquiryCreated) {
        onInquiryCreated(inquiry.id);
      }
    } catch (error) {
      console.error('Failed to create inquiry:', error);
    } finally {
      setCreatingFor(null);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-neutral-700">
          Detected Assumptions
        </h4>
        <Badge variant="neutral">
          {assumptions.filter(a => a.validated).length} / {assumptions.length} Validated
        </Badge>
      </div>

      <div className="space-y-2">
        {assumptions.map((assumption, idx) => {
          const isValidated = assumption.validated;
          const hasInquiry = assumption.has_inquiry;
          const isCreating = creatingFor === assumption.text;

          return (
            <div
              key={idx}
              className={cn(
                'p-3 rounded-md border-l-4',
                isValidated
                  ? 'bg-success-50 border-success-500'
                  : hasInquiry
                  ? 'bg-primary-50 border-accent-500'
                  : 'bg-warning-50 border-warning-500'
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    {isValidated ? (
                      <Badge variant="success" className="text-xs">
                        ✓ Validated
                      </Badge>
                    ) : hasInquiry ? (
                      <Badge variant="default" className="text-xs">
                        Investigating
                      </Badge>
                    ) : (
                      <Badge variant="warning" className="text-xs">
                        ⚠️ Untested
                      </Badge>
                    )}
                    
                    {assumption.related_signals_count > 0 && (
                      <span className="text-xs text-neutral-500">
                        {assumption.related_signals_count} signal{assumption.related_signals_count > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                  
                  <p className="text-sm text-neutral-900">
                    {assumption.text}
                  </p>
                  
                  {hasInquiry && assumption.inquiry_title && (
                    <p className="text-xs text-neutral-600 mt-1">
                      → Inquiry: {assumption.inquiry_title}
                    </p>
                  )}
                </div>

                <div className="flex-shrink-0">
                  {!hasInquiry && !isCreating && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleCreateInquiry(assumption.text)}
                    >
                      Investigate →
                    </Button>
                  )}
                  
                  {isCreating && (
                    <div className="flex items-center gap-1 text-xs text-neutral-500">
                      <span className="inline-flex gap-1">
                        <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce [animation-delay:-0.2s]" />
                        <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" />
                        <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                      </span>
                    </div>
                  )}
                  
                  {hasInquiry && assumption.inquiry_id && onViewInquiry && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onViewInquiry(assumption.inquiry_id!)}
                    >
                      View →
                    </Button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Help text */}
      <p className="text-xs text-neutral-500">
        Assumptions were detected from your conversation. Click "Investigate" to create an inquiry and validate them with evidence.
      </p>
    </div>
  );
}

// Helper function (matches design system pattern)
function cn(...inputs: (string | boolean | undefined | null)[]) {
  return inputs.filter(Boolean).join(' ');
}
