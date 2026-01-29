'use client';

import React from 'react';
import { Summary, ConfigOut, CustomProvision, FixedLine } from '../../lib/api';
import { calculateBudgetTotals } from '../../lib/dashboard-calculations';
import { Card } from '../ui';

interface KeyMetricsProps {
  summary: Summary | null;
  config: ConfigOut | null;
  provisions: CustomProvision[];
  fixedExpenses: FixedLine[];
}

const KeyMetrics = React.memo<KeyMetricsProps>(({ 
  summary, 
  config, 
  provisions = [], 
  fixedExpenses = [] 
}) => {
  // Early return with loading state if data is not ready
  if (!summary || !config) {
    return (
      <div className="grid grid-cols-1 xs:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {[...Array(4)].map((_, index) => (
          <MetricCardSkeleton key={index} />
        ))}
      </div>
    );
  }

  const activeProvisions = provisions.filter(p => p.is_active);
  const activeFixedExpenses = fixedExpenses.filter(e => e.active);
  
  // Provide safe default value for var_total
  const safeVarTotal = summary.var_total ?? 0;
  
  const { 
    totalProvisions, 
    totalFixedExpenses, 
    totalVariables, 
    budgetTotal 
  } = calculateBudgetTotals(provisions, fixedExpenses, safeVarTotal, config);

  return (
    <div className="grid grid-cols-1 xs:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
      <MetricCard
        title="Total Provisions"
        value={totalProvisions}
        color="indigo"
        icon="🎯"
        subtitle={`${activeProvisions.length} provision${activeProvisions.length > 1 ? 's' : ''}`}
      />
      <MetricCard
        title="Charges Fixes"
        value={totalFixedExpenses}
        color="emerald"
        icon="💳"
        subtitle={`${activeFixedExpenses.length} dépense${activeFixedExpenses.length > 1 ? 's' : ''}`}
      />
      <MetricCard
        title="Variables"
        value={totalVariables}
        color="blue"
        icon="📊"
        subtitle="Transactions bancaires"
      />
      <MetricCard
        title="Budget Total"
        value={budgetTotal}
        color="purple"
        icon="📈"
        subtitle="Vision d'ensemble"
        isTotal
      />
    </div>
  );
});

KeyMetrics.displayName = 'KeyMetrics';

// Individual metric card
const MetricCard = React.memo<{ 
  title: string; 
  value: number; 
  color: string; 
  icon: string;
  subtitle?: string;
  isTotal?: boolean;
}>(({ title, value, color, icon, subtitle, isTotal = false }) => {
  const colorClasses = {
    indigo: 'border-l-indigo-500 bg-gradient-to-r from-indigo-50 to-indigo-100 text-indigo-900',
    emerald: 'border-l-emerald-500 bg-gradient-to-r from-emerald-50 to-emerald-100 text-emerald-900',
    blue: 'border-l-blue-500 bg-gradient-to-r from-blue-50 to-blue-100 text-blue-900',
    purple: 'border-l-purple-500 bg-gradient-to-r from-purple-50 to-purple-100 text-purple-900'
  };

  // Safe value handling with fallback to 0
  const safeValue = typeof value === 'number' && !isNaN(value) ? value : 0;

  return (
    <Card className={`p-3 md:p-4 border-l-4 ${colorClasses[color as keyof typeof colorClasses]} ${
      isTotal ? 'ring-2 ring-purple-200 shadow-lg' : ''
    }`}>
      <div className="flex items-center justify-between mb-1.5 md:mb-2">
        <span className="text-base md:text-lg">{icon}</span>
        {isTotal && <span className="text-[10px] md:text-xs font-medium px-1.5 md:px-2 py-0.5 md:py-1 bg-purple-200 rounded-full">TOTAL</span>}
      </div>
      <div className="text-xs md:text-sm font-medium mb-0.5 md:mb-1">{title}</div>
      <div className={`text-lg md:text-xl font-bold ${isTotal ? 'md:text-2xl' : ''}`}>{safeValue.toFixed(2)} €</div>
      {subtitle && <div className="text-[10px] md:text-xs opacity-75 mt-0.5 md:mt-1 truncate">{subtitle}</div>}
    </Card>
  );
});

MetricCard.displayName = 'MetricCard';

// Loading skeleton component
const MetricCardSkeleton = () => (
  <Card className="p-4 border-l-4 border-l-gray-300 bg-gradient-to-r from-gray-50 to-gray-100 animate-pulse">
    <div className="flex items-center justify-between mb-2">
      <div className="w-6 h-6 bg-gray-300 rounded"></div>
    </div>
    <div className="w-20 h-4 bg-gray-300 rounded mb-1"></div>
    <div className="w-24 h-6 bg-gray-300 rounded"></div>
    <div className="w-16 h-3 bg-gray-300 rounded mt-1"></div>
  </Card>
);

export default KeyMetrics;