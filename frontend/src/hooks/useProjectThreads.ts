/**
 * useProjectThreads — fetches past chat threads for a project.
 *
 * Backend already supports `project_id` filter on `/chat/threads/`.
 * Returns non-archived threads sorted by most recent activity.
 */

import { useQuery } from '@tanstack/react-query';
import { chatAPI } from '@/lib/api/chat';

export function useProjectThreads(projectId: string | undefined) {
  return useQuery({
    queryKey: ['project-threads', projectId],
    queryFn: () => chatAPI.listThreads({ project_id: projectId!, archived: 'false' }),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}
