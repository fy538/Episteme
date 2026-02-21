/**
 * API Client for Django backend
 */

import * as Sentry from '@sentry/nextjs';
import { parseSSEStream, type SSEEvent } from './sse-parser';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export class APIClient {
  private baseURL: string;
  private token: string | null;

  constructor() {
    this.baseURL = API_BASE_URL;
    this.token = null;
  }

  getBaseURL(): string {
    return this.baseURL;
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
    }
  }

  getToken(): string | null {
    if (this.token) {
      return this.token;
    }
    
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token');
    }
    
    return this.token;
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    // Dev mode bypass: skip auth for local development
    const isDevMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
    const token = isDevMode ? null : this.getToken();
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    };

    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        headers,
        mode: 'cors',
      });

      const correlationId = response.headers.get('X-Correlation-ID');

      if (!response.ok) {
        let errorMessage = `API Error ${response.status}`;
        try {
          // Try to get the response body as text first
          const responseText = await response.text();
          if (responseText) {
            try {
              // Try to parse as JSON
              const errorData = JSON.parse(responseText);
              errorMessage = errorData.detail || errorData.error || JSON.stringify(errorData);
            } catch {
              // Not JSON, use the text directly
              errorMessage = responseText;
            }
          }
        } catch (err) {
          console.error('Error reading response:', err);
        }
        if (errorMessage.toLowerCase().includes('token not valid')) {
          this.clearToken();
        }

        const error = new Error(errorMessage);
        Sentry.captureException(error, {
          tags: {
            endpoint,
            method: options.method || 'GET',
          },
          extra: {
            status: response.status,
            correlationId,
          },
        });
        throw error;
      }

      return response.json();
    } catch (err) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        Sentry.captureException(err, {
          tags: {
            endpoint,
            method: options.method || 'GET',
          },
        });
        throw new Error(`Cannot connect to backend at ${this.baseURL}. Please check if the backend is running and CORS is configured.`);
      }
      if (err instanceof Error) {
        Sentry.captureException(err, {
          tags: {
            endpoint,
            method: options.method || 'GET',
          },
        });
      }
      throw err;
    }
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async post<T>(endpoint: string, data: Record<string, any>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async stream(
    endpoint: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data: Record<string, any> | undefined,
    onEvent: (event: SSEEvent) => void,
    signal?: AbortSignal
  ): Promise<void> {
    const isDevMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
    const token = isDevMode ? null : this.getToken();

    const isGet = data === undefined || data === null;
    const headers: HeadersInit = {
      ...(!isGet && { 'Content-Type': 'application/json' }),
      'Accept': 'text/event-stream',
      ...(token && { Authorization: `Bearer ${token}` }),
    };

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: isGet ? 'GET' : 'POST',
      headers,
      ...(!isGet && { body: JSON.stringify(data) }),
      mode: 'cors',
      signal, // Pass abort signal
    });

    if (!response.ok) {
      let errorMessage = `API Error ${response.status}`;
      try {
        const responseText = await response.text();
        if (responseText) {
          try {
            const errorData = JSON.parse(responseText);
            errorMessage = errorData.detail || errorData.error || JSON.stringify(errorData);
          } catch {
            errorMessage = responseText;
          }
        }
      } catch (err) {
        console.error('Error reading response:', err);
      }
      if (errorMessage.toLowerCase().includes('token not valid')) {
        this.clearToken();
      }
      throw new Error(errorMessage);
    }

    if (!response.body) return;
    await parseSSEStream(response.body, onEvent);
  }

  async upload<T>(endpoint: string, formData: FormData): Promise<T> {
    const isDevMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
    const token = isDevMode ? null : this.getToken();

    // No Content-Type — browser sets multipart/form-data with boundary
    const headers: HeadersInit = {
      ...(token && { Authorization: `Bearer ${token}` }),
    };

    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        method: 'POST',
        headers,
        body: formData,
        mode: 'cors',
      });

      if (!response.ok) {
        let errorMessage = `API Error ${response.status}`;
        try {
          const responseText = await response.text();
          if (responseText) {
            try {
              const errorData = JSON.parse(responseText);
              errorMessage = errorData.detail || errorData.error || JSON.stringify(errorData);
            } catch {
              errorMessage = responseText;
            }
          }
        } catch (err) {
          console.error('Error reading response:', err);
        }
        if (errorMessage.toLowerCase().includes('token not valid')) {
          this.clearToken();
        }
        throw new Error(errorMessage);
      }

      return response.json();
    } catch (err) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        throw new Error(`Cannot connect to backend at ${this.baseURL}. Please check if the backend is running and CORS is configured.`);
      }
      throw err;
    }
  }

  async streamGet(
    endpoint: string,
    onEvent: (event: SSEEvent) => void,
    signal?: AbortSignal
  ): Promise<void> {
    return this.stream(endpoint, undefined, onEvent, signal);
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async put<T>(endpoint: string, data: Record<string, any>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async patch<T>(endpoint: string, data: Record<string, any>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new APIClient();
