/**
 * Centralized API helper utilities for Budget Famille v2.3 Frontend
 * Eliminates duplicate API handling patterns across components
 */

import { AxiosResponse } from 'axios';
import { api } from '../api';
import type { ApiResponse, LoadingState, PaginationParams } from './types';
import { handleError, withRetry, createErrorFromAxios } from './errorHandling';

/**
 * Standard API request wrapper with error handling
 */
export async function apiRequest<T = any>(
  requestFn: () => Promise<AxiosResponse<T>>,
  options: {
    retries?: number;
    showLoading?: boolean;
    onLoading?: (state: LoadingState) => void;
  } = {}
): Promise<T> {
  const { retries = 0, showLoading = false, onLoading } = options;

  if (showLoading && onLoading) {
    onLoading({ isLoading: true });
  }

  try {
    const operation = () => requestFn().then(response => response.data);
    
    const result = retries > 0 
      ? await withRetry(operation, retries + 1)
      : await operation();

    if (showLoading && onLoading) {
      onLoading({ isLoading: false });
    }

    return result;
  } catch (error) {
    if (showLoading && onLoading) {
      onLoading({ isLoading: false });
    }
    throw error;
  }
}

/**
 * GET request helper
 */
export async function apiGet<T = any>(
  url: string,
  params?: Record<string, any>,
  options?: { retries?: number; showLoading?: boolean; onLoading?: (state: LoadingState) => void }
): Promise<T> {
  return apiRequest(() => api.get(url, { params }), options);
}

/**
 * POST request helper
 */
export async function apiPost<T = any>(
  url: string,
  data?: any,
  options?: { retries?: number; showLoading?: boolean; onLoading?: (state: LoadingState) => void }
): Promise<T> {
  return apiRequest(() => api.post(url, data), options);
}

/**
 * PUT request helper
 */
export async function apiPut<T = any>(
  url: string,
  data?: any,
  options?: { retries?: number; showLoading?: boolean; onLoading?: (state: LoadingState) => void }
): Promise<T> {
  return apiRequest(() => api.put(url, data), options);
}

/**
 * PATCH request helper
 */
export async function apiPatch<T = any>(
  url: string,
  data?: any,
  options?: { retries?: number; showLoading?: boolean; onLoading?: (state: LoadingState) => void }
): Promise<T> {
  return apiRequest(() => api.patch(url, data), options);
}

/**
 * DELETE request helper
 */
export async function apiDelete<T = any>(
  url: string,
  options?: { retries?: number; showLoading?: boolean; onLoading?: (state: LoadingState) => void }
): Promise<T> {
  return apiRequest(() => api.delete(url), options);
}

/**
 * File upload helper
 */
export async function apiUploadFile<T = any>(
  url: string,
  file: File,
  options: {
    fieldName?: string;
    additionalData?: Record<string, any>;
    onProgress?: (progress: number) => void;
    onLoading?: (state: LoadingState) => void;
  } = {}
): Promise<T> {
  const { fieldName = 'file', additionalData = {}, onProgress, onLoading } = options;

  if (onLoading) {
    onLoading({ isLoading: true, operation: 'upload' });
  }

  const formData = new FormData();
  formData.append(fieldName, file);
  
  Object.entries(additionalData).forEach(([key, value]) => {
    formData.append(key, typeof value === 'string' ? value : JSON.stringify(value));
  });

  try {
    const response = await api.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
          
          if (onLoading) {
            onLoading({ isLoading: true, operation: 'upload', progress });
          }
        }
      },
    });

    if (onLoading) {
      onLoading({ isLoading: false });
    }

    return response.data;
  } catch (error) {
    if (onLoading) {
      onLoading({ isLoading: false });
    }
    throw error;
  }
}

/**
 * Paginated request helper
 */
export async function apiGetPaginated<T = any>(
  url: string,
  params: PaginationParams & Record<string, any> = { page: 1, limit: 50 },
  options?: { retries?: number; showLoading?: boolean; onLoading?: (state: LoadingState) => void }
): Promise<{
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}> {
  const response = await apiGet<{
    data: T[];
    meta: {
      pagination: any;
    };
  }>(url, params, options);

  return {
    data: response.data || [],
    pagination: response.meta?.pagination || {
      page: 1,
      limit: 50,
      total: 0,
      totalPages: 0,
      hasNext: false,
      hasPrevious: false
    }
  };
}

/**
 * Batch request helper
 */
export async function apiBatch<T = any>(
  requests: Array<() => Promise<AxiosResponse<T>>>,
  options: {
    concurrency?: number;
    failFast?: boolean;
    onProgress?: (completed: number, total: number) => void;
    onLoading?: (state: LoadingState) => void;
  } = {}
): Promise<T[]> {
  const { concurrency = 3, failFast = true, onProgress, onLoading } = options;
  
  if (onLoading) {
    onLoading({ isLoading: true, operation: 'batch' });
  }

  const results: T[] = [];
  const errors: Error[] = [];
  let completed = 0;

  // Process requests in batches
  for (let i = 0; i < requests.length; i += concurrency) {
    const batch = requests.slice(i, i + concurrency);
    
    try {
      const batchResults = await Promise.allSettled(
        batch.map(request => request().then(response => response.data))
      );

      batchResults.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          results[i + index] = result.value;
        } else {
          errors.push(result.reason);
          if (failFast) {
            throw result.reason;
          }
        }
      });

      completed += batch.length;
      if (onProgress) {
        onProgress(completed, requests.length);
      }

    } catch (error) {
      if (onLoading) {
        onLoading({ isLoading: false });
      }
      throw error;
    }
  }

  if (onLoading) {
    onLoading({ isLoading: false });
  }

  if (!failFast && errors.length > 0) {
    console.warn(`Batch completed with ${errors.length} errors:`, errors);
  }

  return results;
}

/**
 * Search helper with debouncing
 */
export function createSearchHelper<T = any>(
  searchUrl: string,
  debounceMs = 300
) {
  let debounceTimer: NodeJS.Timeout;
  let currentRequest: Promise<T[]> | null = null;

  return {
    search: async (query: string, filters: Record<string, any> = {}): Promise<T[]> => {
      return new Promise((resolve, reject) => {
        clearTimeout(debounceTimer);
        
        debounceTimer = setTimeout(async () => {
          try {
            // Cancel previous request if still pending
            if (currentRequest) {
              // In a real implementation, you might want to use AbortController
            }

            const params = { q: query, ...filters };
            currentRequest = apiGet<{ results: T[] }>(searchUrl, params)
              .then(response => response.results || []);

            const results = await currentRequest;
            currentRequest = null;
            resolve(results);
          } catch (error) {
            currentRequest = null;
            reject(error);
          }
        }, debounceMs);
      });
    },

    cancel: () => {
      clearTimeout(debounceTimer);
      currentRequest = null;
    }
  };
}

/**
 * Cache helper for API responses
 */
export class ApiCache {
  private cache = new Map<string, { data: any; timestamp: number; ttl: number }>();

  constructor(private defaultTtl = 5 * 60 * 1000) {} // 5 minutes

  private getCacheKey(url: string, params?: Record<string, any>): string {
    return `${url}${params ? '?' + new URLSearchParams(params).toString() : ''}`;
  }

  get<T>(url: string, params?: Record<string, any>): T | null {
    const key = this.getCacheKey(url, params);
    const cached = this.cache.get(key);
    
    if (!cached) return null;
    
    if (Date.now() - cached.timestamp > cached.ttl) {
      this.cache.delete(key);
      return null;
    }
    
    return cached.data;
  }

  set<T>(url: string, data: T, params?: Record<string, any>, ttl?: number): void {
    const key = this.getCacheKey(url, params);
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: ttl || this.defaultTtl
    });
  }

  clear(pattern?: string): void {
    if (!pattern) {
      this.cache.clear();
      return;
    }
    
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    }
  }

  async getOrFetch<T>(
    url: string,
    params?: Record<string, any>,
    ttl?: number
  ): Promise<T> {
    const cached = this.get<T>(url, params);
    if (cached) return cached;
    
    const data = await apiGet<T>(url, params);
    this.set(url, data, params, ttl);
    return data;
  }
}

// Global cache instance
export const apiCache = new ApiCache();

/**
 * React hook utilities for API calls
 */
export function createApiHook<T = any>(
  requestFn: () => Promise<T>,
  dependencies: any[] = []
) {
  return {
    fetch: requestFn,
    dependencies
  };
}

/**
 * Optimistic update helper
 */
export async function optimisticUpdate<T>(
  currentData: T,
  optimisticUpdate: (data: T) => T,
  apiCall: () => Promise<T>,
  onUpdate: (data: T) => void,
  onError?: (error: any, originalData: T) => void
): Promise<T> {
  // Apply optimistic update
  const optimisticData = optimisticUpdate(currentData);
  onUpdate(optimisticData);

  try {
    // Make API call
    const result = await apiCall();
    onUpdate(result);
    return result;
  } catch (error) {
    // Revert on error
    if (onError) {
      onError(error, currentData);
    } else {
      onUpdate(currentData);
    }
    throw error;
  }
}

/**
 * Polling helper
 */
export function createPollingHelper<T = any>(
  requestFn: () => Promise<T>,
  interval = 5000,
  options: {
    immediate?: boolean;
    maxAttempts?: number;
    onData?: (data: T) => void;
    onError?: (error: any) => void;
  } = {}
) {
  const { immediate = true, maxAttempts = Infinity, onData, onError } = options;
  
  let timeoutId: NodeJS.Timeout | null = null;
  let attempts = 0;
  let isRunning = false;

  const poll = async () => {
    if (!isRunning || attempts >= maxAttempts) return;

    try {
      const data = await requestFn();
      attempts = 0; // Reset on success
      if (onData) onData(data);
    } catch (error) {
      attempts++;
      if (onError) onError(error);
    }

    if (isRunning && attempts < maxAttempts) {
      timeoutId = setTimeout(poll, interval);
    }
  };

  return {
    start: () => {
      isRunning = true;
      attempts = 0;
      if (immediate) {
        poll();
      } else {
        timeoutId = setTimeout(poll, interval);
      }
    },

    stop: () => {
      isRunning = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }
    },

    isRunning: () => isRunning
  };
}

/**
 * Request queue for handling multiple simultaneous requests
 */
export class RequestQueue {
  private queue: Array<() => Promise<any>> = [];
  private processing = false;
  private concurrency: number;

  constructor(concurrency = 3) {
    this.concurrency = concurrency;
  }

  async add<T>(requestFn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          const result = await requestFn();
          resolve(result);
        } catch (error) {
          reject(error);
        }
      });

      if (!this.processing) {
        this.process();
      }
    });
  }

  private async process(): Promise<void> {
    if (this.processing || this.queue.length === 0) return;
    
    this.processing = true;

    while (this.queue.length > 0) {
      const batch = this.queue.splice(0, this.concurrency);
      await Promise.allSettled(batch.map(fn => fn()));
    }

    this.processing = false;
  }
}

// Global request queue
export const requestQueue = new RequestQueue();