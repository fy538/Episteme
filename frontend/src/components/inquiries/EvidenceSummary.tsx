/**
 * Evidence Summary Component
 * 
 * Shows aggregated evidence with confidence calculation.
 * Helps users know if they're ready to resolve an inquiry.
 * 
 * Uses design system: Success/error colors, Cards, Badges.
 */

'use client';

import * as React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useEvidenceSummary, type EvidenceItem } from '@/hooks/useInquiryDashboard';

interface EvidenceSummaryProps {
  inquiryId: string;
  onResolve?: () => void;
}

export function EvidenceSummary({ inquiryId, onResolve }: EvidenceSummaryProps) {
  const { data: evidenceSummary, isLoading } = useEvidenceSummary(inquiryId);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <LoadingDots />
        </CardContent>
      </Card>
    );
  }

  if (!evidenceSummary) {
    return null;
  }

  const { supporting, contradicting, neutral, summary } = evidenceSummary;
  const { aggregate_confidence, strength, ready_to_resolve, total_evidence } = summary;

  // Determine badge variant based on strength
  const strengthBadgeVariant = 
    strength === 'strong' ? 'success' :
    strength === 'moderate' ? 'warning' :
    'error';

  return (
    <div className="space-y-4">
      {/* Confidence Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Evidence Summary</CardTitle>
              <CardDescription>
                {total_evidence} piece{total_evidence !== 1 ? 's' : ''} of evidence collected
              </CardDescription>
            </div>
            <Badge variant={strengthBadgeVariant} className="text-sm">
              {(aggregate_confidence * 100).toFixed(0)}% Confidence
            </Badge>
          </div>
        </CardHeader>
        
        <CardContent>
          {/* Confidence Breakdown */}
          <div className="space-y-4">
            {/* Visual confidence bar */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-neutral-700">
                  Aggregate Confidence
                </span>
                <span className="text-xs text-neutral-500">
                  {strength.charAt(0).toUpperCase() + strength.slice(1)}
                </span>
              </div>
              <div className="h-2 bg-neutral-200 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all ${
                    strength === 'strong' ? 'bg-success-600' :
                    strength === 'moderate' ? 'bg-warning-600' :
                    'bg-error-600'
                  }`}
                  style={{ width: `${aggregate_confidence * 100}%` }}
                />
              </div>
            </div>

            {/* Evidence counts */}
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center p-3 bg-success-50 rounded-md border border-success-200">
                <p className="text-lg font-semibold text-success-900">
                  {summary.supporting_count}
                </p>
                <p className="text-xs text-success-700">Supporting</p>
              </div>
              
              <div className="text-center p-3 bg-error-50 rounded-md border border-error-200">
                <p className="text-lg font-semibold text-error-900">
                  {summary.contradicting_count}
                </p>
                <p className="text-xs text-error-700">Contradicting</p>
              </div>
              
              <div className="text-center p-3 bg-neutral-50 rounded-md border border-neutral-200">
                <p className="text-lg font-semibold text-neutral-900">
                  {summary.neutral_count}
                </p>
                <p className="text-xs text-neutral-700">Neutral</p>
              </div>
            </div>

            {/* Average credibility */}
            {summary.avg_credibility > 0 && (
              <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-md">
                <span className="text-sm text-neutral-700">
                  Average Credibility Rating
                </span>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <span
                      key={star}
                      className={
                        star <= summary.avg_credibility
                          ? 'text-warning-500'
                          : 'text-neutral-300'
                      }
                    >
                      ★
                    </span>
                  ))}
                  <span className="ml-1 text-sm text-neutral-600">
                    {summary.avg_credibility.toFixed(1)}
                  </span>
                </div>
              </div>
            )}

            {/* Recommended conclusion */}
            {summary.recommended_conclusion && (
              <div className="p-3 bg-primary-50 border border-primary-200 rounded-md">
                <p className="text-xs font-medium text-primary-900 mb-1">
                  💡 Recommended Conclusion
                </p>
                <p className="text-sm text-primary-800">
                  {summary.recommended_conclusion}
                </p>
              </div>
            )}
          </div>
        </CardContent>

        {/* Ready to resolve indicator */}
        {ready_to_resolve && onResolve && (
          <CardFooter className="bg-success-50 border-t border-success-200">
            <div className="flex items-center justify-between w-full">
              <p className="text-sm font-medium text-success-900">
                ✓ Ready to resolve with high confidence
              </p>
              <Button variant="success" onClick={onResolve}>
                Resolve Inquiry
              </Button>
            </div>
          </CardFooter>
        )}

        {/* Not ready warning */}
        {!ready_to_resolve && total_evidence > 0 && (
          <CardFooter className="border-t border-neutral-200">
            <p className="text-xs text-neutral-600">
              {total_evidence < 2
                ? 'Add at least 2 pieces of evidence before resolving'
                : summary.avg_credibility < 3.0
                ? 'Evidence credibility is low. Consider adding higher-quality sources'
                : aggregate_confidence <= 0.6
                ? 'Confidence is moderate. Consider gathering more supporting evidence'
                : 'Continue gathering evidence'}
            </p>
          </CardFooter>
        )}
      </Card>

      {/* Evidence Lists */}
      {total_evidence > 0 && (
        <div className="space-y-4">
          {supporting.length > 0 && (
            <EvidenceList
              title="Supporting Evidence"
              evidence={supporting}
              variant="success"
            />
          )}
          
          {contradicting.length > 0 && (
            <EvidenceList
              title="Contradicting Evidence"
              evidence={contradicting}
              variant="error"
            />
          )}
          
          {neutral.length > 0 && (
            <EvidenceList
              title="Neutral Evidence"
              evidence={neutral}
              variant="neutral"
            />
          )}
        </div>
      )}
    </div>
  );
}

function EvidenceList({ title, evidence, variant }: {
  title: string;
  evidence: EvidenceItem[];
  variant: 'success' | 'error' | 'neutral';
}) {
  const headerClass =
    variant === 'success' ? 'text-success-900' :
    variant === 'error' ? 'text-error-900' :
    'text-neutral-900';

  return (
    <div>
      <h4 className={`text-sm font-medium mb-2 ${headerClass}`}>
        {title} ({evidence.length})
      </h4>
      <div className="space-y-2">
        {evidence.map((item, idx) => (
          <div
            key={idx}
            className="p-3 bg-white border border-neutral-200 rounded-md text-sm"
          >
            <p className="text-neutral-900">{item.text || item.description}</p>
            {item.source && (
              <p className="text-xs text-neutral-500 mt-1">
                Source: {item.source}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function LoadingDots() {
  return (
    <div className="flex items-center gap-2 text-sm text-neutral-600">
      <span className="inline-flex gap-1">
        <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce [animation-delay:-0.2s]" />
        <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" />
        <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce [animation-delay:0.2s]" />
      </span>
      <span>Loading evidence...</span>
    </div>
  );
}
