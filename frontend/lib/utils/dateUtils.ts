/**
 * Centralized date utilities for Budget Famille v2.3 Frontend
 * Eliminates duplicate date handling patterns across components
 */

/**
 * Get current date in YYYY-MM-DD format
 */
export function getCurrentDate(): string {
  return new Date().toISOString().split('T')[0] ?? '';
}

/**
 * Get current month in YYYY-MM format
 */
export function getCurrentMonth(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = (now.getMonth() + 1).toString().padStart(2, '0');
  return `${year}-${month}`;
}

/**
 * Get current year as number
 */
export function getCurrentYear(): number {
  return new Date().getFullYear();
}

/**
 * Convert date to month string (YYYY-MM)
 */
export function dateToMonth(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const year = dateObj.getFullYear();
  const month = (dateObj.getMonth() + 1).toString().padStart(2, '0');
  return `${year}-${month}`;
}

/**
 * Convert month string to first day of month
 */
export function monthToDate(monthStr: string): Date {
  const parts = monthStr.split('-').map(Number);
  const year = parts[0] ?? 2020;
  const month = parts[1] ?? 1;
  return new Date(year, month - 1, 1);
}

/**
 * Get month range (first and last day) from month string
 */
export function getMonthRange(monthStr: string): { startDate: Date; endDate: Date } {
  const parts = monthStr.split('-').map(Number);
  const year = parts[0] ?? 2020;
  const month = parts[1] ?? 1;
  const startDate = new Date(year, month - 1, 1);
  const endDate = new Date(year, month, 0); // Last day of the month
  return { startDate, endDate };
}

/**
 * Add months to a date
 */
export function addMonths(date: Date | string, months: number): Date {
  const dateObj = typeof date === 'string' ? new Date(date) : new Date(date);
  const newDate = new Date(dateObj);
  newDate.setMonth(newDate.getMonth() + months);
  return newDate;
}

/**
 * Add months to month string and return new month string
 */
export function addMonthsToMonth(monthStr: string, months: number): string {
  const date = monthToDate(monthStr);
  const newDate = addMonths(date, months);
  return dateToMonth(newDate);
}

/**
 * Get previous month
 */
export function getPreviousMonth(monthStr?: string): string {
  const currentMonth = monthStr || getCurrentMonth();
  return addMonthsToMonth(currentMonth, -1);
}

/**
 * Get next month
 */
export function getNextMonth(monthStr?: string): string {
  const currentMonth = monthStr || getCurrentMonth();
  return addMonthsToMonth(currentMonth, 1);
}

/**
 * Get array of month strings between two dates
 */
export function getMonthsBetween(startMonth: string, endMonth: string): string[] {
  const months: string[] = [];
  let current = startMonth;
  
  while (current <= endMonth) {
    months.push(current);
    current = getNextMonth(current);
  }
  
  return months;
}

/**
 * Get last N months including current month
 */
export function getLastNMonths(n: number, includeCurrentMonth = true): string[] {
  const months: string[] = [];
  let current = getCurrentMonth();
  
  if (!includeCurrentMonth) {
    current = getPreviousMonth(current);
  }
  
  for (let i = 0; i < n; i++) {
    months.unshift(current);
    current = getPreviousMonth(current);
  }
  
  return months;
}

/**
 * Get months for a specific year
 */
export function getMonthsForYear(year: number): string[] {
  const months: string[] = [];
  for (let month = 1; month <= 12; month++) {
    const monthStr = month.toString().padStart(2, '0');
    months.push(`${year}-${monthStr}`);
  }
  return months;
}

/**
 * Check if date is in the past
 */
export function isDateInPast(date: Date | string): boolean {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  dateObj.setHours(0, 0, 0, 0);
  return dateObj < today;
}

/**
 * Check if date is today
 */
export function isDateToday(date: Date | string): boolean {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const today = new Date();
  return dateObj.toDateString() === today.toDateString();
}

/**
 * Check if month is current month
 */
export function isCurrentMonth(monthStr: string): boolean {
  return monthStr === getCurrentMonth();
}

/**
 * Check if month is in the past
 */
export function isMonthInPast(monthStr: string): boolean {
  return monthStr < getCurrentMonth();
}

/**
 * Get difference in months between two month strings
 */
export function getMonthDifference(startMonth: string, endMonth: string): number {
  const startParts = startMonth.split('-').map(Number);
  const endParts = endMonth.split('-').map(Number);
  const startYear = startParts[0] ?? 0;
  const startMonthNum = startParts[1] ?? 0;
  const endYear = endParts[0] ?? 0;
  const endMonthNum = endParts[1] ?? 0;

  return (endYear - startYear) * 12 + (endMonthNum - startMonthNum);
}

/**
 * Get difference in days between two dates
 */
export function getDayDifference(startDate: Date | string, endDate: Date | string): number {
  const start = typeof startDate === 'string' ? new Date(startDate) : startDate;
  const end = typeof endDate === 'string' ? new Date(endDate) : endDate;
  
  const timeDiff = end.getTime() - start.getTime();
  return Math.ceil(timeDiff / (1000 * 3600 * 24));
}

/**
 * Validate date string format (YYYY-MM-DD)
 */
export function isValidDateString(dateStr: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    return false;
  }
  
  const date = new Date(dateStr);
  return date.toISOString().split('T')[0] === dateStr;
}

/**
 * Validate month string format (YYYY-MM)
 */
export function isValidMonthString(monthStr: string): boolean {
  if (!/^\d{4}-\d{2}$/.test(monthStr)) {
    return false;
  }

  const parts = monthStr.split('-').map(Number);
  const year = parts[0] ?? 0;
  const month = parts[1] ?? 0;
  return year >= 1900 && year <= 2100 && month >= 1 && month <= 12;
}

/**
 * Parse French date format (DD/MM/YYYY) to YYYY-MM-DD
 */
export function parseFrenchDate(frenchDate: string): string | null {
  const match = frenchDate.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!match) return null;

  const day = match[1] ?? '';
  const month = match[2] ?? '';
  const year = match[3] ?? '';
  const dayPadded = day.padStart(2, '0');
  const monthPadded = month.padStart(2, '0');

  const dateStr = `${year}-${monthPadded}-${dayPadded}`;
  return isValidDateString(dateStr) ? dateStr : null;
}

/**
 * Format date string to French format (DD/MM/YYYY)
 */
export function toFrenchDateFormat(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return '';
  
  const day = dateObj.getDate().toString().padStart(2, '0');
  const month = (dateObj.getMonth() + 1).toString().padStart(2, '0');
  const year = dateObj.getFullYear();
  
  return `${day}/${month}/${year}`;
}

/**
 * Get start and end of week for a given date
 */
export function getWeekRange(date: Date | string): { startDate: Date; endDate: Date } {
  const dateObj = typeof date === 'string' ? new Date(date) : new Date(date);
  
  const startDate = new Date(dateObj);
  const day = startDate.getDay();
  const diff = startDate.getDate() - day + (day === 0 ? -6 : 1); // Monday as first day
  startDate.setDate(diff);
  
  const endDate = new Date(startDate);
  endDate.setDate(startDate.getDate() + 6);
  
  return { startDate, endDate };
}

/**
 * Get quarter number for a given date
 */
export function getQuarter(date: Date | string): number {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return Math.floor((dateObj.getMonth() + 3) / 3);
}

/**
 * Get quarter string (YYYY-Q1, YYYY-Q2, etc.)
 */
export function getQuarterString(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const year = dateObj.getFullYear();
  const quarter = getQuarter(dateObj);
  return `${year}-Q${quarter}`;
}

/**
 * Get fiscal year (assuming fiscal year starts in April)
 */
export function getFiscalYear(date: Date | string, fiscalYearStartMonth = 4): number {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const year = dateObj.getFullYear();
  const month = dateObj.getMonth() + 1; // 1-based month
  
  return month >= fiscalYearStartMonth ? year : year - 1;
}

/**
 * Check if a year is a leap year
 */
export function isLeapYear(year: number): boolean {
  return (year % 4 === 0 && year % 100 !== 0) || (year % 400 === 0);
}

/**
 * Get number of days in a month
 */
export function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

/**
 * Get business days between two dates (excluding weekends)
 */
export function getBusinessDaysBetween(startDate: Date | string, endDate: Date | string): number {
  const start = typeof startDate === 'string' ? new Date(startDate) : new Date(startDate);
  const end = typeof endDate === 'string' ? new Date(endDate) : new Date(endDate);
  
  let count = 0;
  const current = new Date(start);
  
  while (current <= end) {
    const dayOfWeek = current.getDay();
    if (dayOfWeek !== 0 && dayOfWeek !== 6) { // Not Sunday (0) or Saturday (6)
      count++;
    }
    current.setDate(current.getDate() + 1);
  }
  
  return count;
}

/**
 * Create date range options for dropdowns
 */
export function createDateRangeOptions(): Array<{ label: string; value: string; startDate: string; endDate: string }> {
  const today = new Date();
  const currentMonth = getCurrentMonth();
  const toDateStr = (d: Date): string => d.toISOString().split('T')[0] ?? '';

  return [
    {
      label: 'Aujourd\'hui',
      value: 'today',
      startDate: getCurrentDate(),
      endDate: getCurrentDate()
    },
    {
      label: 'Cette semaine',
      value: 'this_week',
      startDate: toDateStr(getWeekRange(today).startDate),
      endDate: toDateStr(getWeekRange(today).endDate)
    },
    {
      label: 'Ce mois',
      value: 'this_month',
      startDate: toDateStr(getMonthRange(currentMonth).startDate),
      endDate: toDateStr(getMonthRange(currentMonth).endDate)
    },
    {
      label: 'Mois dernier',
      value: 'last_month',
      startDate: toDateStr(getMonthRange(getPreviousMonth()).startDate),
      endDate: toDateStr(getMonthRange(getPreviousMonth()).endDate)
    },
    {
      label: '3 derniers mois',
      value: 'last_3_months',
      startDate: toDateStr(getMonthRange(addMonthsToMonth(currentMonth, -2)).startDate),
      endDate: toDateStr(getMonthRange(currentMonth).endDate)
    },
    {
      label: 'Cette année',
      value: 'this_year',
      startDate: `${getCurrentYear()}-01-01`,
      endDate: `${getCurrentYear()}-12-31`
    }
  ];
}

/**
 * Format relative time (e.g., "il y a 2 heures")
 */
export function formatRelativeTime(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - dateObj.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return 'À l\'instant';
  } else if (diffMinutes < 60) {
    return `Il y a ${diffMinutes} minute${diffMinutes > 1 ? 's' : ''}`;
  } else if (diffHours < 24) {
    return `Il y a ${diffHours} heure${diffHours > 1 ? 's' : ''}`;
  } else if (diffDays < 30) {
    return `Il y a ${diffDays} jour${diffDays > 1 ? 's' : ''}`;
  } else {
    return dateObj.toLocaleDateString('fr-FR');
  }
}