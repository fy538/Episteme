/**
 * Inquiry Dashboard Component
 * 
 * Shows investigation status overview with next actions.
 * Core experience component - makes inquiries prominent.
 * 
 * Uses design system: Card, Button, Badge with semantic colors.
 */

'use client';

import * as React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useInquiryDashboard, useStartInvestigation } from '@/hooks/useInquiryDashboard';

interface InquiryDashboardProps {
  caseId: string;
  onStartInquiry?: (inquiryId: string) => void;
  onViewInquiry?: (inquiryId: string) => void;
}

export function InquiryDashboard({ caseId, onStartInquiry, onViewInquiry }: InquiryDashboardProps) {
  const { data: dashboard, isLoading } = useInquiryDashboard(caseId);
  const startInvestigation = useStartInvestigation();

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-sm text-neutral-600">
            <LoadingDots />
            <span>Loading dashboard...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!dashboard) {
    return null;
  }

  const { by_status, summary, next_actions } = dashboard;

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Investigation Progress</CardTitle>
              <CardDescription>
                {summary.resolved} of {summary.total} inquiries resolved
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="neutral" className="text-sm">
                {summary.completion_rate.toFixed(0)}% Complete
              </Badge>
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <StatCard
              label="Open"
              value={summary.open}
              variant="warning"
            />
            <StatCard
              label="Investigating"
              value={summary.investigating}
              variant="default"
            />
            <StatCard
              label="Resolved"
              value={summary.resolved}
              variant="success"
            />
            <StatCard
              label="Total"
              value={summary.total}
              variant="neutral"
            />
          </div>
        </CardContent>
      </Card>

      {/* Next Actions */}
      {next_actions && next_actions.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-neutral-900 mb-3">
            Suggested Next Actions
          </h3>
          <div className="space-y-3">
            {next_actions.map((action, idx) => (
              <Card key={action.inquiry_id}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-100 flex items-center justify-center">
                        <span className="text-xs font-medium text-primary-700">
                          {idx + 1}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-neutral-900">
                        {action.title}
                      </p>
                    </div>
                    
                    <div className="flex gap-2">
                      {action.type === 'start_investigation' && onStartInquiry && (
                        <Button
                          size="sm"
                          onClick={() => onStartInquiry(action.inquiry_id)}
                        >
                          Start Investigation
                        </Button>
                      )}
                      
                      {action.type === 'resolve_inquiry' && onViewInquiry && (
                        <Button
                          size="sm"
                          variant="success"
                          onClick={() => onViewInquiry(action.inquiry_id)}
                        >
                          Resolve
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Inquiries by Status */}
      <div className="space-y-6">
        {/* Open Inquiries */}
        {by_status.open && by_status.open.length > 0 && (
          <InquirySection
            title="Open Inquiries"
            inquiries={by_status.open}
            statusColor="warning"
            onStartInquiry={onStartInquiry}
            onViewInquiry={onViewInquiry}
            startInvestigation={startInvestigation}
          />
        )}

        {/* Investigating */}
        {by_status.investigating && by_status.investigating.length > 0 && (
          <InquirySection
            title="Currently Investigating"
            inquiries={by_status.investigating}
            statusColor="primary"
            onViewInquiry={onViewInquiry}
          />
        )}

        {/* Resolved */}
        {by_status.resolved && by_status.resolved.length > 0 && (
          <InquirySection
            title="Resolved"
            inquiries={by_status.resolved}
            statusColor="success"
            onViewInquiry={onViewInquiry}
          />
        )}
      </div>
    </div>
  );
}

// Helper Components

function StatCard({ label, value, variant }: { label: string; value: number; variant: string }) {
  const colorClasses = {
    warning: 'bg-warning-50 text-warning-900 border-warning-200',
    default: 'bg-primary-50 text-primary-900 border-primary-200',
    success: 'bg-success-50 text-success-900 border-success-200',
    neutral: 'bg-neutral-50 text-neutral-900 border-neutral-200',
  };

  return (
    <div className={`p-4 rounded-md border ${colorClasses[variant as keyof typeof colorClasses]}`}>
      <p className="text-2xl tracking-tight font-semibold">{value}</p>
      <p className="text-xs font-medium mt-1">{label}</p>
    </div>
  );
}

function InquirySection({
  title,
  inquiries,
  statusColor,
  onStartInquiry,
  onViewInquiry,
  startInvestigation,
}: {
  title: string;
  inquiries: any[];
  statusColor: string;
  onStartInquiry?: (id: string) => void;
  onViewInquiry?: (id: string) => void;
  startInvestigation?: any;
}) {
  return (
    <div>
      <h3 className="text-lg font-semibold text-neutral-900 mb-3">{title}</h3>
      <div className="space-y-2">
        {inquiries.map((inquiry) => (
          <Card key={inquiry.id}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-neutral-900 mb-1">
                    {inquiry.title}
                  </p>
                  {inquiry.description && (
                    <p className="text-xs text-neutral-600">
                      {inquiry.description}
                    </p>
                  )}
                </div>
                
                <div className="flex gap-2">
                  {inquiry.status === 'OPEN' && onStartInquiry && (
                    <Button
                      size="sm"
                      onClick={() => onStartInquiry(inquiry.id)}
                    >
                      Start
                    </Button>
                  )}
                  
                  {onViewInquiry && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onViewInquiry(inquiry.id)}
                    >
                      View
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function LoadingDots() {
  return (
    <span className="inline-flex gap-1">
      <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce [animation-delay:-0.2s]" />
      <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" />
      <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce [animation-delay:0.2s]" />
    </span>
  );
}
