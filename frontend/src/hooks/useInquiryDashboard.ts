/**
 * React Query hooks for inquiry dashboard and evidence
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inquiriesAPI } from '@/lib/api/inquiries';

export interface InquiryDashboardData {
  by_status: {
    open: any[];
    investigating: any[];
    resolved: any[];
    archived: any[];
  };
  summary: {
    total: number;
    open: number;
    investigating: number;
    resolved: number;
    completion_rate: number;
  };
  next_actions: Array<{
    type: string;
    inquiry_id: string;
    title: string;
    priority: number;
  }>;
}

export interface EvidenceSummaryData {
  supporting: any[];
  contradicting: any[];
  neutral: any[];
  summary: {
    total_evidence: number;
    supporting_count: number;
    contradicting_count: number;
    neutral_count: number;
    avg_credibility: number;
    aggregate_confidence: number;
    strength: 'strong' | 'moderate' | 'weak';
    ready_to_resolve: boolean;
    recommended_conclusion: string | null;
  };
}

export function useInquiryDashboard(caseId: string | undefined) {
  return useQuery<InquiryDashboardData>({
    queryKey: ['inquiries', 'dashboard', caseId],
    queryFn: () => inquiriesAPI.getDashboard(caseId!),
    enabled: !!caseId,
    refetchInterval: 30000, // Refetch every 30s to show live updates
  });
}

export function useEvidenceSummary(inquiryId: string | undefined) {
  return useQuery<EvidenceSummaryData>({
    queryKey: ['inquiries', inquiryId, 'evidence-summary'],
    queryFn: () => inquiriesAPI.getEvidenceSummary(inquiryId!),
    enabled: !!inquiryId,
    refetchInterval: 15000, // Refetch every 15s as evidence is added
  });
}

export function useStartInvestigation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (inquiryId: string) => inquiriesAPI.startInvestigation(inquiryId),
    onSuccess: (data, inquiryId) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['inquiries'] });
      queryClient.invalidateQueries({ queryKey: ['inquiries', 'dashboard'] });
    },
  });
}

export function useCreateInquiryFromAssumption() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (params: { caseId: string; assumptionText: string; autoGenerateTitle?: boolean }) =>
      inquiriesAPI.createFromAssumption(params),
    onSuccess: (data, variables) => {
      // Invalidate case and inquiry queries
      queryClient.invalidateQueries({ queryKey: ['cases', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['inquiries', 'dashboard', variables.caseId] });
    },
  });
}
