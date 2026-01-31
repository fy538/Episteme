/**
 * Case card component - shows active case info
 */

'use client';

import { useState, useEffect } from 'react';
import type { Case, Inquiry } from '@/lib/types/case';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';

export function CaseCard({ caseId }: { caseId: string }) {
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);

  useEffect(() => {
    async function loadCase() {
      try {
        const c = await casesAPI.getCase(caseId);
        setCaseData(c);
      } catch (error) {
        console.error('Failed to load case:', error);
      }
    }

    async function loadInquiries() {
      try {
        const inqs = await inquiriesAPI.getByCase(caseId);
        setInquiries(inqs);
      } catch (error) {
        console.error('Failed to load inquiries:', error);
      }
    }

    loadCase();
    loadInquiries();

    // Poll for updates
    const interval = setInterval(() => {
      loadCase();
      loadInquiries();
    }, 5000);

    return () => clearInterval(interval);
  }, [caseId]);

  if (!caseData) {
    return <div className="text-sm text-gray-500">Loading case...</div>;
  }

  return (
    <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
      <h3 className="text-sm font-semibold text-gray-900 mb-1">
        Active Case
      </h3>
      <p className="text-lg font-medium text-gray-900 mb-2">
        {caseData.title}
      </p>
      
      {inquiries.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <h4 className="text-xs font-semibold text-gray-700 mb-2">
            Inquiries ({inquiries.length})
          </h4>
          <div className="space-y-1">
            {inquiries.map(inquiry => (
              <div key={inquiry.id} className="text-sm text-gray-700">
                • {inquiry.title}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
