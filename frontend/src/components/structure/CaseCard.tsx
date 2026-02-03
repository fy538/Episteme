/**
 * Case card component - shows active case info
 * Enhanced with hover preview
 */

'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import type { Case, Inquiry } from '@/lib/types/case';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useHoverShadow } from '@/components/ui/card-hover';

export function CaseCard({ caseId }: { caseId: string }) {
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [isHovered, setIsHovered] = useState(false);
  const prefersReducedMotion = useReducedMotion();
  const hoverShadow = useHoverShadow();

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
    return <div className="text-sm text-neutral-500">Loading case...</div>;
  }

  const content = (
    <>
      <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-1">
        Active Case
      </h3>
      <p className="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-2">
        {caseData.title}
      </p>
      
      {/* Show preview on hover */}
      {isHovered && inquiries.length > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.2 }}
          className="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700"
        >
          <h4 className="text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
            Inquiries ({inquiries.length})
          </h4>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {inquiries.slice(0, 5).map(inquiry => (
              <div key={inquiry.id} className="text-sm text-neutral-700 dark:text-neutral-300">
                • {inquiry.title}
              </div>
            ))}
            {inquiries.length > 5 && (
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                +{inquiries.length - 5} more
              </div>
            )}
          </div>
        </motion.div>
      )}
    </>
  );

  if (prefersReducedMotion) {
    return (
      <div 
        className="p-3 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg group"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {content}
      </div>
    );
  }

  return (
    <motion.div
      className="p-3 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg cursor-pointer"
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      whileHover={{ scale: 1.02, y: -2, boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)' }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 20,
      }}
    >
      {content}
    </motion.div>
  );
}
