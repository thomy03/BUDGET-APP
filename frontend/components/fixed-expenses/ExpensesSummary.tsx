'use client';

import { FixedLine } from '../../lib/api';
import { Card } from '../ui';
import { useFixedExpenseCalculations } from '../../hooks/useFixedExpenseCalculations';

interface ExpensesSummaryProps {
  activeExpenses: FixedLine[];
  config?: any;
}

export function ExpensesSummary({ activeExpenses, config }: ExpensesSummaryProps) {
  const { calculateMonthlyAmount, formatAmount } = useFixedExpenseCalculations(config);

  const totalMonthlyAmount = activeExpenses.reduce((sum, expense) => {
    return sum + calculateMonthlyAmount(expense);
  }, 0);

  if (activeExpenses.length === 0) return null;

  return (
    <Card className="p-4 bg-gradient-to-r from-red-50 to-orange-50 border-red-200">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <p className="text-sm font-medium text-red-700">Dépenses Actives</p>
          <p className="text-2xl font-bold text-red-900">{activeExpenses.length}</p>
        </div>
        <div>
          <p className="text-sm font-medium text-red-700">Total Mensuel</p>
          <p className="text-2xl font-bold text-red-900">
            {formatAmount(totalMonthlyAmount)}
          </p>
        </div>
        <div>
          <p className="text-sm font-medium text-red-700">Total Annuel</p>
          <p className="text-2xl font-bold text-red-900">
            {formatAmount(totalMonthlyAmount * 12)}
          </p>
        </div>
      </div>
    </Card>
  );
}
