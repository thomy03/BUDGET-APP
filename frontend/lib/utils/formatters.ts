/**
 * Centralized formatting utilities for Budget Famille v2.3 Frontend
 * Eliminates duplicate formatting patterns across components
 */

import type { FormatOptions } from './types';

/**
 * Format currency amount with French formatting
 */
export function formatCurrency(
  amount: number | string,
  options: FormatOptions = {}
): string {
  const {
    locale = 'fr-FR',
    currency = 'EUR',
    decimals = 2,
    compact = false,
    showSymbol = true
  } = options;

  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
  
  if (isNaN(numAmount)) {
    return showSymbol ? `0,00 €` : '0,00';
  }

  try {
    const formatter = new Intl.NumberFormat(locale, {
      style: showSymbol ? 'currency' : 'decimal',
      currency: showSymbol ? currency : undefined,
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
      notation: compact ? 'compact' : 'standard'
    });

    return formatter.format(numAmount);
  } catch (error) {
    // Fallback formatting
    const formatted = numAmount.toFixed(decimals).replace('.', ',');
    const parts = formatted.split(',');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return showSymbol ? `${parts.join(',')} €` : parts.join(',');
  }
}

/**
 * Format percentage with French formatting
 */
export function formatPercentage(
  value: number | string,
  decimals = 1
): string {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(numValue)) {
    return '0,0 %';
  }

  try {
    return new Intl.NumberFormat('fr-FR', {
      style: 'percent',
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(numValue / 100);
  } catch (error) {
    return `${numValue.toFixed(decimals).replace('.', ',')} %`;
  }
}

/**
 * Format date with various French formats
 */
export function formatDate(
  date: Date | string,
  format: 'short' | 'long' | 'relative' | 'month' | 'year' = 'short'
): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  if (isNaN(dateObj.getTime())) {
    return 'Date invalide';
  }

  const now = new Date();
  
  try {
    switch (format) {
      case 'short':
        return dateObj.toLocaleDateString('fr-FR');
      
      case 'long':
        return dateObj.toLocaleDateString('fr-FR', {
          weekday: 'long',
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        });
      
      case 'month':
        return dateObj.toLocaleDateString('fr-FR', {
          year: 'numeric',
          month: 'long'
        });
      
      case 'year':
        return dateObj.getFullYear().toString();
      
      case 'relative':
        const diffTime = now.getTime() - dateObj.getTime();
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return "Aujourd'hui";
        if (diffDays === 1) return 'Hier';
        if (diffDays === -1) return 'Demain';
        if (diffDays > 1 && diffDays <= 7) return `Il y a ${diffDays} jours`;
        if (diffDays < -1 && diffDays >= -7) return `Dans ${Math.abs(diffDays)} jours`;
        
        return dateObj.toLocaleDateString('fr-FR');
      
      default:
        return dateObj.toLocaleDateString('fr-FR');
    }
  } catch (error) {
    return dateObj.toLocaleDateString('fr-FR');
  }
}

/**
 * Format month string (YYYY-MM) for display
 */
export function formatMonthDisplay(monthStr: string): string {
  try {
    const [year, month] = monthStr.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1, 1);
    return date.toLocaleDateString('fr-FR', { year: 'numeric', month: 'long' });
  } catch (error) {
    return monthStr;
  }
}

/**
 * Format number with French formatting
 */
export function formatNumber(
  value: number | string,
  decimals = 0,
  compact = false
): string {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(numValue)) {
    return '0';
  }

  try {
    return new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
      notation: compact ? 'compact' : 'standard'
    }).format(numValue);
  } catch (error) {
    return numValue.toFixed(decimals).replace('.', ',');
  }
}

/**
 * Format file size in human readable format
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const base = 1024;
  const unitIndex = Math.floor(Math.log(bytes) / Math.log(base));
  const size = bytes / Math.pow(base, unitIndex);

  return `${size.toFixed(unitIndex === 0 ? 0 : 1).replace('.', ',')} ${units[unitIndex]}`;
}

/**
 * Format duration in human readable format
 */
export function formatDuration(seconds: number): string {
  if (seconds < 1) {
    return `${Math.round(seconds * 1000)} ms`;
  } else if (seconds < 60) {
    return `${seconds.toFixed(1).replace('.', ',')} s`;
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return secs > 0 ? `${minutes} min ${secs} s` : `${minutes} min`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.round((seconds % 3600) / 60);
    return minutes > 0 ? `${hours} h ${minutes} min` : `${hours} h`;
  }
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(text: string, maxLength: number, suffix = '...'): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - suffix.length) + suffix;
}

/**
 * Format text for display (capitalize, etc.)
 */
export function formatDisplayText(text: string, format: 'capitalize' | 'upper' | 'lower' | 'title' = 'capitalize'): string {
  if (!text) return '';

  switch (format) {
    case 'capitalize':
      return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
    case 'upper':
      return text.toUpperCase();
    case 'lower':
      return text.toLowerCase();
    case 'title':
      return text.replace(/\w\S*/g, (txt) => 
        txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
      );
    default:
      return text;
  }
}

/**
 * Format array as readable list
 */
export function formatList(
  items: string[],
  conjunction: 'et' | 'ou' = 'et',
  limit?: number
): string {
  if (!items || items.length === 0) return '';
  
  let displayItems = limit ? items.slice(0, limit) : items;
  
  if (displayItems.length === 1) {
    return displayItems[0];
  } else if (displayItems.length === 2) {
    return `${displayItems[0]} ${conjunction} ${displayItems[1]}`;
  } else {
    const lastItem = displayItems.pop();
    const result = `${displayItems.join(', ')} ${conjunction} ${lastItem}`;
    
    if (limit && items.length > limit) {
      const remaining = items.length - limit;
      return `${result} ${conjunction} ${remaining} autre${remaining > 1 ? 's' : ''}`;
    }
    
    return result;
  }
}

/**
 * Format validation errors for display
 */
export function formatValidationErrors(errors: Array<{ field: string; message: string }>): string {
  if (!errors || errors.length === 0) return '';
  
  if (errors.length === 1) {
    return errors[0].message;
  }
  
  return errors.map(error => `• ${error.message}`).join('\n');
}

/**
 * Format boolean for display
 */
export function formatBoolean(value: boolean, format: 'oui-non' | 'vrai-faux' | 'actif-inactif' = 'oui-non'): string {
  switch (format) {
    case 'oui-non':
      return value ? 'Oui' : 'Non';
    case 'vrai-faux':
      return value ? 'Vrai' : 'Faux';
    case 'actif-inactif':
      return value ? 'Actif' : 'Inactif';
    default:
      return value ? 'Oui' : 'Non';
  }
}

/**
 * Format phone number (French format)
 */
export function formatPhoneNumber(phone: string): string {
  const cleaned = phone.replace(/\D/g, '');
  
  if (cleaned.length === 10) {
    return cleaned.replace(/(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/, '$1 $2 $3 $4 $5');
  } else if (cleaned.length === 9 && cleaned.startsWith('0')) {
    return '0' + cleaned.substring(1).replace(/(\d{1})(\d{2})(\d{2})(\d{2})(\d{2})/, '$1 $2 $3 $4 $5');
  }
  
  return phone;
}

/**
 * Format credit card number (masked)
 */
export function formatCreditCard(cardNumber: string, showLast = 4): string {
  const cleaned = cardNumber.replace(/\D/g, '');
  const masked = cleaned.substring(0, cleaned.length - showLast).replace(/\d/g, '*');
  const visible = cleaned.substring(cleaned.length - showLast);
  
  const fullMasked = masked + visible;
  return fullMasked.replace(/(.{4})/g, '$1 ').trim();
}

/**
 * Format address for display
 */
export function formatAddress(address: {
  street?: string;
  city?: string;
  postalCode?: string;
  country?: string;
}, format: 'single-line' | 'multi-line' = 'single-line'): string {
  const parts = [
    address.street,
    address.postalCode && address.city ? `${address.postalCode} ${address.city}` : address.city,
    address.country
  ].filter(Boolean);
  
  return format === 'single-line' ? parts.join(', ') : parts.join('\n');
}

/**
 * Parse and format user input currency
 */
export function parseCurrencyInput(input: string): number {
  if (!input) return 0;
  
  // Remove currency symbols, spaces, and convert comma to dot
  const cleaned = input
    .replace(/[€$£¥]/g, '')
    .replace(/\s/g, '')
    .replace(/,/g, '.');
  
  const parsed = parseFloat(cleaned);
  return isNaN(parsed) ? 0 : parsed;
}

/**
 * Format currency input for forms (keep numeric format)
 */
export function formatCurrencyInput(value: number | string): string {
  const numValue = typeof value === 'string' ? parseCurrencyInput(value) : value;
  return numValue === 0 ? '' : numValue.toString().replace('.', ',');
}

/**
 * Create format utilities object for specific component use
 */
export function createFormatters(options: Partial<FormatOptions> = {}) {
  return {
    currency: (amount: number | string) => formatCurrency(amount, options),
    percentage: (value: number | string, decimals?: number) => formatPercentage(value, decimals),
    date: (date: Date | string, format?: 'short' | 'long' | 'relative' | 'month' | 'year') => formatDate(date, format),
    number: (value: number | string, decimals?: number, compact?: boolean) => formatNumber(value, decimals, compact)
  };
}