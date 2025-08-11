/**
 * Centralized validation utilities for Budget Famille v2.3 Frontend
 * Eliminates duplicate validation patterns across components
 */

import type { ValidationResult, ValidationError } from './types';

export class Validator {
  private errors: ValidationError[] = [];

  constructor(private data: Record<string, any>) {}

  field(fieldName: string): FieldValidator {
    return new FieldValidator(this.data[fieldName], fieldName, this);
  }

  addError(error: ValidationError): Validator {
    this.errors.push(error);
    return this;
  }

  getResult(): ValidationResult {
    return {
      isValid: this.errors.length === 0,
      errors: this.errors
    };
  }

  static validate(data: Record<string, any>): Validator {
    return new Validator(data);
  }
}

export class FieldValidator {
  constructor(
    private value: any,
    private fieldName: string,
    private validator: Validator
  ) {}

  required(message?: string): FieldValidator {
    if (this.value === null || this.value === undefined || this.value === '') {
      this.validator.addError({
        field: this.fieldName,
        message: message || `${this.fieldName} est requis`,
        code: 'REQUIRED'
      });
    }
    return this;
  }

  string(message?: string): FieldValidator {
    if (this.value !== null && this.value !== undefined && typeof this.value !== 'string') {
      this.validator.addError({
        field: this.fieldName,
        message: message || `${this.fieldName} doit être une chaîne de caractères`,
        code: 'TYPE_STRING',
        value: this.value
      });
    }
    return this;
  }

  number(message?: string) {
    if (this.value !== null && this.value !== undefined) {
      const num = Number(this.value);
      if (isNaN(num)) {
        this.validator.addError({
          field: this.fieldName,
          message: message || `${this.fieldName} doit être un nombre`,
          code: 'TYPE_NUMBER',
          value: this.value
        });
      }
    }
    return this;
  }

  min(minValue: number, message?: string) {
    if (this.value !== null && this.value !== undefined) {
      const num = Number(this.value);
      if (!isNaN(num) && num < minValue) {
        this.validator.addError({
          field: this.fieldName,
          message: message || `${this.fieldName} doit être au moins ${minValue}`,
          code: 'MIN_VALUE',
          value: this.value
        });
      }
    }
    return this;
  }

  max(maxValue: number, message?: string) {
    if (this.value !== null && this.value !== undefined) {
      const num = Number(this.value);
      if (!isNaN(num) && num > maxValue) {
        this.validator.addError({
          field: this.fieldName,
          message: message || `${this.fieldName} doit être au maximum ${maxValue}`,
          code: 'MAX_VALUE',
          value: this.value
        });
      }
    }
    return this;
  }

  minLength(minLength: number, message?: string) {
    if (this.value && typeof this.value === 'string' && this.value.length < minLength) {
      this.validator.addError({
        field: this.fieldName,
        message: message || `${this.fieldName} doit faire au moins ${minLength} caractères`,
        code: 'MIN_LENGTH',
        value: this.value
      });
    }
    return this;
  }

  maxLength(maxLength: number, message?: string) {
    if (this.value && typeof this.value === 'string' && this.value.length > maxLength) {
      this.validator.addError({
        field: this.fieldName,
        message: message || `${this.fieldName} doit faire au maximum ${maxLength} caractères`,
        code: 'MAX_LENGTH',
        value: this.value
      });
    }
    return this;
  }

  email(message?: string) {
    if (this.value && typeof this.value === 'string') {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(this.value)) {
        this.validator.addError({
          field: this.fieldName,
          message: message || `${this.fieldName} doit être une adresse email valide`,
          code: 'INVALID_EMAIL',
          value: this.value
        });
      }
    }
    return this;
  }

  date(message?: string) {
    if (this.value && typeof this.value === 'string') {
      const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
      if (!dateRegex.test(this.value) || isNaN(Date.parse(this.value))) {
        this.validator.addError({
          field: this.fieldName,
          message: message || `${this.fieldName} doit être une date valide (YYYY-MM-DD)`,
          code: 'INVALID_DATE',
          value: this.value
        });
      }
    }
    return this;
  }

  month(message?: string) {
    if (this.value && typeof this.value === 'string') {
      const monthRegex = /^\d{4}-\d{2}$/;
      if (!monthRegex.test(this.value)) {
        this.validator.addError({
          field: this.fieldName,
          message: message || `${this.fieldName} doit être au format YYYY-MM`,
          code: 'INVALID_MONTH',
          value: this.value
        });
      } else {
        const [year, month] = this.value.split('-').map(Number);
        if (month < 1 || month > 12) {
          this.validator.addError({
            field: this.fieldName,
            message: message || `${this.fieldName} doit être un mois valide (01-12)`,
            code: 'INVALID_MONTH',
            value: this.value
          });
        }
      }
    }
    return this;
  }

  percentage(message?: string) {
    if (this.value !== null && this.value !== undefined) {
      const num = Number(this.value);
      if (isNaN(num) || num < 0 || num > 100) {
        this.validator.addError({
          field: this.fieldName,
          message: message || `${this.fieldName} doit être un pourcentage entre 0 et 100`,
          code: 'INVALID_PERCENTAGE',
          value: this.value
        });
      }
    }
    return this;
  }

  currency(message?: string) {
    if (this.value !== null && this.value !== undefined) {
      const num = Number(this.value);
      if (isNaN(num) || Math.abs(num) > 1000000) {
        this.validator.addError({
          field: this.fieldName,
          message: message || `${this.fieldName} doit être un montant valide`,
          code: 'INVALID_CURRENCY',
          value: this.value
        });
      }
    }
    return this;
  }

  oneOf(values: any[], message?: string) {
    if (this.value !== null && this.value !== undefined && !values.includes(this.value)) {
      this.validator.addError({
        field: this.fieldName,
        message: message || `${this.fieldName} doit être l'une des valeurs suivantes: ${values.join(', ')}`,
        code: 'INVALID_CHOICE',
        value: this.value
      });
    }
    return this;
  }

  custom(validatorFn: (value: any) => boolean | string, code = 'CUSTOM_VALIDATION') {
    if (this.value !== null && this.value !== undefined) {
      const result = validatorFn(this.value);
      if (result !== true) {
        this.validator.addError({
          field: this.fieldName,
          message: typeof result === 'string' ? result : `${this.fieldName} n'est pas valide`,
          code,
          value: this.value
        });
      }
    }
    return this;
  }
}

// Specific validation functions
export function validateTransaction(transaction: Record<string, any>): ValidationResult {
  return Validator.validate(transaction)
    .field('date_op').required().date()
    .field('label').required().string().minLength(1).maxLength(500)
    .field('amount').required().number().currency()
    .field('category').string().maxLength(100)
    .field('account_label').string().maxLength(100)
    .getResult();
}

export function validateBudgetConfig(config: Record<string, any>): ValidationResult {
  return Validator.validate(config)
    .field('member1').required().string().minLength(1).maxLength(50)
    .field('member2').required().string().minLength(1).maxLength(50)
    .field('rev1').required().number().min(0)
    .field('rev2').required().number().min(0)
    .field('split_mode').required().oneOf(['revenus', 'manuel', '50/50'])
    .field('split1').number().percentage()
    .field('split2').number().percentage()
    .getResult();
}

export function validateFixedLine(fixedLine: Record<string, any>): ValidationResult {
  return Validator.validate(fixedLine)
    .field('label').required().string().minLength(1).maxLength(200)
    .field('amount').required().number().min(0).currency()
    .field('freq').required().oneOf(['mensuelle', 'trimestrielle', 'annuelle'])
    .field('split_mode').required().oneOf(['clé', '50/50', 'm1', 'm2', 'manuel'])
    .getResult();
}

export function validateProvision(provision: Record<string, any>): ValidationResult {
  return Validator.validate(provision)
    .field('name').required().string().minLength(1).maxLength(100)
    .field('percentage').required().number().percentage()
    .field('base_calculation').required().oneOf(['total', 'member1', 'member2', 'fixed'])
    .field('split_mode').required().oneOf(['key', '50/50', 'custom', '100/0', '0/100'])
    .getResult();
}

export function validateDateRange(startDate?: string, endDate?: string): ValidationResult {
  const validator = Validator.validate({ startDate, endDate });
  
  if (startDate) {
    validator.field('startDate').date();
  }
  
  if (endDate) {
    validator.field('endDate').date();
  }
  
  // Check date range logic
  if (startDate && endDate && startDate > endDate) {
    validator.addError({
      field: 'dateRange',
      message: 'La date de début doit être antérieure à la date de fin',
      code: 'INVALID_DATE_RANGE'
    });
  }
  
  return validator.getResult();
}

export function validateFileUpload(file: File, maxSizeMB = 10, allowedTypes = ['text/csv']): ValidationResult {
  const validator = Validator.validate({ file });
  
  if (!file) {
    validator.addError({
      field: 'file',
      message: 'Aucun fichier sélectionné',
      code: 'NO_FILE'
    });
    return validator.getResult();
  }
  
  // Check file size
  const maxSizeBytes = maxSizeMB * 1024 * 1024;
  if (file.size > maxSizeBytes) {
    validator.addError({
      field: 'file',
      message: `Le fichier est trop volumineux (maximum ${maxSizeMB}MB)`,
      code: 'FILE_TOO_LARGE',
      value: file.size
    });
  }
  
  // Check file type
  if (!allowedTypes.includes(file.type)) {
    validator.addError({
      field: 'file',
      message: `Type de fichier non supporté. Types autorisés: ${allowedTypes.join(', ')}`,
      code: 'INVALID_FILE_TYPE',
      value: file.type
    });
  }
  
  return validator.getResult();
}

// Utility functions
export function isValid(validationResult: ValidationResult): boolean {
  return validationResult.isValid;
}

export function getFirstError(validationResult: ValidationResult): ValidationError | undefined {
  return validationResult.errors[0];
}

export function getErrorsForField(validationResult: ValidationResult, fieldName: string): ValidationError[] {
  return validationResult.errors.filter(error => error.field === fieldName);
}

export function getErrorMessage(validationResult: ValidationResult, fieldName?: string): string {
  if (fieldName) {
    const fieldError = getErrorsForField(validationResult, fieldName)[0];
    return fieldError?.message || '';
  }
  return getFirstError(validationResult)?.message || '';
}

export function hasError(validationResult: ValidationResult, fieldName: string): boolean {
  return getErrorsForField(validationResult, fieldName).length > 0;
}

// React hook utilities
export function useValidation<T extends Record<string, any>>(
  validationFn: (data: T) => ValidationResult
) {
  return (data: T) => {
    const result = validationFn(data);
    
    // Convert to format suitable for form libraries
    const fieldErrors = result.errors.reduce((acc, error) => {
      if (!acc[error.field]) {
        acc[error.field] = [];
      }
      acc[error.field].push(error.message);
      return acc;
    }, {} as Record<string, string[]>);
    
    return {
      isValid: result.isValid,
      errors: fieldErrors,
      firstError: getFirstError(result)?.message,
      rawErrors: result.errors
    };
  };
}

// Real-time validation
export function createRealTimeValidator<T extends Record<string, any>>(
  validationFn: (data: T) => ValidationResult
) {
  let debounceTimer: NodeJS.Timeout;
  
  return (data: T, callback: (result: ValidationResult) => void, delay = 500) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const result = validationFn(data);
      callback(result);
    }, delay);
  };
}

// Common validation rules
export const VALIDATION_RULES = {
  REQUIRED: (message?: string) => (value: any) => {
    if (value === null || value === undefined || value === '') {
      return message || 'Ce champ est requis';
    }
    return true;
  },
  
  MIN_LENGTH: (minLength: number, message?: string) => (value: string) => {
    if (value && value.length < minLength) {
      return message || `Minimum ${minLength} caractères requis`;
    }
    return true;
  },
  
  MAX_LENGTH: (maxLength: number, message?: string) => (value: string) => {
    if (value && value.length > maxLength) {
      return message || `Maximum ${maxLength} caractères autorisés`;
    }
    return true;
  },
  
  EMAIL: (message?: string) => (value: string) => {
    if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      return message || 'Adresse email invalide';
    }
    return true;
  },
  
  POSITIVE_NUMBER: (message?: string) => (value: number) => {
    const num = Number(value);
    if (isNaN(num) || num < 0) {
      return message || 'Doit être un nombre positif';
    }
    return true;
  },
  
  PERCENTAGE: (message?: string) => (value: number) => {
    const num = Number(value);
    if (isNaN(num) || num < 0 || num > 100) {
      return message || 'Doit être entre 0 et 100%';
    }
    return true;
  }
} as const;