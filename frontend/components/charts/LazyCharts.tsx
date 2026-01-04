'use client';

import dynamic from 'next/dynamic';
import React, { Suspense, memo } from 'react';
import { ChartLoader } from '../ui/PageLoader';

// Lazy load Recharts components to reduce initial bundle size
// Recharts is ~200KB+ so lazy loading improves initial page load

const LazyPieChart = dynamic(
  () => import('recharts').then((mod) => ({ default: mod.PieChart })),
  { ssr: false, loading: () => <ChartLoader height={300} /> }
);

const LazyBarChart = dynamic(
  () => import('recharts').then((mod) => ({ default: mod.BarChart })),
  { ssr: false, loading: () => <ChartLoader height={300} /> }
);

const LazyLineChart = dynamic(
  () => import('recharts').then((mod) => ({ default: mod.LineChart })),
  { ssr: false, loading: () => <ChartLoader height={300} /> }
);

const LazyAreaChart = dynamic(
  () => import('recharts').then((mod) => ({ default: mod.AreaChart })),
  { ssr: false, loading: () => <ChartLoader height={300} /> }
);

const LazyComposedChart = dynamic(
  () => import('recharts').then((mod) => ({ default: mod.ComposedChart })),
  { ssr: false, loading: () => <ChartLoader height={300} /> }
);

// Re-export static components that don't need lazy loading
export {
  ResponsiveContainer,
  Pie,
  Bar,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
  ReferenceLine
} from 'recharts';

// Export lazy components
export {
  LazyPieChart as PieChart,
  LazyBarChart as BarChart,
  LazyLineChart as LineChart,
  LazyAreaChart as AreaChart,
  LazyComposedChart as ComposedChart
};

// Memoized chart wrapper to prevent unnecessary re-renders
interface ChartWrapperProps {
  children: React.ReactNode;
  height?: number | string;
  width?: string;
  className?: string;
}

export const MemoizedChartWrapper = memo<ChartWrapperProps>(
  ({ children, height = 300, width = '100%', className = '' }) => (
    <div className={`chart-wrapper ${className}`} style={{ width, height }}>
      <Suspense fallback={<ChartLoader height={typeof height === 'number' ? height : 300} />}>
        {children}
      </Suspense>
    </div>
  )
);

MemoizedChartWrapper.displayName = 'MemoizedChartWrapper';

export default {
  PieChart: LazyPieChart,
  BarChart: LazyBarChart,
  LineChart: LazyLineChart,
  AreaChart: LazyAreaChart,
  ComposedChart: LazyComposedChart,
};
