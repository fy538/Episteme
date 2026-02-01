/**
 * React Query hooks for user preferences
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { preferencesAPI, type UserPreferences } from '@/lib/api/preferences';

export function useUserPreferences() {
  return useQuery<UserPreferences>({
    queryKey: ['user', 'preferences'],
    queryFn: () => preferencesAPI.getPreferences(),
    staleTime: 5 * 60 * 1000, // 5 minutes (preferences don't change often)
  });
}

export function useUpdatePreferences() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (updates: Partial<UserPreferences>) => 
      preferencesAPI.updatePreferences(updates),
    onSuccess: (updatedPreferences) => {
      // Update the cache with new preferences
      queryClient.setQueryData(['user', 'preferences'], updatedPreferences);
    },
  });
}

export function useResetPreferences() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => preferencesAPI.resetToDefaults(),
    onSuccess: (defaultPreferences) => {
      queryClient.setQueryData(['user', 'preferences'], defaultPreferences);
    },
  });
}

/**
 * Hook to get a specific preference value
 * Returns the value or a default if preferences aren't loaded
 */
export function usePreference<K extends keyof UserPreferences>(
  key: K,
  defaultValue: UserPreferences[K]
): UserPreferences[K] {
  const { data: preferences } = useUserPreferences();
  return preferences?.[key] ?? defaultValue;
}
