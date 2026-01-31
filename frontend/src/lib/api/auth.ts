/**
 * Authentication API functions
 */

import { apiClient } from './client';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface TokenResponse {
  access: string;
  refresh: string;
}

export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
}

export const authAPI = {
  /**
   * Login with email and password
   */
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>('/auth/token/', credentials);
    
    // Debug log
    console.log('Login successful, tokens received:', {
      hasAccess: !!response.access,
      hasRefresh: !!response.refresh,
    });
    
    // Save the access token
    apiClient.setToken(response.access);
    // Save refresh token to localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('refresh_token', response.refresh);
      // Verify it was saved
      console.log('Token saved to localStorage:', {
        authToken: localStorage.getItem('auth_token')?.substring(0, 20) + '...',
        refreshToken: localStorage.getItem('refresh_token')?.substring(0, 20) + '...',
      });
    }
    return response;
  },

  /**
   * Logout - clear tokens
   */
  logout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
    }
    apiClient.setToken('');
  },

  /**
   * Get current user
   */
  async getCurrentUser(): Promise<User> {
    return apiClient.get<User>('/auth/me/');
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    if (typeof window === 'undefined') return false;
    const token = localStorage.getItem('auth_token');
    return !!token;
  },

  /**
   * Refresh the access token
   */
  async refreshToken(): Promise<string> {
    if (typeof window === 'undefined') throw new Error('Not in browser');
    
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) throw new Error('No refresh token');

    const response = await apiClient.post<{ access: string }>('/auth/token/refresh/', {
      refresh: refreshToken,
    });
    
    apiClient.setToken(response.access);
    return response.access;
  },
};
