'use client';

import React from 'react';
import { Input } from '../ui';
import { FixedLine, ConfigOut } from '../../lib/api';

interface FixedExpenseCalculationSettingsProps {
  formData: Omit<FixedLine, 'id'>;
  config?: ConfigOut;
  onChange: (field: keyof Omit<FixedLine, 'id'>, value: any) => void;
}

const FixedExpenseCalculationSettings = React.memo<FixedExpenseCalculationSettingsProps>(({
  formData,
  config,
  onChange
}) => {
  const calculateMonthlyAmount = (): number => {
    switch (formData.freq) {
      case 'mensuelle':
        return formData.amount;
      case 'trimestrielle':
        return formData.amount / 3;
      case 'annuelle':
        return formData.amount / 12;
      default:
        return formData.amount;
    }
  };

  const calculateMemberSplit = (monthlyAmount: number) => {
    if (!config) return { member1: 0, member2: 0 };

    switch (formData.split_mode) {
      case 'clé':
        const totalRev = (config.rev1 || 0) + (config.rev2 || 0);
        if (totalRev > 0) {
          const r1 = (config.rev1 || 0) / totalRev;
          const r2 = (config.rev2 || 0) / totalRev;
          return { member1: monthlyAmount * r1, member2: monthlyAmount * r2 };
        }
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case '50/50':
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case 'm1':
        return { member1: monthlyAmount, member2: 0 };
      case 'm2':
        return { member1: 0, member2: monthlyAmount };
      case 'manuel':
        return { 
          member1: monthlyAmount * formData.split1, 
          member2: monthlyAmount * formData.split2 
        };
      default:
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
    }
  };

  const monthlyAmount = calculateMonthlyAmount();
  const memberSplit = calculateMemberSplit(monthlyAmount);

  return (
    <div className="space-y-4">
      <h4 className="font-medium text-zinc-700">💰 Montant et répartition</h4>
      
      {/* Amount and Frequency */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Input
          label="Montant (€) *"
          type="number"
          value={formData.amount}
          onChange={(e) => onChange('amount', Number(e.target.value))}
          placeholder="0.00"
          min="0"
          step="0.01"
          required
        />
        
        <div>
          <label className="block text-sm font-medium mb-2">Fréquence</label>
          <select
            value={formData.freq}
            onChange={(e) => onChange('freq', e.target.value)}
            className="w-full p-3 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="mensuelle">Mensuelle</option>
            <option value="trimestrielle">Trimestrielle</option>
            <option value="annuelle">Annuelle</option>
          </select>
        </div>
      </div>

      {/* Split Mode */}
      <div>
        <label className="block text-sm font-medium mb-2">Répartition</label>
        <select
          value={formData.split_mode}
          onChange={(e) => onChange('split_mode', e.target.value)}
          className="w-full p-3 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="clé">Selon la clé de répartition</option>
          <option value="50/50">50/50</option>
          <option value="m1">100% {config?.member1 || 'Membre 1'}</option>
          <option value="m2">100% {config?.member2 || 'Membre 2'}</option>
          <option value="manuel">Manuel</option>
        </select>
      </div>

      {/* Manual Split */}
      {formData.split_mode === 'manuel' && (
        <div className="grid grid-cols-2 gap-4">
          <Input
            label={`Part ${config?.member1 || 'Membre 1'}`}
            type="number"
            value={formData.split1}
            onChange={(e) => onChange('split1', Number(e.target.value))}
            min="0"
            max="1"
            step="0.01"
          />
          <Input
            label={`Part ${config?.member2 || 'Membre 2'}`}
            type="number"
            value={formData.split2}
            onChange={(e) => onChange('split2', Number(e.target.value))}
            min="0"
            max="1"
            step="0.01"
          />
        </div>
      )}

      {/* Preview */}
      {config && (
        <div className="p-4 bg-emerald-50 rounded-lg">
          <h5 className="font-medium text-emerald-900 mb-2">Aperçu mensuel</h5>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Montant mensuel :</span>
              <span className="font-mono font-semibold">{monthlyAmount.toFixed(2)} €</span>
            </div>
            <div className="flex justify-between text-emerald-800">
              <span>{config.member1} :</span>
              <span className="font-mono">{memberSplit.member1.toFixed(2)} €</span>
            </div>
            <div className="flex justify-between text-emerald-800">
              <span>{config.member2} :</span>
              <span className="font-mono">{memberSplit.member2.toFixed(2)} €</span>
            </div>
            {formData.freq !== 'mensuelle' && (
              <div className="pt-2 border-t border-emerald-200 text-xs text-emerald-700">
                Montant {formData.freq === 'trimestrielle' ? 'trimestriel' : 'annuel'} : {formData.amount.toFixed(2)} €
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
});

FixedExpenseCalculationSettings.displayName = 'FixedExpenseCalculationSettings';

export default FixedExpenseCalculationSettings;