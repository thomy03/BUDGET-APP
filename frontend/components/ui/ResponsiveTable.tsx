'use client';

import React from 'react';
import { useIsMobile } from '../../hooks/useMediaQuery';

/**
 * Column definition for ResponsiveTable
 */
export interface TableColumn<T> {
  /** Unique key for the column */
  key: string;
  /** Header label */
  header: string;
  /** Function to render cell content */
  render: (item: T) => React.ReactNode;
  /** Optional: Show in mobile card view (default: true for first 3 columns) */
  showOnMobile?: boolean;
  /** Optional: Priority for mobile view (lower = more important) */
  mobilePriority?: number;
  /** Optional: Width class for the column */
  width?: string;
  /** Optional: Alignment */
  align?: 'left' | 'center' | 'right';
}

/**
 * Props for ResponsiveTable component
 */
export interface ResponsiveTableProps<T> {
  /** Data items to display */
  data: T[];
  /** Column definitions */
  columns: TableColumn<T>[];
  /** Key extractor for items */
  getKey: (item: T) => string | number;
  /** Optional: Empty state content */
  emptyContent?: React.ReactNode;
  /** Optional: Loading state */
  loading?: boolean;
  /** Optional: On row click handler */
  onRowClick?: (item: T) => void;
  /** Optional: Custom row className */
  rowClassName?: (item: T) => string;
  /** Optional: Show header on mobile (default: false) */
  showHeaderOnMobile?: boolean;
  /** Optional: Custom card renderer for mobile */
  mobileCardRenderer?: (item: T) => React.ReactNode;
}

/**
 * ResponsiveTable component
 * Renders as a table on desktop and as cards on mobile
 */
export function ResponsiveTable<T>({
  data,
  columns,
  getKey,
  emptyContent,
  loading = false,
  onRowClick,
  rowClassName,
  showHeaderOnMobile = false,
  mobileCardRenderer,
}: ResponsiveTableProps<T>) {
  const isMobile = useIsMobile();

  // Get columns to show on mobile (sorted by priority)
  const mobileColumns = columns
    .filter((col, index) => col.showOnMobile !== false && (col.showOnMobile || index < 3))
    .sort((a, b) => (a.mobilePriority ?? 99) - (b.mobilePriority ?? 99));

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-white rounded-xl p-4 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
            <div className="h-3 bg-gray-200 rounded w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        {emptyContent || 'Aucune donnée à afficher'}
      </div>
    );
  }

  // Mobile: Card view
  if (isMobile) {
    return (
      <div className="space-y-3">
        {data.map((item) => {
          // Use custom renderer if provided
          if (mobileCardRenderer) {
            return (
              <div key={getKey(item)} onClick={() => onRowClick?.(item)}>
                {mobileCardRenderer(item)}
              </div>
            );
          }

          return (
            <div
              key={getKey(item)}
              className={`bg-white rounded-xl p-4 shadow-sm border border-gray-100 ${
                onRowClick ? 'cursor-pointer active:bg-gray-50' : ''
              } ${rowClassName?.(item) || ''}`}
              onClick={() => onRowClick?.(item)}
            >
              {mobileColumns.map((col, index) => (
                <div
                  key={col.key}
                  className={`${index > 0 ? 'mt-2 pt-2 border-t border-gray-100' : ''} ${
                    col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : ''
                  }`}
                >
                  {showHeaderOnMobile && (
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">
                      {col.header}
                    </div>
                  )}
                  <div className={index === 0 ? 'font-medium text-gray-900' : 'text-sm text-gray-600'}>
                    {col.render(item)}
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    );
  }

  // Desktop: Table view
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider ${
                  col.width || ''
                } ${
                  col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                }`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {data.map((item) => (
            <tr
              key={getKey(item)}
              className={`hover:bg-gray-50 transition-colors ${
                onRowClick ? 'cursor-pointer' : ''
              } ${rowClassName?.(item) || ''}`}
              onClick={() => onRowClick?.(item)}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`px-4 py-3 ${col.width || ''} ${
                    col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                  }`}
                >
                  {col.render(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Utility to create a simple text column
 */
export function createTextColumn<T>(
  key: string,
  header: string,
  accessor: (item: T) => string | number | null | undefined,
  options?: Partial<TableColumn<T>>
): TableColumn<T> {
  return {
    key,
    header,
    render: (item) => <span>{accessor(item) ?? '-'}</span>,
    ...options,
  };
}

/**
 * Utility to create a currency column
 */
export function createCurrencyColumn<T>(
  key: string,
  header: string,
  accessor: (item: T) => number | null | undefined,
  options?: Partial<TableColumn<T>> & { colorize?: boolean }
): TableColumn<T> {
  const { colorize = false, ...rest } = options || {};

  return {
    key,
    header,
    render: (item) => {
      const value = accessor(item);
      if (value === null || value === undefined) return <span>-</span>;

      const formatted = new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'EUR',
      }).format(Math.abs(value));

      const prefix = value >= 0 ? '+' : '-';
      const className = colorize
        ? value >= 0
          ? 'text-green-600'
          : 'text-red-600'
        : '';

      return (
        <span className={`font-medium ${className}`}>
          {prefix}{formatted}
        </span>
      );
    },
    align: 'right',
    ...rest,
  };
}

/**
 * Utility to create a date column
 */
export function createDateColumn<T>(
  key: string,
  header: string,
  accessor: (item: T) => string | Date | null | undefined,
  options?: Partial<TableColumn<T>> & { format?: 'short' | 'medium' | 'long' }
): TableColumn<T> {
  const { format = 'short', ...rest } = options || {};

  const dateFormatOptions: Intl.DateTimeFormatOptions = {
    short: { day: '2-digit', month: 'short' },
    medium: { day: '2-digit', month: 'short', year: 'numeric' },
    long: { day: '2-digit', month: 'long', year: 'numeric' },
  }[format];

  return {
    key,
    header,
    render: (item) => {
      const value = accessor(item);
      if (!value) return <span>-</span>;

      const date = typeof value === 'string' ? new Date(value) : value;
      if (isNaN(date.getTime())) return <span>-</span>;

      return <span>{date.toLocaleDateString('fr-FR', dateFormatOptions)}</span>;
    },
    ...rest,
  };
}

/**
 * Utility to create a badge column
 */
export function createBadgeColumn<T>(
  key: string,
  header: string,
  accessor: (item: T) => string | string[] | null | undefined,
  options?: Partial<TableColumn<T>> & { colorMap?: Record<string, string> }
): TableColumn<T> {
  const { colorMap = {}, ...rest } = options || {};

  const defaultColor = 'bg-gray-100 text-gray-700';

  return {
    key,
    header,
    render: (item) => {
      const value = accessor(item);
      if (!value) return <span className="text-gray-400">-</span>;

      const badges = Array.isArray(value) ? value : [value];

      return (
        <div className="flex flex-wrap gap-1">
          {badges.map((badge, idx) => (
            <span
              key={idx}
              className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                colorMap[badge] || defaultColor
              }`}
            >
              {badge}
            </span>
          ))}
        </div>
      );
    },
    ...rest,
  };
}

export default ResponsiveTable;
