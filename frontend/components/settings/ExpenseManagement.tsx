'use client';

import { ConfigOut } from '../../lib/api';
import FixedExpenses from '../FixedExpenses';
import CustomProvisions from '../CustomProvisions';
import { Card } from '../ui';

interface ExpenseManagementProps {
  config?: ConfigOut;
  onDataChange?: () => void;
}

export function ExpenseManagement({ config, onDataChange }: ExpenseManagementProps) {
  return (
    <div className="space-y-8">
      {/* Dépenses Fixes */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="border-b pb-3">
            <h3 className="text-xl font-semibold text-gray-900 flex items-center">
              <span className="mr-2">💳</span>
              Dépenses Fixes
            </h3>
            <p className="text-gray-600 text-sm mt-1">
              Gérez vos dépenses récurrentes automatiques (loyer, abonnements, etc.)
            </p>
          </div>
          <FixedExpenses config={config} onDataChange={onDataChange} />
        </div>
      </Card>

      {/* Provisions Personnalisées */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="border-b pb-3">
            <h3 className="text-xl font-semibold text-gray-900 flex items-center">
              <span className="mr-2">🎯</span>
              Provisions Personnalisées
            </h3>
            <p className="text-gray-600 text-sm mt-1">
              Créez vos objectifs d'épargne et provisions pour projets futurs
            </p>
          </div>
          <CustomProvisions config={config} onDataChange={onDataChange} />
        </div>
      </Card>
    </div>
  );
}