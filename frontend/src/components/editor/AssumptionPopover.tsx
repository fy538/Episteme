/**
 * Popover showing assumption details and actions
 */

'use client';

import { Button } from '@/components/ui/button';

interface Assumption {
  id: string;
  text: string;
  status: 'untested' | 'investigating' | 'validated';
  risk_level: 'low' | 'medium' | 'high';
  inquiry_id?: string;
  validation_approach?: string;
}

interface AssumptionPopoverProps {
  assumption: Assumption;
  position: { x: number; y: number };
  onCreateInquiry: () => void;
  onViewInquiry?: (inquiryId: string) => void;
  onMarkValidated?: () => void;
  onClose: () => void;
}

export function AssumptionPopover({
  assumption,
  position,
  onCreateInquiry,
  onViewInquiry,
  onMarkValidated,
  onClose,
}: AssumptionPopoverProps) {
  const statusColors = {
    untested: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' },
    investigating: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
    validated: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
  };

  const riskIcons = {
    low: '🟢',
    medium: '🟡',
    high: '🔴',
  };

  const colors = statusColors[assumption.status];

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={onClose}
      />

      {/* Popover */}
      <div
        className={`fixed z-50 bg-white border-2 ${colors.border} rounded-lg shadow-xl p-4 max-w-sm`}
        style={{
          left: `${position.x}px`,
          top: `${position.y + 10}px`,
        }}
      >
        <div className={`${colors.bg} ${colors.text} px-3 py-2 rounded-lg mb-3`}>
          <h4 className="font-semibold mb-1">
            Assumption
          </h4>
          <p className="text-sm">"{assumption.text}"</p>
        </div>

        <div className="space-y-2 text-sm mb-3">
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Status:</span>
            <span className={`font-medium ${colors.text}`}>
              {assumption.status}
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Risk if wrong:</span>
            <span className="font-medium">
              {riskIcons[assumption.risk_level]} {assumption.risk_level}
            </span>
          </div>

          {assumption.validation_approach && (
            <div className="pt-2 border-t border-gray-200">
              <p className="text-gray-600 text-xs">
                Suggested: {assumption.validation_approach}
              </p>
            </div>
          )}
        </div>

        <div className="space-y-2">
          {assumption.status === 'untested' && (
            <Button
              onClick={() => {
                onCreateInquiry();
                onClose();
              }}
              size="sm"
              className="w-full"
            >
              Create Inquiry to Validate
            </Button>
          )}

          {assumption.inquiry_id && onViewInquiry && (
            <Button
              onClick={() => {
                onViewInquiry(assumption.inquiry_id!);
                onClose();
              }}
              size="sm"
              variant="outline"
              className="w-full"
            >
              View Inquiry →
            </Button>
          )}

          {assumption.status !== 'validated' && onMarkValidated && (
            <Button
              onClick={() => {
                onMarkValidated();
                onClose();
              }}
              size="sm"
              variant="outline"
              className="w-full text-green-700"
            >
              Mark as Validated
            </Button>
          )}
        </div>
      </div>
    </>
  );
}
