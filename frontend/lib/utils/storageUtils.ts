/**
 * Centralized storage utilities for Budget Famille v2.3 Frontend
 * Eliminates duplicate storage patterns across components
 */

/**
 * Safe localStorage wrapper with error handling
 */
export class SafeStorage {
  private isAvailable: boolean;

  constructor(private storage: Storage = localStorage) {
    this.isAvailable = this.checkAvailability();
  }

  private checkAvailability(): boolean {
    try {
      const test = '__storage_test__';
      this.storage.setItem(test, test);
      this.storage.removeItem(test);
      return true;
    } catch {
      return false;
    }
  }

  set<T>(key: string, value: T): boolean {
    if (!this.isAvailable) return false;

    try {
      const serializedValue = JSON.stringify({
        value,
        timestamp: Date.now(),
        type: typeof value
      });
      this.storage.setItem(key, serializedValue);
      return true;
    } catch (error) {
      console.warn(`Failed to save to ${this.storage.constructor.name}:`, error);
      return false;
    }
  }

  get<T>(key: string, defaultValue?: T): T | undefined {
    if (!this.isAvailable) return defaultValue;

    try {
      const item = this.storage.getItem(key);
      if (!item) return defaultValue;

      const parsed = JSON.parse(item);
      return parsed.value as T;
    } catch (error) {
      console.warn(`Failed to read from ${this.storage.constructor.name}:`, error);
      return defaultValue;
    }
  }

  remove(key: string): boolean {
    if (!this.isAvailable) return false;

    try {
      this.storage.removeItem(key);
      return true;
    } catch (error) {
      console.warn(`Failed to remove from ${this.storage.constructor.name}:`, error);
      return false;
    }
  }

  clear(): boolean {
    if (!this.isAvailable) return false;

    try {
      this.storage.clear();
      return true;
    } catch (error) {
      console.warn(`Failed to clear ${this.storage.constructor.name}:`, error);
      return false;
    }
  }

  has(key: string): boolean {
    if (!this.isAvailable) return false;
    return this.storage.getItem(key) !== null;
  }

  keys(): string[] {
    if (!this.isAvailable) return [];

    try {
      return Object.keys(this.storage);
    } catch {
      return [];
    }
  }

  size(): number {
    return this.keys().length;
  }

  getWithMetadata<T>(key: string): {
    value: T | undefined;
    timestamp: number | undefined;
    type: string | undefined;
  } | null {
    if (!this.isAvailable) return null;

    try {
      const item = this.storage.getItem(key);
      if (!item) return null;

      const parsed = JSON.parse(item);
      return {
        value: parsed.value,
        timestamp: parsed.timestamp,
        type: parsed.type
      };
    } catch {
      return null;
    }
  }
}

// Global instances
export const localStorage = new SafeStorage(window?.localStorage);
export const sessionStorage = new SafeStorage(window?.sessionStorage);

/**
 * Cache with expiration support
 */
export class ExpiringCache extends SafeStorage {
  constructor(storage: Storage = window?.localStorage, private prefix = 'cache_') {
    super(storage);
  }

  setWithExpiration<T>(key: string, value: T, expirationMs: number): boolean {
    const expirationTime = Date.now() + expirationMs;
    return this.set(`${this.prefix}${key}`, {
      value,
      expiration: expirationTime
    });
  }

  getIfNotExpired<T>(key: string, defaultValue?: T): T | undefined {
    const cached = this.get<{ value: T; expiration: number }>(`${this.prefix}${key}`);
    
    if (!cached) return defaultValue;

    if (Date.now() > cached.expiration) {
      this.remove(`${this.prefix}${key}`);
      return defaultValue;
    }

    return cached.value;
  }

  removeExpired(): number {
    let removed = 0;
    const keys = this.keys().filter(key => key.startsWith(this.prefix));

    keys.forEach(key => {
      const cached = this.get<{ expiration: number }>(key);
      if (cached && Date.now() > cached.expiration) {
        this.remove(key);
        removed++;
      }
    });

    return removed;
  }

  clearCache(): boolean {
    const keys = this.keys().filter(key => key.startsWith(this.prefix));
    let success = true;

    keys.forEach(key => {
      if (!this.remove(key)) {
        success = false;
      }
    });

    return success;
  }
}

// Global cache instance
export const cache = new ExpiringCache();

/**
 * User preferences storage
 */
export class UserPreferences {
  private readonly PREFERENCES_KEY = 'user_preferences';
  private storage: SafeStorage;

  constructor(useSession = false) {
    this.storage = useSession ? sessionStorage : localStorage;
  }

  private getPreferences(): Record<string, any> {
    return this.storage.get(this.PREFERENCES_KEY, {});
  }

  private savePreferences(preferences: Record<string, any>): boolean {
    return this.storage.set(this.PREFERENCES_KEY, preferences);
  }

  get<T>(key: string, defaultValue?: T): T | undefined {
    const preferences = this.getPreferences();
    return preferences[key] !== undefined ? preferences[key] : defaultValue;
  }

  set<T>(key: string, value: T): boolean {
    const preferences = this.getPreferences();
    preferences[key] = value;
    return this.savePreferences(preferences);
  }

  remove(key: string): boolean {
    const preferences = this.getPreferences();
    delete preferences[key];
    return this.savePreferences(preferences);
  }

  clear(): boolean {
    return this.storage.remove(this.PREFERENCES_KEY);
  }

  getAll(): Record<string, any> {
    return this.getPreferences();
  }

  setMultiple(values: Record<string, any>): boolean {
    const preferences = this.getPreferences();
    Object.assign(preferences, values);
    return this.savePreferences(preferences);
  }
}

// Global preferences instance
export const userPreferences = new UserPreferences();

/**
 * Form data persistence
 */
export class FormPersistence {
  private storage: SafeStorage;

  constructor(useSession = true) {
    this.storage = useSession ? sessionStorage : localStorage;
  }

  saveFormData(formId: string, data: Record<string, any>): boolean {
    const key = `form_${formId}`;
    return this.storage.set(key, {
      data,
      savedAt: Date.now()
    });
  }

  loadFormData(formId: string): Record<string, any> | null {
    const key = `form_${formId}`;
    const saved = this.storage.get<{
      data: Record<string, any>;
      savedAt: number;
    }>(key);

    if (!saved) return null;

    // Check if data is older than 1 hour
    if (Date.now() - saved.savedAt > 60 * 60 * 1000) {
      this.clearFormData(formId);
      return null;
    }

    return saved.data;
  }

  clearFormData(formId: string): boolean {
    const key = `form_${formId}`;
    return this.storage.remove(key);
  }

  hasFormData(formId: string): boolean {
    return this.loadFormData(formId) !== null;
  }

  clearAllFormData(): boolean {
    const keys = this.storage.keys().filter(key => key.startsWith('form_'));
    let success = true;

    keys.forEach(key => {
      if (!this.storage.remove(key)) {
        success = false;
      }
    });

    return success;
  }
}

// Global form persistence instance
export const formPersistence = new FormPersistence();

/**
 * Recent items storage
 */
export class RecentItems<T> {
  private storage: SafeStorage;
  private readonly key: string;
  private readonly maxItems: number;

  constructor(
    key: string,
    maxItems = 10,
    useSession = false
  ) {
    this.storage = useSession ? sessionStorage : localStorage;
    this.key = `recent_${key}`;
    this.maxItems = maxItems;
  }

  private getItems(): T[] {
    return this.storage.get<T[]>(this.key, []);
  }

  add(item: T, uniqueField?: keyof T): boolean {
    const items = this.getItems();
    
    // Remove existing item if uniqueField is provided
    if (uniqueField) {
      const existingIndex = items.findIndex(existing => 
        existing[uniqueField] === item[uniqueField]
      );
      if (existingIndex !== -1) {
        items.splice(existingIndex, 1);
      }
    }

    // Add to beginning
    items.unshift(item);

    // Limit to maxItems
    if (items.length > this.maxItems) {
      items.splice(this.maxItems);
    }

    return this.storage.set(this.key, items);
  }

  getAll(): T[] {
    return this.getItems();
  }

  remove(predicate: (item: T) => boolean): boolean {
    const items = this.getItems();
    const filteredItems = items.filter(item => !predicate(item));
    return this.storage.set(this.key, filteredItems);
  }

  clear(): boolean {
    return this.storage.remove(this.key);
  }

  size(): number {
    return this.getItems().length;
  }
}

/**
 * Theme storage
 */
export class ThemeStorage {
  private readonly THEME_KEY = 'app_theme';
  private storage: SafeStorage;

  constructor() {
    this.storage = localStorage; // Always use localStorage for theme
  }

  getTheme(): 'light' | 'dark' | 'system' {
    return this.storage.get(this.THEME_KEY, 'system');
  }

  setTheme(theme: 'light' | 'dark' | 'system'): boolean {
    return this.storage.set(this.THEME_KEY, theme);
  }

  getEffectiveTheme(): 'light' | 'dark' {
    const theme = this.getTheme();
    
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    
    return theme;
  }
}

// Global theme storage instance
export const themeStorage = new ThemeStorage();

/**
 * Authentication token storage
 */
export class AuthStorage {
  private readonly TOKEN_KEY = 'auth_token';
  private readonly TOKEN_TYPE_KEY = 'token_type';
  private readonly USERNAME_KEY = 'username';
  private readonly EXPIRY_KEY = 'token_expiry';
  
  private storage: SafeStorage;

  constructor(useSession = false) {
    this.storage = useSession ? sessionStorage : localStorage;
  }

  setToken(token: string, tokenType = 'Bearer', expiryMs?: number): boolean {
    const success = this.storage.set(this.TOKEN_KEY, token) &&
                   this.storage.set(this.TOKEN_TYPE_KEY, tokenType);
    
    if (expiryMs) {
      const expiryTime = Date.now() + expiryMs;
      this.storage.set(this.EXPIRY_KEY, expiryTime);
    }

    return success;
  }

  getToken(): string | undefined {
    // Check expiry first
    const expiry = this.storage.get<number>(this.EXPIRY_KEY);
    if (expiry && Date.now() > expiry) {
      this.clearAuth();
      return undefined;
    }

    return this.storage.get(this.TOKEN_KEY);
  }

  getTokenType(): string {
    return this.storage.get(this.TOKEN_TYPE_KEY, 'Bearer');
  }

  getAuthHeader(): string | undefined {
    const token = this.getToken();
    if (!token) return undefined;
    
    const tokenType = this.getTokenType();
    return `${tokenType} ${token}`;
  }

  setUsername(username: string): boolean {
    return this.storage.set(this.USERNAME_KEY, username);
  }

  getUsername(): string | undefined {
    return this.storage.get(this.USERNAME_KEY);
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  getTokenExpiry(): Date | undefined {
    const expiry = this.storage.get<number>(this.EXPIRY_KEY);
    return expiry ? new Date(expiry) : undefined;
  }

  isTokenExpired(): boolean {
    const expiry = this.getTokenExpiry();
    return expiry ? Date.now() > expiry.getTime() : false;
  }

  clearAuth(): boolean {
    return this.storage.remove(this.TOKEN_KEY) &&
           this.storage.remove(this.TOKEN_TYPE_KEY) &&
           this.storage.remove(this.USERNAME_KEY) &&
           this.storage.remove(this.EXPIRY_KEY);
  }
}

// Global auth storage instance
export const authStorage = new AuthStorage();

/**
 * App state persistence
 */
export class AppStatePersistence {
  private readonly STATE_KEY = 'app_state';
  private storage: SafeStorage;

  constructor(useSession = false) {
    this.storage = useSession ? sessionStorage : localStorage;
  }

  saveState(state: Record<string, any>): boolean {
    return this.storage.set(this.STATE_KEY, {
      ...state,
      savedAt: Date.now()
    });
  }

  loadState(): Record<string, any> | null {
    const saved = this.storage.get<Record<string, any> & { savedAt: number }>(this.STATE_KEY);
    
    if (!saved) return null;

    // Remove savedAt timestamp from returned state
    const { savedAt, ...state } = saved;
    return state;
  }

  clearState(): boolean {
    return this.storage.remove(this.STATE_KEY);
  }

  hasState(): boolean {
    return this.storage.has(this.STATE_KEY);
  }

  getStateAge(): number | null {
    const saved = this.storage.get<{ savedAt: number }>(this.STATE_KEY);
    return saved ? Date.now() - saved.savedAt : null;
  }
}

// Global app state persistence instance
export const appStatePersistence = new AppStatePersistence();

/**
 * Utility functions
 */
export function getStorageUsage(): {
  localStorage: { used: number; available: number };
  sessionStorage: { used: number; available: number };
} {
  const getStorageSize = (storage: Storage): { used: number; available: number } => {
    try {
      let used = 0;
      for (let key in storage) {
        if (storage.hasOwnProperty(key)) {
          used += storage[key].length + key.length;
        }
      }

      // Estimate available space (most browsers have ~10MB limit)
      const estimatedLimit = 10 * 1024 * 1024; // 10MB in bytes
      return {
        used: used * 2, // UTF-16 uses 2 bytes per character
        available: estimatedLimit - (used * 2)
      };
    } catch {
      return { used: 0, available: 0 };
    }
  };

  return {
    localStorage: getStorageSize(window.localStorage),
    sessionStorage: getStorageSize(window.sessionStorage)
  };
}

export function cleanExpiredData(): { removed: number; errors: number } {
  let removed = 0;
  let errors = 0;

  try {
    // Clean expired cache
    removed += cache.removeExpired();
    
    // Clean old form data
    const formKeys = localStorage.keys().filter(key => key.startsWith('form_'));
    formKeys.forEach(key => {
      try {
        const data = localStorage.get<{ savedAt: number }>(key);
        if (data && Date.now() - data.savedAt > 60 * 60 * 1000) { // 1 hour
          if (localStorage.remove(key)) {
            removed++;
          } else {
            errors++;
          }
        }
      } catch {
        errors++;
      }
    });

  } catch {
    errors++;
  }

  return { removed, errors };
}

export function exportStorageData(): {
  localStorage: Record<string, any>;
  sessionStorage: Record<string, any>;
} {
  const exportStorage = (storage: SafeStorage): Record<string, any> => {
    const data: Record<string, any> = {};
    
    storage.keys().forEach(key => {
      data[key] = storage.get(key);
    });

    return data;
  };

  return {
    localStorage: exportStorage(localStorage),
    sessionStorage: exportStorage(sessionStorage)
  };
}