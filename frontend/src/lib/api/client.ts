/**
 * API Client for Django backend
 */

import * as Sentry from '@sentry/nextjs';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export class APIClient {
  private baseURL: string;
  private token: string | null;

  constructor() {
    this.baseURL = API_BASE_URL;
    this.token = null;
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

  async post<T>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async stream(
    endpoint: string,
    data: any,
    onEvent: (event: { event: string; data: any }) => void,
    signal?: AbortSignal
  ): Promise<void> {
    const isDevMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
    const token = isDevMode ? null : this.getToken();

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
      ...(token && { Authorization: `Bearer ${token}` }),
    };

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
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

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const raw of events) {
        const lines = raw.split('\n');
        let eventType = 'message';
        let dataPayload = '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.replace('event:', '').trim();
          } else if (line.startsWith('data:')) {
            dataPayload += line.replace('data:', '').trim();
          }
        }

        if (!dataPayload) continue;
        try {
          onEvent({ event: eventType, data: JSON.parse(dataPayload) });
        } catch {
          onEvent({ event: eventType, data: dataPayload });
        }
      }
    }
  }

  async put<T>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async patch<T>(endpoint: string, data: any): Promise<T> {
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
