'use client';

import { CustomProvision } from '../../lib/api';
import { Card } from '../ui';
import { useProvisionCalculations } from '../../hooks/useProvisionCalculations';

interface ProvisionsSummaryProps {
  activeProvisions: CustomProvision[];
  config?: any;
}

export function ProvisionsSummary({ activeProvisions, config }: ProvisionsSummaryProps) {
  const { calculateMonthlyAmount, formatAmount } = useProvisionCalculations(config);

  const totalMonthlyAmount = activeProvisions.reduce((sum, provision) => {
    return sum + calculateMonthlyAmount(provision);
  }, 0);

  if (activeProvisions.length === 0) return null;

  return (
    <Card className="p-4 bg-gradient-to-r from-indigo-50 to-purple-50 border-indigo-200">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <p className="text-sm font-medium text-indigo-700">Provisions Actives</p>
          <p className="text-2xl font-bold text-indigo-900">{activeProvisions.length}</p>
        </div>
        <div>
          <p className="text-sm font-medium text-indigo-700">Total Mensuel</p>
          <p className="text-2xl font-bold text-indigo-900">
            {formatAmount(totalMonthlyAmount)}
          </p>
        </div>
        <div>
          <p className="text-sm font-medium text-indigo-700">Total Annuel</p>
          <p className="text-2xl font-bold text-indigo-900">
            {formatAmount(totalMonthlyAmount * 12)}
          </p>
        </div>
      </div>
    </Card>
  );
}
