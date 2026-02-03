/**
 * Projects API functions
 */

import { apiClient } from './client';
import type { Project } from '../types/project';

export const projectsAPI = {
  async listProjects(): Promise<Project[]> {
    const response = await apiClient.get<{ results: Project[] }>('/projects/');
    return response.results || [];
  },

  async getProject(projectId: string): Promise<Project> {
    return apiClient.get<Project>(`/projects/${projectId}/`);
  },

  async createProject(data: { title: string; description?: string }): Promise<Project> {
    return apiClient.post<Project>('/projects/', data);
  },

  async updateProject(projectId: string, data: Partial<Project>): Promise<Project> {
    return apiClient.patch<Project>(`/projects/${projectId}/`, data);
  },

  async deleteProject(projectId: string): Promise<void> {
    await apiClient.delete(`/projects/${projectId}/`);
  },
};
