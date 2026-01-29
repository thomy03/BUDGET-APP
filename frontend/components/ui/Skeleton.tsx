'use client';

import React from 'react';

interface SkeletonProps {
  /** Width class (e.g., 'w-full', 'w-24') */
  width?: string;
  /** Height class (e.g., 'h-4', 'h-12') */
  height?: string;
  /** Border radius class (e.g., 'rounded', 'rounded-full') */
  rounded?: string;
  /** Additional classes */
  className?: string;
}

/**
 * Basic skeleton loading placeholder
 */
export function Skeleton({
  width = 'w-full',
  height = 'h-4',
  rounded = 'rounded',
  className = '',
}: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-gray-200 ${width} ${height} ${rounded} ${className}`}
      aria-hidden="true"
    />
  );
}

/**
 * Skeleton for text content
 */
export function SkeletonText({
  lines = 3,
  className = '',
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={`space-y-2 ${className}`}>
      {[...Array(lines)].map((_, i) => (
        <Skeleton
          key={i}
          width={i === lines - 1 ? 'w-3/4' : 'w-full'}
          height="h-4"
        />
      ))}
    </div>
  );
}

/**
 * Skeleton for avatar/profile image
 */
export function SkeletonAvatar({
  size = 'md',
  className = '',
}: {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}) {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  };

  return (
    <Skeleton
      width=""
      height=""
      rounded="rounded-full"
      className={`${sizeClasses[size]} ${className}`}
    />
  );
}

/**
 * Skeleton for a card component
 */
export function SkeletonCard({
  className = '',
  hasImage = false,
  hasAvatar = false,
}: {
  className?: string;
  hasImage?: boolean;
  hasAvatar?: boolean;
}) {
  return (
    <div className={`bg-white rounded-xl border border-gray-100 p-4 ${className}`}>
      {hasImage && (
        <Skeleton width="w-full" height="h-32 md:h-48" rounded="rounded-lg" className="mb-4" />
      )}
      <div className="flex items-start gap-3">
        {hasAvatar && <SkeletonAvatar size="md" />}
        <div className="flex-1 space-y-2">
          <Skeleton width="w-3/4" height="h-5" />
          <Skeleton width="w-1/2" height="h-4" />
        </div>
      </div>
      <SkeletonText lines={2} className="mt-4" />
    </div>
  );
}

/**
 * Skeleton for table row
 */
export function SkeletonTableRow({
  columns = 4,
  className = '',
}: {
  columns?: number;
  className?: string;
}) {
  return (
    <div className={`flex items-center gap-4 p-4 border-b border-gray-100 ${className}`}>
      {[...Array(columns)].map((_, i) => (
        <Skeleton
          key={i}
          width={i === 0 ? 'w-24' : i === columns - 1 ? 'w-16' : 'flex-1'}
          height="h-4"
        />
      ))}
    </div>
  );
}

/**
 * Skeleton for a list of items
 */
export function SkeletonList({
  count = 3,
  itemHeight = 'h-16',
  className = '',
}: {
  count?: number;
  itemHeight?: string;
  className?: string;
}) {
  return (
    <div className={`space-y-3 ${className}`}>
      {[...Array(count)].map((_, i) => (
        <div key={i} className={`flex items-center gap-3 ${itemHeight}`}>
          <SkeletonAvatar size="md" />
          <div className="flex-1 space-y-2">
            <Skeleton width="w-2/3" height="h-4" />
            <Skeleton width="w-1/3" height="h-3" />
          </div>
          <Skeleton width="w-16" height="h-4" />
        </div>
      ))}
    </div>
  );
}

/**
 * Skeleton for metric/stat card
 */
export function SkeletonMetric({
  className = '',
}: {
  className?: string;
}) {
  return (
    <div className={`bg-white rounded-xl border border-gray-100 p-4 ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <Skeleton width="w-6" height="h-6" rounded="rounded" />
        <Skeleton width="w-12" height="h-4" rounded="rounded-full" />
      </div>
      <Skeleton width="w-20" height="h-4" className="mb-1" />
      <Skeleton width="w-24" height="h-6" />
      <Skeleton width="w-16" height="h-3" className="mt-1" />
    </div>
  );
}

/**
 * Skeleton for dashboard metrics grid
 */
export function SkeletonMetricsGrid({
  count = 4,
  className = '',
}: {
  count?: number;
  className?: string;
}) {
  return (
    <div className={`grid grid-cols-1 xs:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 ${className}`}>
      {[...Array(count)].map((_, i) => (
        <SkeletonMetric key={i} />
      ))}
    </div>
  );
}

/**
 * Skeleton for chart
 */
export function SkeletonChart({
  height = 'h-64',
  className = '',
}: {
  height?: string;
  className?: string;
}) {
  return (
    <div className={`bg-white rounded-xl border border-gray-100 p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <Skeleton width="w-32" height="h-5" />
        <Skeleton width="w-24" height="h-8" rounded="rounded-lg" />
      </div>
      <div className={`${height} flex items-end justify-around gap-2 pt-4`}>
        {[...Array(7)].map((_, i) => (
          <Skeleton
            key={i}
            width="flex-1"
            height=""
            rounded="rounded-t"
            className={`max-w-[40px]`}
            style={{ height: `${30 + Math.random() * 70}%` }}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * Skeleton for page loading
 */
export function SkeletonPage({
  className = '',
}: {
  className?: string;
}) {
  return (
    <div className={`space-y-6 p-4 md:p-6 ${className}`} role="status" aria-label="Chargement...">
      {/* Header */}
      <div className="text-center space-y-2">
        <Skeleton width="w-48" height="h-8" className="mx-auto" />
        <Skeleton width="w-32" height="h-4" className="mx-auto" />
      </div>

      {/* Metrics */}
      <SkeletonMetricsGrid />

      {/* Content area */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SkeletonCard hasImage />
        <SkeletonList count={4} />
      </div>

      <span className="sr-only">Chargement en cours...</span>
    </div>
  );
}

export default Skeleton;
