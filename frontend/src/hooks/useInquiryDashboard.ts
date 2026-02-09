/**
 * React Query hooks for inquiry dashboard
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inquiriesAPI } from '@/lib/api/inquiries';

/** Inquiry item in dashboard */
export interface DashboardInquiry {
  id: string;
  title: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface InquiryDashboardData {
  by_status: {
    open: DashboardInquiry[];
    investigating: DashboardInquiry[];
    resolved: DashboardInquiry[];
    archived: DashboardInquiry[];
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

export function useInquiryDashboard(caseId: string | undefined) {
  return useQuery<InquiryDashboardData>({
    queryKey: ['inquiries', 'dashboard', caseId],
    queryFn: () => inquiriesAPI.getDashboard(caseId!),
    enabled: !!caseId,
    refetchInterval: 30000, // Refetch every 30s to show live updates
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
