/**
 * Evidence List Component
 * 
 * Displays list of evidence items with filtering.
 */

'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { evidenceAPI, type Evidence } from '@/lib/api/evidence';
import { EvidenceCard } from './EvidenceCard';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { easingCurves, transitionDurations } from '@/lib/motion-config';

const listContainerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.04 } },
};

const listItemVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: transitionDurations.fast, ease: easingCurves.easeOutExpo },
  },
};

interface EvidenceListProps {
  caseId?: string;
  documentId?: string;
  projectId?: string;
}

export function EvidenceList({ caseId, documentId, projectId }: EvidenceListProps) {
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [filteredEvidence, setFilteredEvidence] = useState<Evidence[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const prefersReducedMotion = useReducedMotion();
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [minRating, setMinRating] = useState<number>(0);

  useEffect(() => {
    loadEvidence();
  }, [caseId, documentId, projectId]);

  useEffect(() => {
    applyFilters();
  }, [evidence, typeFilter, minRating]);

  const loadEvidence = async () => {
    setIsLoading(true);
    try {
      const data = await evidenceAPI.list({
        case_id: caseId,
        document_id: documentId,
        project_id: projectId,
      });
      setEvidence(data);
    } catch (error) {
      console.error('Failed to load evidence:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = evidence;

    if (typeFilter !== 'all') {
      filtered = filtered.filter(e => e.type === typeFilter);
    }

    if (minRating > 0) {
      filtered = filtered.filter(e => 
        e.user_credibility_rating && e.user_credibility_rating >= minRating
      );
    }

    setFilteredEvidence(filtered);
  };

  if (isLoading) {
    return <div className="text-center py-8 text-neutral-500">Loading evidence...</div>;
  }

  return (
    <div>
      {/* Filters */}
      <div className="mb-4 flex gap-4">
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Type
          </label>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border rounded px-3 py-1"
          >
            <option value="all">All Types</option>
            <option value="metric">Metrics</option>
            <option value="benchmark">Benchmarks</option>
            <option value="fact">Facts</option>
            <option value="claim">Claims</option>
            <option value="quote">Quotes</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Min Rating
          </label>
          <select
            value={minRating}
            onChange={(e) => setMinRating(Number(e.target.value))}
            className="border rounded px-3 py-1"
          >
            <option value="0">Any</option>
            <option value="3">3+ stars</option>
            <option value="4">4+ stars</option>
            <option value="5">5 stars</option>
          </select>
        </div>
      </div>

      {/* Results count */}
      <div className="mb-3 text-sm text-neutral-600">
        Showing {filteredEvidence.length} of {evidence.length} evidence items
      </div>

      {/* Evidence list */}
      <motion.div
        className="space-y-3"
        variants={prefersReducedMotion ? undefined : listContainerVariants}
        initial="hidden"
        animate="visible"
        key={`${typeFilter}-${minRating}`}
      >
        {filteredEvidence.length === 0 ? (
          <div className="text-center py-8 text-neutral-500">
            No evidence found
          </div>
        ) : (
          filteredEvidence.map((item) => (
            <motion.div key={item.id} variants={prefersReducedMotion ? undefined : listItemVariants}>
              <EvidenceCard
                evidence={item}
                onUpdate={(updated) => {
                  setEvidence(prev =>
                    prev.map(e => e.id === updated.id ? updated : e)
                  );
                }}
                showLinkButton
              />
            </motion.div>
          ))
        )}
      </motion.div>
    </div>
  );
}
