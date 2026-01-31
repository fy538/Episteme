/**
 * Knowledge Graph API client
 * 
 * For querying relationships between signals and evidence.
 */

import { apiClient } from './client';

export interface DependencyChain {
  root: any;  // Signal
  dependencies: any[];  // Signals
  depth: number;
}

export interface EvidenceStrength {
  supporting: any[];  // Evidence
  contradicting: any[];  // Evidence
  strength: {
    support_count: number;
    contradict_count: number;
    avg_support_credibility: number;
    strength: 'strong' | 'moderate' | 'weak';
  };
}

export interface Contradictions {
  this_contradicts: any[];  // Signals
  contradicted_by: any[];  // Signals
}

export const graphAPI = {
  /**
   * Get dependency chain for a signal
   */
  signalDependencies: async (signalId: string): Promise<DependencyChain> => {
    return apiClient.get(`/signals/${signalId}/dependencies/`);
  },

  /**
   * Get supporting and contradicting evidence for a signal
   */
  signalEvidence: async (signalId: string): Promise<EvidenceStrength> => {
    return apiClient.get(`/signals/${signalId}/evidence/`);
  },

  /**
   * Find contradicting signals
   */
  signalContradictions: async (signalId: string): Promise<Contradictions> => {
    return apiClient.get(`/signals/${signalId}/contradictions/`);
  },

  /**
   * Link two signals
   */
  linkSignals: async (
    signalId: string,
    targetSignalId: string,
    relationship: 'depends_on' | 'contradicts'
  ): Promise<any> => {
    return apiClient.post(`/signals/${signalId}/link/`, {
      target_signal_id: targetSignalId,
      relationship,
    });
  },
};
