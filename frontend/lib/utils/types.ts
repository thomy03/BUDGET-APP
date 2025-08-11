/**
 * Common types for utility functions
 */

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: {
    message: string;
    code?: string;
    details?: Record<string, unknown>;
  };
  meta?: Record<string, unknown>;
  timestamp: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

export interface ValidationError {
  field: string;
  message: string;
  code?: string;
  value?: any;
}

export interface ErrorInfo {
  message: string;
  code?: string;
  type?: 'network' | 'validation' | 'auth' | 'server' | 'client';
  statusCode?: number;
  details?: Record<string, unknown>;
  timestamp: string;
}

export interface FormatOptions {
  locale?: string;
  currency?: string;
  decimals?: number;
  compact?: boolean;
  showSymbol?: boolean;
}

export interface CalculationResult {
  value: number;
  formatted: string;
  metadata?: Record<string, unknown>;
}

export interface PaginationParams {
  page: number;
  limit: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface DateRange {
  startDate?: string;
  endDate?: string;
}

export interface LoadingState {
  isLoading: boolean;
  operation?: string;
  progress?: number;
}

export interface ToastOptions {
  type: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  message: string;
  duration?: number;
  persistent?: boolean;
  actions?: ToastAction[];
}

export interface ToastAction {
  label: string;
  action: () => void;
  style?: 'primary' | 'secondary';
}

export interface FormFieldProps {
  name: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  value?: any;
  onChange?: (value: any) => void;
}

// Budget-specific types
export interface TransactionData {
  id?: number;
  date_op: string;
  label: string;
  category: string;
  category_parent?: string;
  amount: number;
  account_label?: string;
  is_expense: boolean;
  exclude?: boolean;
  tags?: string[];
  month?: string;
}

export interface BudgetConfig {
  member1: string;
  member2: string;
  rev1: number;
  rev2: number;
  split_mode: 'revenus' | 'manuel' | '50/50';
  split1: number;
  split2: number;
}

export interface SplitResult {
  member1_amount: number;
  member2_amount: number;
  total_amount: number;
  split_percentage1: number;
  split_percentage2: number;
}