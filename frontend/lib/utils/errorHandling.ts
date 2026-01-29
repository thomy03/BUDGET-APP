/**
 * Centralized error handling utilities for Budget Famille v2.3 Frontend
 * Eliminates duplicate error handling patterns across components
 */

import { AxiosError } from 'axios';
import type { ErrorInfo, ApiResponse } from './types';

export class BudgetError extends Error {
  public code?: string;
  public type: 'network' | 'validation' | 'auth' | 'server' | 'client';
  public statusCode?: number;
  public details?: Record<string, unknown>;
  public timestamp: string;

  constructor(
    message: string,
    type: 'network' | 'validation' | 'auth' | 'server' | 'client' = 'client',
    code?: string,
    statusCode?: number,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'BudgetError';
    this.type = type;
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
    this.timestamp = new Date().toISOString();
  }

  toErrorInfo(): ErrorInfo {
    return {
      message: this.message,
      code: this.code,
      type: this.type,
      statusCode: this.statusCode,
      details: this.details,
      timestamp: this.timestamp
    };
  }
}

export function createErrorFromAxios(error: AxiosError): BudgetError {
  const status = error.response?.status;
  const data = error.response?.data as any;
  
  let message = 'Une erreur est survenue';
  let type: 'network' | 'validation' | 'auth' | 'server' | 'client' = 'server';
  let code = error.code;

  // Network errors
  if (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') {
    type = 'network';
    message = error.code === 'ECONNABORTED' 
      ? 'Délai de connexion dépassé'
      : 'Erreur réseau - Vérifiez votre connexion';
  }
  // HTTP status-based errors
  else if (status) {
    switch (status) {
      case 400:
        type = 'validation';
        message = 'Données invalides';
        if (data?.detail) message = data.detail;
        break;
      case 401:
        type = 'auth';
        message = 'Session expirée. Veuillez vous reconnecter.';
        break;
      case 403:
        type = 'auth';
        message = 'Accès refusé';
        break;
      case 404:
        type = 'client';
        message = 'Ressource introuvable';
        break;
      case 422:
        type = 'validation';
        message = 'Données de validation incorrectes';
        break;
      case 429:
        type = 'client';
        message = 'Trop de requêtes. Veuillez attendre un moment.';
        break;
      case 500:
      case 502:
      case 503:
      case 504:
        type = 'server';
        message = 'Erreur serveur - Veuillez réessayer plus tard';
        break;
      default:
        type = 'server';
        message = `Erreur HTTP ${status}`;
    }
    
    // Try to extract server message
    if (data?.detail && typeof data.detail === 'string') {
      message = data.detail;
    } else if (data?.message && typeof data.message === 'string') {
      message = data.message;
    } else if (data?.error && typeof data.error === 'string') {
      message = data.error;
    }
  }

  return new BudgetError(
    message,
    type,
    code,
    status,
    data
  );
}

export function handleError(error: unknown): ErrorInfo {
  if (error instanceof BudgetError) {
    return error.toErrorInfo();
  }
  
  if (error instanceof AxiosError) {
    return createErrorFromAxios(error).toErrorInfo();
  }
  
  if (error instanceof Error) {
    return {
      message: error.message,
      type: 'client',
      timestamp: new Date().toISOString()
    };
  }
  
  return {
    message: 'Une erreur inconnue est survenue',
    type: 'client',
    timestamp: new Date().toISOString()
  };
}

export function logError(error: unknown, context?: Record<string, unknown>) {
  const errorInfo = handleError(error);
  
  const logData = {
    ...errorInfo,
    context
  };
  
  // In development, log to console
  if (process.env.NODE_ENV === 'development') {
    console.error('🚨 Error occurred:', logData);
  }
  
  // In production, you might want to send to monitoring service
  // sendErrorToMonitoring(logData);
}

export function createErrorMessage(
  error: unknown,
  fallbackMessage = 'Une erreur est survenue'
): string {
  const errorInfo = handleError(error);
  return errorInfo.message || fallbackMessage;
}

export function isNetworkError(error: unknown): boolean {
  return handleError(error).type === 'network';
}

export function isAuthError(error: unknown): boolean {
  return handleError(error).type === 'auth';
}

export function isValidationError(error: unknown): boolean {
  return handleError(error).type === 'validation';
}

export function isServerError(error: unknown): boolean {
  return handleError(error).type === 'server';
}

export function shouldRetry(error: unknown): boolean {
  const errorInfo = handleError(error);

  // Retry on network errors and 5xx server errors
  return errorInfo.type === 'network' ||
         (errorInfo.statusCode !== undefined && errorInfo.statusCode >= 500);
}

export function getRetryDelay(attemptNumber: number): number {
  // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
  return Math.min(1000 * Math.pow(2, attemptNumber - 1), 30000);
}

export async function withRetry<T>(
  operation: () => Promise<T>,
  maxAttempts = 3,
  shouldRetryFn = shouldRetry
): Promise<T> {
  let lastError: unknown;
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      
      if (attempt === maxAttempts || !shouldRetryFn(error)) {
        throw error;
      }
      
      const delay = getRetryDelay(attempt);
      await new Promise(resolve => setTimeout(resolve, delay));
      
      logError(error, { attempt, maxAttempts, retrying: true });
    }
  }
  
  throw lastError;
}

export function safeAsync<T>(
  asyncFn: () => Promise<T>,
  defaultValue?: T
): Promise<T | typeof defaultValue> {
  return asyncFn().catch((error) => {
    logError(error);
    return defaultValue as T | typeof defaultValue;
  });
}

export function safe<T>(
  fn: () => T,
  defaultValue?: T
): T | typeof defaultValue {
  try {
    return fn();
  } catch (error) {
    logError(error);
    return defaultValue as T | typeof defaultValue;
  }
}

// React Hook utilities
export function useErrorHandler() {
  return (error: unknown, context?: Record<string, unknown>) => {
    logError(error, context);
    
    // You can add toast notifications here
    // toast.error(createErrorMessage(error));
  };
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error?: ErrorInfo;
}

export function createErrorBoundaryReducer() {
  return (state: ErrorBoundaryState, action: { type: 'ERROR' | 'RESET'; error?: unknown }) => {
    switch (action.type) {
      case 'ERROR':
        return {
          hasError: true,
          error: handleError(action.error)
        };
      case 'RESET':
        return {
          hasError: false,
          error: undefined
        };
      default:
        return state;
    }
  };
}

// Common error messages
export const ERROR_MESSAGES = {
  NETWORK: 'Erreur de connexion. Vérifiez votre connexion internet.',
  AUTH_REQUIRED: 'Authentification requise. Veuillez vous connecter.',
  AUTH_EXPIRED: 'Session expirée. Veuillez vous reconnecter.',
  PERMISSION_DENIED: 'Vous n\'avez pas les permissions nécessaires.',
  NOT_FOUND: 'La ressource demandée est introuvable.',
  VALIDATION_FAILED: 'Les données saisies ne sont pas valides.',
  SERVER_ERROR: 'Erreur serveur. Veuillez réessayer plus tard.',
  FILE_TOO_LARGE: 'Le fichier est trop volumineux.',
  FILE_INVALID: 'Le format de fichier n\'est pas supporté.',
  SAVE_FAILED: 'Erreur lors de la sauvegarde.',
  LOAD_FAILED: 'Erreur lors du chargement des données.',
  DELETE_FAILED: 'Erreur lors de la suppression.',
  UPDATE_FAILED: 'Erreur lors de la mise à jour.'
} as const;

export function createStandardError(messageKey: keyof typeof ERROR_MESSAGES): BudgetError {
  return new BudgetError(ERROR_MESSAGES[messageKey]);
}