'use client';

import { Card } from '../ui';

interface TransactionsSummaryProps {
  month: string | null;
  calculations: {
    totalAmount: number;
    includedCount: number;
    excludedCount: number;
    totalIncome: number;
    totalExpenses: number;
  };
}

export function TransactionsSummary({ month, calculations }: TransactionsSummaryProps) {
  return (
    <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-l-blue-500">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            Résumé du mois - {month}
          </h2>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-gray-900">
                {calculations.totalAmount >= 0 ? '+' : ''}{calculations.totalAmount.toFixed(2)} €
              </span>
              <span className="text-sm text-gray-600">Total du mois</span>
            </div>
            <div className="text-sm text-gray-600">
              {calculations.includedCount} transaction{calculations.includedCount > 1 ? 's' : ''} incluse{calculations.includedCount > 1 ? 's' : ''}
              {calculations.excludedCount > 0 && (
                <span className="ml-1">({calculations.excludedCount} exclue{calculations.excludedCount > 1 ? 's' : ''})</span>
              )}
            </div>
          </div>
        </div>
        <div className="text-right space-y-1">
          <div className="text-sm">
            <span className="text-green-600 font-medium">
              +{calculations.totalIncome.toFixed(2)} € revenus
            </span>
          </div>
          <div className="text-sm">
            <span className="text-red-600 font-medium">
              -{calculations.totalExpenses.toFixed(2)} € dépenses
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}
