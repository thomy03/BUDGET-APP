'use client';

import React from 'react';

interface PageLoaderProps {
  message?: string;
}

/**
 * PageLoader - Skeleton loading component for lazy-loaded pages
 * Used with React.lazy() and Suspense for code splitting
 */
export const PageLoader: React.FC<PageLoaderProps> = ({
  message = 'Chargement...'
}) => {
  return (
    <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
      <div className="text-center">
        {/* Animated spinner */}
        <div className="relative w-16 h-16 mx-auto mb-4">
          <div className="absolute inset-0 border-4 border-blue-200 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-blue-600 rounded-full border-t-transparent animate-spin"></div>
        </div>

        {/* Loading text */}
        <p className="text-gray-600 font-medium">{message}</p>

        {/* Skeleton cards for visual feedback */}
        <div className="mt-8 max-w-4xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-white rounded-lg p-6 shadow-sm animate-pulse"
              >
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-3"></div>
                <div className="h-8 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * ChartLoader - Skeleton for chart components
 */
export const ChartLoader: React.FC<{ height?: number }> = ({ height = 300 }) => {
  return (
    <div
      className="bg-gray-100 rounded-lg animate-pulse flex items-center justify-center"
      style={{ height }}
    >
      <div className="text-center text-gray-400">
        <svg
          className="w-12 h-12 mx-auto mb-2 opacity-50"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <p className="text-sm">Chargement du graphique...</p>
      </div>
    </div>
  );
};

/**
 * TableLoader - Skeleton for table components
 */
export const TableLoader: React.FC<{ rows?: number }> = ({ rows = 5 }) => {
  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden">
      {/* Header */}
      <div className="bg-gray-50 px-4 py-3 border-b">
        <div className="flex gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-4 bg-gray-200 rounded flex-1 animate-pulse"></div>
          ))}
        </div>
      </div>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-4 py-3 border-b last:border-b-0">
          <div className="flex gap-4">
            {[1, 2, 3, 4].map((j) => (
              <div
                key={j}
                className="h-4 bg-gray-100 rounded flex-1 animate-pulse"
                style={{ animationDelay: `${(i * 4 + j) * 50}ms` }}
              ></div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default PageLoader;
