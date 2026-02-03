export interface Project {
  id: string;
  title: string;
  description?: string;
  is_archived?: boolean;
  total_documents?: number;
  created_at: string;
  updated_at: string;
}
