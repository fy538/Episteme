export interface Project {
  id: string;
  title: string;
  description?: string;
  is_archived?: boolean;
  total_documents?: number;
  total_cases?: number;
  case_count_by_status?: {
    active: number;
    draft: number;
    archived: number;
  };
  has_hierarchy?: boolean;
  latest_activity?: string;
  created_at: string;
  updated_at: string;
}
