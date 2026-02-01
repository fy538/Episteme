/**
 * React Query hooks for case onboarding
 */
import { useQuery } from '@tanstack/react-query';
import { casesAPI } from '@/lib/api/cases';

export interface OnboardingData {
  auto_created: {
    inquiries: any[];
    assumptions: string[];
    brief_exists: boolean;
    brief_id: string | null;
  };
  next_steps: Array<{
    action: string;
    title: string;
    description: string;
    inquiry_id?: string;
    completed: boolean;
    priority: number;
  }>;
  first_time_user: boolean;
  summary: {
    total_inquiries: number;
    assumptions_count: number;
    from_conversation: boolean;
  };
}

export function useCaseOnboarding(caseId: string | undefined) {
  return useQuery<OnboardingData>({
    queryKey: ['cases', caseId, 'onboarding'],
    queryFn: () => casesAPI.getOnboarding(caseId!),
    enabled: !!caseId,
    staleTime: 5 * 60 * 1000, // 5 minutes (onboarding data doesn't change often)
  });
}
