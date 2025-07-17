import { ApiConfig, ApiResponse } from '@/types';

export class ApiClient {
  private config: ApiConfig;

  constructor(config: Partial<ApiConfig> = {}) {
    this.config = {
      baseUrl: config.baseUrl || '/api',
      headers: {
        'Content-Type': 'application/json',
        ...config.headers,
      },
    };
  }

  private async request<T>(
    method: string,
    endpoint: string,
    data?: any,
    customHeaders?: Record<string, string>
  ): Promise<ApiResponse<T>> {
    const headers: Record<string, string> = {
      ...this.config.headers,
      ...customHeaders,
    };

    try {
      const response = await fetch(`${this.config.baseUrl}${endpoint}`, {
        method,
        headers,
        credentials: 'include', // Include cookies for authentication
        body: data ? JSON.stringify(data) : undefined,
      });

      const responseData = await response.json();

      if (!response.ok) {
        return {
          data: responseData as T,
          error: responseData.error || 'Request failed',
          status: response.status,
        };
      }

      return {
        data: responseData as T,
        status: response.status,
      };
    } catch (error) {
      return {
        data: {} as T,
        error: error instanceof Error ? error.message : 'Network error',
        status: 500,
      };
    }
  }

  async get<T>(endpoint: string, customHeaders?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('GET', endpoint, undefined, customHeaders);
  }

  async post<T>(endpoint: string, data: any, customHeaders?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('POST', endpoint, data, customHeaders);
  }

  async put<T>(endpoint: string, data: any, customHeaders?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', endpoint, data, customHeaders);
  }

  async delete<T>(endpoint: string, customHeaders?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', endpoint, undefined, customHeaders);
  }

  // SSE (Server-Sent Events) helper for real-time updates
  createEventSource(endpoint: string): EventSource {
    const url = `${this.config.baseUrl}${endpoint}`;
    return new EventSource(url, { withCredentials: true });
  }
} 
