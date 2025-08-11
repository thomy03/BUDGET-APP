/**
 * Utility modules for Budget Famille v2.3 Frontend
 * Centralized utilities to eliminate code duplication
 */

export * from './errorHandling';
export * from './validation';
export * from './formatters';
export * from './apiHelpers';
export * from './calculations';
export * from './dateUtils';
export * from './storageUtils';

// Re-export common types
export type {
  ApiResponse,
  ValidationResult,
  ErrorInfo,
  FormatOptions,
  CalculationResult
} from './types';