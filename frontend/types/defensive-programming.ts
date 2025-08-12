/**
 * DEFENSIVE PROGRAMMING UTILITIES
 * 
 * This file contains TypeScript utilities and patterns to prevent runtime errors
 * caused by undefined/null property access. All components should follow these patterns.
 */

// Utility type to ensure props are defined
export type RequiredProps<T> = {
  [K in keyof T]-?: T[K];
};

// Safe array access utility
export function safeArray<T>(arr: T[] | undefined | null): T[] {
  return arr || [];
}

// Safe object property access
export function safeProp<T, K extends keyof T>(obj: T | undefined | null, key: K): T[K] | undefined {
  return obj?.[key];
}

// Safe map operation that always returns an array
export function safeMap<T, U>(
  arr: T[] | undefined | null, 
  mapper: (item: T, index: number) => U
): U[] {
  return safeArray(arr).map(mapper);
}

// Safe filter operation
export function safeFilter<T>(
  arr: T[] | undefined | null, 
  predicate: (item: T, index: number) => boolean
): T[] {
  return safeArray(arr).filter(predicate);
}

// Safe slice operation
export function safeSlice<T>(
  arr: T[] | undefined | null, 
  start?: number, 
  end?: number
): T[] {
  return safeArray(arr).slice(start, end);
}

// Component prop validator for critical props
export function validateRequiredProps<T extends Record<string, any>>(
  props: T,
  requiredKeys: (keyof T)[],
  componentName: string
): boolean {
  const missingProps = requiredKeys.filter(key => 
    props[key] === undefined || props[key] === null
  );
  
  if (missingProps.length > 0) {
    console.error(
      `${componentName}: Missing required props: ${missingProps.join(', ')}`
    );
    return false;
  }
  
  return true;
}

// Error boundary helper
export class ComponentError extends Error {
  constructor(
    message: string,
    public componentName: string,
    public props?: any
  ) {
    super(`${componentName}: ${message}`);
    this.name = 'ComponentError';
  }
}

// Type guard for expense types
export function isValidExpenseType(type: any): type is 'fixed' | 'variable' {
  return type === 'fixed' || type === 'variable';
}

// Safe enum access
export function getSafeEnumValue<T extends Record<string, any>>(
  enumObj: T,
  key: string | number | symbol,
  fallback: T[keyof T]
): T[keyof T] {
  return enumObj[key as keyof T] || fallback;
}

/**
 * CODING STANDARDS EXAMPLES:
 * 
 * ❌ UNSAFE:
 * items.map(item => ...)
 * data.users.filter(...)
 * config[type].label
 * 
 * ✅ SAFE:
 * safeMap(items, item => ...)
 * safeFilter(data?.users, ...)
 * getSafeEnumValue(typeConfig, type, defaultConfig).label
 */