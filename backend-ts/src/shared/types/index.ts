// Re-export all types from schemas for easy consumption by React frontend
export * from '../schemas/player';

// Common API response types
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface ErrorResponse {
  error: string;
  message: string;
  code?: string;
  details?: unknown;
}

// React-friendly type utilities
export type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

export type ApiEndpointConfig = {
  baseUrl: string;
  timeout: number;
  retries: number;
};