/**
 * User Preferences API
 */

import { apiClient } from './client';

export interface UserPreferences {
  // Workspace
  default_case_view: 'brief' | 'dashboard' | 'documents';
  auto_save_delay_ms: number;
  auto_create_inquiries: boolean;
  auto_detect_assumptions: boolean;
  auto_generate_titles: boolean;
  structure_auto_detect?: boolean;
  structure_sensitivity?: number;
  structure_auto_create?: boolean;
  
  // AI/Agents
  chat_model: string;
  agent_check_interval: number;
  agent_min_confidence: number;
  agent_auto_run: boolean;
  show_agent_reasoning?: boolean;
  show_agent_confidence?: boolean;
  
  // Evidence
  evidence_min_credibility: number;
  highlight_assumptions?: boolean;
  highlight_questions?: boolean;
  highlight_evidence?: boolean;
  
  // Appearance
  theme: 'light' | 'dark' | 'auto';
  font_size: 'small' | 'medium' | 'large';
  density: 'compact' | 'comfortable' | 'relaxed';
  
  // Notifications
  email_notifications: boolean;
  notify_on_inquiry_resolved: boolean;
  notify_on_agent_complete: boolean;
  
  // Advanced
  show_debug_info: boolean;
  show_ai_prompts: boolean;
  
  // Metadata
  created_at: string;
  updated_at: string;
}

export const preferencesAPI = {
  async getPreferences(): Promise<UserPreferences> {
    return apiClient.get<UserPreferences>('/auth/preferences/');
  },

  async updatePreferences(updates: Partial<UserPreferences>): Promise<UserPreferences> {
    return apiClient.patch<UserPreferences>('/auth/preferences/', updates);
  },

  async resetToDefaults(): Promise<UserPreferences> {
    // Reset by updating with default values
    const defaults: Partial<UserPreferences> = {
      default_case_view: 'brief',
      auto_save_delay_ms: 1000,
      auto_create_inquiries: true,
      auto_detect_assumptions: true,
      auto_generate_titles: true,
      chat_model: 'anthropic:claude-haiku-4-5',
      agent_check_interval: 3,
      agent_min_confidence: 0.75,
      agent_auto_run: false,
      evidence_min_credibility: 3,
      theme: 'light',
      font_size: 'medium',
      density: 'comfortable',
    };
    
    return apiClient.patch<UserPreferences>('/auth/preferences/', defaults);
  },
};
